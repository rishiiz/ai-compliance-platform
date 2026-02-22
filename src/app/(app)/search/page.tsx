"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { PageTransition } from "@/components/layout/page-transition";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, FileText, ScrollText, AlertTriangle } from "lucide-react";
import { fetchPolicies, fetchRules, fetchViolations } from "@/api";
import type { Policy, Rule, Violation } from "@/types";

function matchesQuery(text: string | null | undefined, q: string): boolean {
  if (!text || !q) return false;
  return text.toLowerCase().includes(q.toLowerCase());
}

export default function SearchPage() {
  const searchParams = useSearchParams();
  const q = (searchParams.get("q") ?? "").trim();

  const [policies, setPolicies] = useState<Policy[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!q) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([fetchPolicies(), fetchRules(), fetchViolations()])
      .then(([p, r, v]) => {
        setPolicies(p);
        setRules(r);
        setViolations(v);
      })
      .finally(() => setLoading(false));
  }, [q]);

  const filtered = useMemo(() => {
    if (!q) return { policies: [], rules: [], violations: [] };
    const lower = q.toLowerCase();
    return {
      policies: policies.filter(
        (p) =>
          matchesQuery(p.name, q) ||
          p.name.toLowerCase().includes(lower)
      ),
      rules: rules.filter(
        (r) =>
          matchesQuery(r.clause, q) ||
          matchesQuery(r.policyName, q) ||
          r.clause.toLowerCase().includes(lower) ||
          (r.policyName && r.policyName.toLowerCase().includes(lower))
      ),
      violations: violations.filter(
        (v) =>
          matchesQuery(v.clause, q) ||
          matchesQuery(v.policyName, q) ||
          matchesQuery(v.aiExplanation, q) ||
          matchesQuery(v.evidence, q) ||
          v.clause.toLowerCase().includes(lower) ||
          (v.policyName && v.policyName.toLowerCase().includes(lower)) ||
          (v.aiExplanation && v.aiExplanation.toLowerCase().includes(lower))
      ),
    };
  }, [q, policies, rules, violations]);

  if (!q) {
    return (
      <PageTransition>
        <div className="space-y-8">
          <h1 className="text-3xl font-bold tracking-tight">Search</h1>
          <p className="text-muted-foreground">
            Enter a term in the header search bar and press Enter to search policies, rules, and violations.
          </p>
        </div>
      </PageTransition>
    );
  }

  if (loading) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      </PageTransition>
    );
  }

  const { policies: pList, rules: rList, violations: vList } = filtered;
  const total = pList.length + rList.length + vList.length;

  return (
    <PageTransition>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Search results</h1>
          <p className="mt-1 text-muted-foreground">
            &ldquo;{q}&rdquo; — {total} result{total !== 1 ? "s" : ""} across policies, rules, and violations
          </p>
        </div>

        {total === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              <Search className="mx-auto h-12 w-12 opacity-50 mb-4" />
              <p>No policies, rules, or violations match your search.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {pList.length > 0 && (
              <Card>
                <CardHeader className="flex flex-row items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  <h2 className="font-semibold">Policies ({pList.length})</h2>
                </CardHeader>
                <CardContent className="space-y-2">
                  {pList.map((p) => (
                    <Link
                      key={p.id}
                      href="/upload"
                      className="block rounded-lg border border-border/50 bg-card p-3 transition-colors hover:bg-accent/30"
                    >
                      <p className="font-medium">{p.name}</p>
                      <p className="text-xs text-muted-foreground">
                        Version {p.version} · {p.rulesCount} rules
                      </p>
                    </Link>
                  ))}
                </CardContent>
              </Card>
            )}

            {rList.length > 0 && (
              <Card>
                <CardHeader className="flex flex-row items-center gap-2">
                  <ScrollText className="h-5 w-5 text-primary" />
                  <h2 className="font-semibold">Rules ({rList.length})</h2>
                </CardHeader>
                <CardContent className="space-y-2">
                  {rList.map((r) => (
                    <Link
                      key={r.id}
                      href="/rules"
                      className="block rounded-lg border border-border/50 bg-card p-3 transition-colors hover:bg-accent/30"
                    >
                      <p className="font-medium">{r.clause}</p>
                      <div className="mt-1 flex items-center gap-2">
                        <Badge variant="outline">{r.severity}</Badge>
                        <span className="text-xs text-muted-foreground">{r.policyName}</span>
                      </div>
                    </Link>
                  ))}
                </CardContent>
              </Card>
            )}

            {vList.length > 0 && (
              <Card>
                <CardHeader className="flex flex-row items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-primary" />
                  <h2 className="font-semibold">Violations ({vList.length})</h2>
                </CardHeader>
                <CardContent className="space-y-2">
                  {vList.map((v) => (
                    <Link
                      key={v.id}
                      href={`/violations?id=${v.id}`}
                      className="block rounded-lg border border-border/50 bg-card p-3 transition-colors hover:bg-accent/30"
                    >
                      <p className="font-medium">{v.clause}</p>
                      <p className="text-xs text-muted-foreground line-clamp-2">{v.aiExplanation}</p>
                      <div className="mt-1 flex items-center gap-2">
                        <Badge variant="outline">{v.severity}</Badge>
                        <span className="text-xs text-muted-foreground">{v.status}</span>
                      </div>
                    </Link>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </PageTransition>
  );
}
