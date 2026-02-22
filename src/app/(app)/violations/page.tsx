"use client";

import { useState, useMemo } from "react";
import * as Collapsible from "@radix-ui/react-collapsible";
import { motion, AnimatePresence } from "framer-motion";
import { PageTransition } from "@/components/layout/page-transition";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronDown, ChevronRight, Search, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { useViolations } from "@/api/hooks";

export default function ViolationsPage() {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [departmentFilter, setDepartmentFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: violationsData, isLoading, error } = useViolations({
    severity: severityFilter,
    department: departmentFilter,
    search: searchQuery,
  });

  const departments = useMemo(
    () => Array.from(new Set(violationsData.map((v) => v.department))),
    [violationsData]
  );

  const filteredViolations = violationsData;

  const severityStyles: Record<string, string> = {
    critical: "border-l-red-500 bg-red-500/5",
    high: "border-l-amber-500 bg-amber-500/5",
    medium: "border-l-blue-500 bg-blue-500/5",
  };

  const statusColors: Record<string, string> = {
    pending: "warning",
    pending_review: "warning",
    resolved: "success",
    approved: "success",
    dismissed: "destructive",
    rejected: "destructive",
  };

  return (
    <PageTransition>
      <div className="space-y-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Violations</h1>
            <p className="mt-1 text-muted-foreground">
              Track and manage compliance violations across your organization
            </p>
          </div>
        </div>

        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm">What are violations?</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Violations are <strong>records in your connected company database</strong> that break the compliance rules extracted from your policy PDFs. Each row here is one violating record: it shows the <strong>policy rule</strong> (clause), <strong>severity</strong>, <strong>status</strong> (pending / approved / dismissed), <strong>evidence</strong> (the actual data that failed the rule), and an <strong>AI-generated explanation</strong> of why it violates. To see violations: connect your database in Settings → Database, upload policy PDFs to create rules, then run a scan from the Dashboard. You can approve or dismiss each violation in Review.
            </p>
          </CardContent>
        </Card>

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
            {error.message}
          </div>
        )}

        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search violations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2">
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
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All Departments</option>
              {departments.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-4">
          {isLoading && filteredViolations.length === 0 ? (
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <Card key={i}>
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      <Skeleton className="h-5 w-full max-w-md" />
                    </div>
                    <div className="mt-2 flex gap-2">
                      <Skeleton className="h-6 w-16 rounded-full" />
                      <Skeleton className="h-6 w-20 rounded-full" />
                      <Skeleton className="h-4 w-24" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : filteredViolations.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-card p-8 text-center">
              <p className="font-medium text-foreground">No violations yet</p>
              <p className="mt-2 text-sm text-muted-foreground">
                Violations appear here after you connect a company database (Settings → Database), upload policy PDFs to create rules, and run a scan (Dashboard → Run scan now). Each violation is a database record that breaks one of your policy rules.
              </p>
            </div>
          ) : (
          filteredViolations.map((violation) => (
            <div key={violation.id}>
              <Card
                className={cn(
                  "overflow-hidden border-l-4",
                  severityStyles[violation.severity] || "border-l-muted"
                )}
              >
                <Collapsible.Root
                  open={expandedId === violation.id}
                  onOpenChange={(open) =>
                    setExpandedId(open ? violation.id : null)
                  }
                >
                  <Collapsible.Trigger asChild>
                    <button className="w-full text-left">
                      <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                          <div className="flex-1 min-w-0">
                            <p className="font-medium">{violation.clause}</p>
                            <div className="mt-2 flex flex-wrap items-center gap-2">
                              <Badge variant="critical">{violation.severity}</Badge>
                              <Badge
                                variant={
                                  (statusColors[violation.status] as "warning" | "success" | "destructive") ||
                                  "default"
                                }
                              >
                                {violation.status.replace("_", " ")}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                {violation.department} • {violation.policyName}
                              </span>
                              <span className="text-sm text-muted-foreground">
                                • Assigned to {violation.assignee}
                              </span>
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">
                              Discovered:{" "}
                              {new Date(
                                violation.discoveredAt
                              ).toLocaleDateString()}
                            </p>
                          </div>
                          {expandedId === violation.id ? (
                            <ChevronDown className="h-5 w-5 shrink-0" />
                          ) : (
                            <ChevronRight className="h-5 w-5 shrink-0" />
                          )}
                        </div>
                      </CardContent>
                    </button>
                  </Collapsible.Trigger>
                  <AnimatePresence>
                    {expandedId === violation.id && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="space-y-4 border-t border-border/50 bg-muted/10 px-6 py-4">
                          <div>
                            <h4 className="text-sm font-medium text-muted-foreground">
                              Evidence
                            </h4>
                            <p className="mt-1 text-sm">{violation.evidence}</p>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium text-muted-foreground">
                              Affected Resource
                            </h4>
                            <p className="mt-1 font-mono text-sm">
                              {violation.affectedResource}
                            </p>
                          </div>
                          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                            <div className="flex items-center gap-2">
                              <Bot className="h-4 w-4 text-primary" />
                              <h4 className="text-sm font-medium">AI Explanation</h4>
                            </div>
                            <p className="mt-2 text-sm">{violation.aiExplanation}</p>
                          </div>
                          {violation.suggestedRemediation && (
                            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
                              <h4 className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
                                Suggested remediation
                              </h4>
                              <p className="mt-2 text-sm whitespace-pre-wrap">{violation.suggestedRemediation}</p>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Collapsible.Root>
              </Card>
            </div>
          ))
          )}
        </div>
      </div>
    </PageTransition>
  );
}
