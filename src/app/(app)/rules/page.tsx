"use client";

import { useState, useEffect } from "react";
import * as Collapsible from "@radix-ui/react-collapsible";
import { AnimatePresence } from "framer-motion";
import { PageTransition } from "@/components/layout/page-transition";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronDown, ChevronRight, ScrollText, RefreshCw, Plus, Trash2 } from "lucide-react";
import { useRules } from "@/api/hooks";
import { createRule, deleteRule, fetchPolicies } from "@/api";
import type { Policy } from "@/types";
import { config } from "@/lib/env";
import Link from "next/link";

export default function RulesPage() {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [addOpen, setAddOpen] = useState(false);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [addPolicyId, setAddPolicyId] = useState<string>("");
  const [addSeverity, setAddSeverity] = useState("medium");
  const [addClause, setAddClause] = useState("");
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const { data: filteredRules, isLoading, error, refetch } = useRules({
    status: statusFilter,
    severity: severityFilter,
  });

  const severityVariant: Record<string, "critical" | "warning" | "default"> = {
    critical: "critical",
    high: "warning",
    medium: "default",
  };

  useEffect(() => {
    if (config.apiUrl && addOpen) fetchPolicies().then(setPolicies);
  }, [addOpen]);

  const handleAddRule = async () => {
    if (!addPolicyId || !addClause.trim()) {
      setAddError("Select a policy and enter rule text.");
      return;
    }
    setAddError(null);
    setAddSubmitting(true);
    try {
      await createRule({
        policy_id: Number(addPolicyId),
        severity: addSeverity,
        policy_clause_text: addClause.trim(),
      });
      setAddOpen(false);
      setAddClause("");
      setAddPolicyId("");
      setAddSeverity("medium");
      refetch();
    } catch (e) {
      setAddError(e instanceof Error ? e.message : "Failed to add rule");
    } finally {
      setAddSubmitting(false);
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    setDeletingId(ruleId);
    try {
      await deleteRule(ruleId);
      setDeleteConfirmId(null);
      refetch();
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <PageTransition>
      <div className="space-y-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Rules</h1>
            <p className="mt-1 text-muted-foreground">
              Policy-derived compliance rules and requirements
            </p>
          </div>
          {config.apiUrl && (
            <div className="flex gap-2">
              <Button variant="default" size="sm" onClick={() => setAddOpen(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                Add rule
              </Button>
              <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading} className="gap-2">
                <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          )}
          {error && (
            <p className="text-sm text-destructive">{error.message}</p>
          )}
          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
            </select>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All Severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
            </select>
          </div>
        </div>

        <div className="grid gap-4">
          {isLoading && filteredRules.length === 0 ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <Card key={i}>
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      <Skeleton className="h-10 w-10 rounded-lg shrink-0" />
                      <div className="flex-1 min-w-0 space-y-2">
                        <Skeleton className="h-5 w-full max-w-md" />
                        <div className="flex flex-wrap gap-2">
                          <Skeleton className="h-6 w-16 rounded-full" />
                          <Skeleton className="h-6 w-14 rounded-full" />
                          <Skeleton className="h-4 w-24" />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : filteredRules.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-card p-8 text-center">
              {!config.apiUrl ? (
                <>
                  <p className="font-medium text-foreground">Backend not connected</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Set <strong>NEXT_PUBLIC_API_URL</strong> in <strong>.env.local</strong> (e.g. <code className="rounded bg-muted px-1">http://localhost:8000</code>) and restart the dev server to load rules from the backend.
                  </p>
                </>
              ) : (
                <>
                  <p className="font-medium text-foreground">No rules yet</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Rules are displayed here after you upload policy PDFs. Go to <Link href="/upload" className="underline font-medium">Upload policy</Link>, upload a PDF, then click <strong>Refresh</strong> above or return here to see the rules.
                  </p>
                </>
              )}
            </div>
          ) : (
            <>
              {filteredRules.map((rule) => (
            <div key={rule.id}>
              <Collapsible.Root
                open={expandedId === rule.id}
                onOpenChange={(open) => setExpandedId(open ? rule.id : null)}
              >
                <Card className="overflow-hidden">
                  <Collapsible.Trigger asChild>
                    <button className="w-full text-left">
                      <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                          <div className="rounded-lg bg-primary/10 p-2">
                            <ScrollText className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium">{rule.clause}</p>
                            <div className="mt-2 flex flex-wrap items-center gap-2">
                              <Badge variant={severityVariant[rule.severity] || "default"}>
                                {rule.severity}
                              </Badge>
                              <Badge variant="outline">v{rule.version}</Badge>
                              <Badge
                                variant={rule.status === "active" ? "success" : "secondary"}
                              >
                                {rule.status}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                {rule.policyName} • {rule.department}
                              </span>
                            </div>
                          </div>
                          {expandedId === rule.id ? (
                            <ChevronDown className="h-5 w-5 shrink-0 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
                          )}
                        </div>
                      </CardContent>
                    </button>
                  </Collapsible.Trigger>
                  <AnimatePresence>
                    {expandedId === rule.id && (
                      <div className="overflow-hidden">
                        <div className="border-t border-border/50 bg-muted/20 px-6 py-4 flex items-start justify-between gap-4">
                          <div className="space-y-2 text-sm">
                            <div>
                              <span className="font-medium text-muted-foreground">
                                Category:
                              </span>{" "}
                              {rule.category}
                            </div>
                            <div>
                              <span className="font-medium text-muted-foreground">
                                Policy ID:
                              </span>{" "}
                              {rule.policyId}
                            </div>
                            <div>
                              <span className="font-medium text-muted-foreground">
                                Created:
                              </span>{" "}
                              {new Date(rule.createdAt).toLocaleDateString()}
                            </div>
                          </div>
                          {config.apiUrl && (
                            <>
                              {deleteConfirmId === rule.id ? (
                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-muted-foreground">Delete?</span>
                                  <Button
                                    variant="destructive"
                                    size="sm"
                                    onClick={() => handleDeleteRule(rule.id)}
                                    disabled={deletingId === rule.id}
                                  >
                                    {deletingId === rule.id ? "Deleting…" : "Yes"}
                                  </Button>
                                  <Button variant="ghost" size="sm" onClick={() => setDeleteConfirmId(null)}>
                                    No
                                  </Button>
                                </div>
                              ) : (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-destructive hover:text-destructive"
                                  onClick={() => setDeleteConfirmId(rule.id)}
                                  disabled={deletingId !== null}
                                >
                                  <Trash2 className="h-4 w-4 mr-1" />
                                  Delete rule
                                </Button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </AnimatePresence>
                </Card>
              </Collapsible.Root>
            </div>
              ))}
            </>
          )}
        </div>

        {/* Add rule dialog */}
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add rule</DialogTitle>
              <DialogDescription>
                Create a manual compliance rule linked to a policy.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              {addError && (
                <p className="text-sm text-destructive">{addError}</p>
              )}
              <div>
                <label className="mb-1 block text-sm font-medium">Policy</label>
                <select
                  value={addPolicyId}
                  onChange={(e) => setAddPolicyId(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                  <option value="">Select policy</option>
                  {policies.map((p) => (
                    <option key={p.id} value={String(p.id)}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Severity</label>
                <select
                  value={addSeverity}
                  onChange={(e) => setAddSeverity(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Rule text</label>
                <textarea
                  value={addClause}
                  onChange={(e) => setAddClause(e.target.value)}
                  placeholder="e.g. All personal data must be encrypted at rest."
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground min-h-[80px]"
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
              <Button onClick={handleAddRule} disabled={addSubmitting}>
                {addSubmitting ? "Adding…" : "Add rule"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </PageTransition>
  );
}
