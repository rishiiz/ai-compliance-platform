"use client";

import { useState, useCallback, useEffect } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GitCompare } from "lucide-react";
import { fetchPolicies, fetchPolicyCompare, type PolicyCompareResult } from "@/api";
import { config } from "@/lib/env";

export default function PolicyImpactPage() {
  const [oldPolicyId, setOldPolicyId] = useState<string>("");
  const [newPolicyId, setNewPolicyId] = useState<string>("");
  const [result, setResult] = useState<PolicyCompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [policiesList, setPoliciesList] = useState<{ id: string; name: string; version: string }[]>([]);

  useEffect(() => {
    if (!config.apiUrl) return;
    fetchPolicies()
      .then(setPoliciesList)
      .catch(() => setPoliciesList([]));
  }, []);

  const loadPoliciesOnce = useCallback(async () => {
    if (policiesList.length > 0 || !config.apiUrl) return;
    try {
      const list = await fetchPolicies();
      setPoliciesList(list);
    } catch {
      setPoliciesList([]);
    }
  }, [policiesList.length]);

  const handleCompare = useCallback(async () => {
    if (!oldPolicyId || !newPolicyId) {
      setError("Select both old and new policy versions.");
      return;
    }
    if (oldPolicyId === newPolicyId) {
      setError("Old and new policy must be different.");
      return;
    }
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await fetchPolicyCompare(oldPolicyId, newPolicyId, true);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compare failed");
    } finally {
      setLoading(false);
    }
  }, [oldPolicyId, newPolicyId]);

  return (
    <PageTransition>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Policy Impact</h1>
          <p className="mt-1 text-muted-foreground">
            Compare two policy versions and see rule changes plus estimated new violations if you adopt the new policy
          </p>
        </div>

        {!config.apiUrl && (
          <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
            <strong>Backend not connected.</strong> Set <strong>NEXT_PUBLIC_API_URL</strong> in <strong>.env.local</strong> to use Policy Impact.
          </div>
        )}

        <Card>
          <CardHeader>
            <h3 className="font-semibold flex items-center gap-2">
              <GitCompare className="h-4 w-4" />
              Compare policy versions
            </h3>
            <p className="text-sm text-muted-foreground">
              Select old and new policy (by version). Impact count is based on current connected database snapshot.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <PolicyImpactPageInner
              policiesList={policiesList}
              loadPoliciesOnce={loadPoliciesOnce}
              oldPolicyId={oldPolicyId}
              setOldPolicyId={setOldPolicyId}
              newPolicyId={newPolicyId}
              setNewPolicyId={setNewPolicyId}
              onCompare={handleCompare}
              loading={loading}
              error={error}
              result={result}
            />
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}

function PolicyImpactPageInner({
  policiesList,
  loadPoliciesOnce,
  oldPolicyId,
  setOldPolicyId,
  newPolicyId,
  setNewPolicyId,
  onCompare,
  loading,
  error,
  result,
}: {
  policiesList: { id: string; name: string; version: string }[];
  loadPoliciesOnce: () => Promise<void>;
  oldPolicyId: string;
  setOldPolicyId: (v: string) => void;
  newPolicyId: string;
  setNewPolicyId: (v: string) => void;
  onCompare: () => void;
  loading: boolean;
  error: string | null;
  result: PolicyCompareResult | null;
}) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-sm font-medium">Old policy version</label>
          <select
            value={oldPolicyId}
            onChange={(e) => setOldPolicyId(e.target.value)}
            onFocus={loadPoliciesOnce}
            className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground"
          >
            <option value="">Select policy...</option>
            {policiesList.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} (v{p.version})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium">New policy version</label>
          <select
            value={newPolicyId}
            onChange={(e) => setNewPolicyId(e.target.value)}
            onFocus={loadPoliciesOnce}
            className="w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground"
          >
            <option value="">Select policy...</option>
            {policiesList.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} (v{p.version})
              </option>
            ))}
          </select>
        </div>
      </div>
      <Button onClick={onCompare} disabled={loading || !config.apiUrl} className="gap-2">
        {loading ? "Comparing…" : "Compare"}
      </Button>
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}
      {result && (
        <div className="space-y-4 pt-4 border-t border-border">
          <div className="flex flex-wrap gap-4 text-sm">
            <span>
              <strong>Only in old:</strong> {result.only_in_old.length} rules
            </span>
            <span>
              <strong>Only in new:</strong> {result.only_in_new.length} rules
            </span>
            <span>
              <strong>In both:</strong> {result.in_both.length} rules
            </span>
          </div>
          {result.impact.new_violations_count !== null && (
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
              <h4 className="font-medium text-emerald-700 dark:text-emerald-400">Impact</h4>
              <p className="mt-1 text-sm">{result.impact.message}</p>
            </div>
          )}
          {result.impact.new_violations_count === null && result.only_in_new.length > 0 && (
            <p className="text-sm text-muted-foreground">{result.impact.message}</p>
          )}
          {result.only_in_new.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Rules only in new policy</h4>
              <ul className="space-y-2">
                {result.only_in_new.map((r) => (
                  <li key={r.id} className="flex items-start gap-2 rounded-lg border border-border bg-card p-3 text-sm">
                    <Badge variant={r.severity === "critical" || r.severity === "high" ? "destructive" : "default"}>
                      {r.severity}
                    </Badge>
                    <span className="text-muted-foreground line-clamp-2">
                      {typeof r.policy_clause_text === "string" && r.policy_clause_text
                        ? r.policy_clause_text
                        : `Rule #${r.id} (entity/field from rule_data)`}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </>
  );
}
