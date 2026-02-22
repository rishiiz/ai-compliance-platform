"use client";

import { useState, lazy, Suspense, useEffect } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, AlertTriangle, ShieldAlert, GitCompare, Database } from "lucide-react";
import { useAnalytics } from "@/api/hooks";
import { fetchPolicies, fetchPolicyCompare, fetchCompanyDatabaseData } from "@/api";
import type { PolicyCompareResult, CompanyDatabaseData } from "@/api";
import DashboardLoading from "./loading";
import type { Policy } from "@/types";

const TrendChart = lazy(() =>
  import("@/components/dashboard/trend-chart-dynamic").then((m) => ({ default: m.TrendChart }))
);

export default function DashboardPage() {
  const { data: analytics, isLoading, error } = useAnalytics();

  // Company database (connection + fetched data)
  const [companyDb, setCompanyDb] = useState<CompanyDatabaseData | null>(null);

  // Policy Impact state (compare previous/old vs new policies)
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [policiesLoading, setPoliciesLoading] = useState(false);
  const [oldPolicyId, setOldPolicyId] = useState("");
  const [newPolicyId, setNewPolicyId] = useState("");
  const [comparing, setComparing] = useState(false);
  const [compareResult, setCompareResult] = useState<PolicyCompareResult | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);

  useEffect(() => {
    fetchCompanyDatabaseData().then(setCompanyDb);
  }, []);

  useEffect(() => {
    setPoliciesLoading(true);
    fetchPolicies()
      .then((list) => {
        setPolicies(list);
        if (list.length >= 2) {
          setOldPolicyId(String(list[0].id));
          setNewPolicyId(String(list[1].id));
        } else if (list.length === 1) {
          setOldPolicyId(String(list[0].id));
        }
      })
      .finally(() => setPoliciesLoading(false));
  }, []);

  const handleCompare = async () => {
    if (!oldPolicyId || !newPolicyId || oldPolicyId === newPolicyId) return;
    setComparing(true);
    setCompareResult(null);
    setCompareError(null);
    try {
      const result = await fetchPolicyCompare(oldPolicyId, newPolicyId, true);
      setCompareResult(result);
    } catch (e) {
      setCompareError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setComparing(false);
    }
  };

  if (isLoading && !analytics) {
    return <DashboardLoading />;
  }
  if (error || !analytics) {
    return (
      <PageTransition>
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-destructive">
          {error?.message ?? "Failed to load dashboard data."}
        </div>
      </PageTransition>
    );
  }

  const { complianceScore, totalPolicies, activeViolations, trendData } = analytics;

  return (
    <PageTransition>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-muted-foreground">
            AI-powered compliance monitoring and analytics overview
          </p>
        </div>

        {/* Company database connection + fetched data */}
        {companyDb && (
          <Card className="border-primary/20 bg-primary/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <h3 className="font-semibold flex items-center gap-2">
                <Database className="h-4 w-4 text-primary" />
                Company database
              </h3>
              {companyDb.connected ? (
                <span className="rounded-full bg-primary/20 px-2.5 py-0.5 text-xs font-medium text-primary">
                  Connected
                </span>
              ) : (
                <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">
                  Not connected
                </span>
              )}
            </CardHeader>
            <CardContent className="space-y-2">
              {companyDb.connected ? (
                <>
                  <p className="text-sm text-muted-foreground">
                    {companyDb.username && companyDb.db_name
                      ? `Connected as ${companyDb.username} to ${companyDb.host ?? "—"} / ${companyDb.db_name}`
                      : "Connected to company database."}
                  </p>
                  {companyDb.data_error ? (
                    <p className="text-sm text-destructive">{companyDb.data_error}</p>
                  ) : (
                    <>
                      <p className="text-sm font-medium text-foreground">
                        Policy documents in company DB: <span className="text-primary">{companyDb.count ?? 0}</span>
                      </p>
                      {companyDb.documents && companyDb.documents.length > 0 && (
                        <ul className="mt-2 max-h-32 overflow-y-auto rounded-md border border-border/50 bg-background/50 p-2 text-sm">
                          {companyDb.documents.map((doc, i) => (
                            <li key={doc.id ?? i} className="truncate text-muted-foreground">
                              {doc.title ?? `Document #${doc.id ?? i + 1}`}
                            </li>
                          ))}
                        </ul>
                      )}
                    </>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Connect your company database in Settings → Database to scan for compliance and see data here.
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* KPI Cards — 3 only */}
        <div className="grid gap-4 md:grid-cols-3">
          <KpiCard
            title="Compliance Score"
            value={`${complianceScore}%`}
            icon={<ShieldAlert />}
            delay={0}
            gradient
          />
          <KpiCard
            title="Total Policies"
            value={totalPolicies}
            icon={<FileText />}
            delay={0}
          />
          <KpiCard
            title="Active Violations"
            value={activeViolations}
            icon={<AlertTriangle />}
            delay={0}
          />
        </div>

        {/* Trend chart + Policy Impact */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* 24-Hour Compliance Trend (left 2/3) */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <h3 className="font-semibold">24-Hour Compliance Trend</h3>
                  <p className="text-sm text-muted-foreground">
                    Score progression over the last 24 hours
                  </p>
                </div>
              </CardHeader>
              <CardContent>
                {trendData.length === 0 ? (
                  <div className="flex h-[300px] min-h-[300px] items-center justify-center rounded-lg border border-dashed border-border/50 bg-muted/20">
                    <p className="text-sm text-muted-foreground">No trend data yet. Run scans over time to see score progression.</p>
                  </div>
                ) : (
                  <Suspense fallback={<div className="h-[300px] animate-pulse rounded-lg bg-muted/30" />}>
                    <TrendChart data={trendData} />
                  </Suspense>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Compare previous (old) vs new policies */}
          <div>
            <Card className="h-full">
              <CardHeader>
                <h3 className="font-semibold flex items-center gap-2">
                  <GitCompare className="h-4 w-4" />
                  Compare policies
                </h3>
                <p className="text-sm text-muted-foreground">
                  Compare previous (old) and new policy versions — rule diff and impact on violations
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                {policies.length === 0 && !policiesLoading ? (
                  <p className="text-sm text-muted-foreground">
                    Upload policies to compare old vs new versions.
                  </p>
                ) : policiesLoading ? (
                  <p className="text-sm text-muted-foreground">Loading policies…</p>
                ) : (
                  <>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Previous / old policy</label>
                      <select
                        value={oldPolicyId}
                        onChange={(e) => { setOldPolicyId(e.target.value); setCompareResult(null); setCompareError(null); }}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      >
                        {policies.map((p) => (
                          <option key={p.id} value={p.id}>{p.name} (v{p.version})</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">New policy</label>
                      <select
                        value={newPolicyId}
                        onChange={(e) => { setNewPolicyId(e.target.value); setCompareResult(null); setCompareError(null); }}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      >
                        {policies.map((p) => (
                          <option key={p.id} value={p.id}>{p.name} (v{p.version})</option>
                        ))}
                      </select>
                    </div>
                    <Button
                      onClick={handleCompare}
                      disabled={comparing || !oldPolicyId || !newPolicyId || oldPolicyId === newPolicyId}
                      className="w-full"
                      size="sm"
                    >
                      {comparing ? "Comparing…" : "Compare"}
                    </Button>

                    {compareError && (
                      <p className="text-sm text-destructive">{compareError}</p>
                    )}

                    {compareResult && (
                      <div className="space-y-2 rounded-lg border border-border/50 bg-muted/20 p-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Only in old</span>
                          <span className="font-medium">{compareResult.only_in_old.length}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Only in new</span>
                          <span className="font-medium">{compareResult.only_in_new.length}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">In both</span>
                          <span className="font-medium">{compareResult.in_both.length}</span>
                        </div>
                        {compareResult.impact?.message && (
                          <p className="mt-2 text-xs text-muted-foreground border-t border-border/50 pt-2">
                            {compareResult.impact.message}
                          </p>
                        )}
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
