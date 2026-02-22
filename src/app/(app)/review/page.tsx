"use client";

import { useState, useMemo, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageTransition } from "@/components/layout/page-transition";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Check, X, MessageSquare, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useViolations } from "@/api/hooks";
import { updateViolationStatus } from "@/api";

const auditLog = [
  { id: 1, action: "Violation submitted for review", user: "System", time: "2 hours ago", status: "info" },
  { id: 2, action: "Evidence attached", user: "Sarah Chen", time: "1 hour ago", status: "info" },
  { id: 3, action: "Review initiated", user: "Admin User", time: "30 min ago", status: "info" },
];

export default function ReviewPage() {
  console.count("Review Render");

  const { data: violationsData, isLoading, error, refetch } = useViolations({});

  const pendingViolations = useMemo(
    () => violationsData.filter((v) => v.status === "pending"),
    [violationsData]
  );

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [statusChange, setStatusChange] = useState<string | null>(null);
  const [resolvedIds, setResolvedIds] = useState<Set<string>>(() => new Set());

  const displayViolations = useMemo(
    () => pendingViolations.filter((v) => !resolvedIds.has(v.id)),
    [pendingViolations, resolvedIds]
  );

  const initialSelectedId = displayViolations[0]?.id ?? null;
  const selectedIdResolved = selectedId ?? initialSelectedId;

  const selected = useMemo(
    () => violationsData.find((v) => v.id === selectedIdResolved) ?? null,
    [violationsData, selectedIdResolved]
  );

  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const actionRef = useRef<{ id: string; nextId: string | null } | null>(null);

  const handleApprove = useCallback(async () => {
    if (!selectedIdResolved) return;
    const nextId = displayViolations.find((v) => v.id !== selectedIdResolved)?.id ?? null;
    actionRef.current = { id: selectedIdResolved, nextId };
    setStatusChange("approved");

    try {
      await updateViolationStatus(selectedIdResolved, "approved", comment || undefined);
    } catch {
      // keep UI optimistic; refetch will correct state
    }

    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      const payload = actionRef.current;
      if (payload) {
        setResolvedIds((prev) => {
          const next = new Set(prev);
          next.add(payload.id);
          return next;
        });
        setSelectedId(payload.nextId);
      }
      setStatusChange(null);
      setComment("");
      actionRef.current = null;
      timeoutRef.current = null;
      refetch();
    }, 600);
  }, [selectedIdResolved, displayViolations, comment, refetch]);

  const handleReject = useCallback(async () => {
    if (!selectedIdResolved) return;
    const nextId = displayViolations.find((v) => v.id !== selectedIdResolved)?.id ?? null;
    actionRef.current = { id: selectedIdResolved, nextId };
    setStatusChange("rejected");

    try {
      await updateViolationStatus(selectedIdResolved, "rejected", comment || undefined);
    } catch {
      // keep UI optimistic; refetch will correct state
    }

    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      const payload = actionRef.current;
      if (payload) {
        setResolvedIds((prev) => {
          const next = new Set(prev);
          next.add(payload.id);
          return next;
        });
        setSelectedId(payload.nextId);
      }
      setStatusChange(null);
      setComment("");
      actionRef.current = null;
      timeoutRef.current = null;
      refetch();
    }, 600);
  }, [selectedIdResolved, displayViolations, comment, refetch]);

  if (isLoading && violationsData.length === 0) {
    return (
      <PageTransition>
        <div className="space-y-8">
          <div className="h-9 w-64 animate-pulse rounded bg-muted" />
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="h-64 animate-pulse rounded-lg bg-muted lg:col-span-2" />
            <div className="h-64 animate-pulse rounded-lg bg-muted" />
          </div>
        </div>
      </PageTransition>
    );
  }
  if (error) {
    return (
      <PageTransition>
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-destructive">
          {error.message}
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Review</h1>
          <p className="mt-1 text-muted-foreground">
            Approve or reject compliance violations with reviewer comments
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            {selected ? (
              <AnimatePresence mode="wait">
                <motion.div
                  key={selected.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <Card>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-semibold">Violation Details</h3>
                          <Badge variant="critical" className="mt-2">
                            {selected.severity}
                          </Badge>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {selected.id}
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <h4 className="text-sm font-medium text-muted-foreground">
                          Policy Clause
                        </h4>
                        <p className="mt-1">{selected.clause}</p>
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-muted-foreground">
                          Evidence
                        </h4>
                        <p className="mt-1 text-sm">{selected.evidence}</p>
                      </div>
                      <div>
                        <h4 className="text-sm font-medium text-muted-foreground">
                          AI Explanation
                        </h4>
                        <p className="mt-1 text-sm">{selected.aiExplanation}</p>
                      </div>
                      {selected.suggestedRemediation && (
                        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                          <h4 className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
                            Suggested remediation
                          </h4>
                          <p className="mt-2 text-sm whitespace-pre-wrap">{selected.suggestedRemediation}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </AnimatePresence>
            ) : (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                  <Check className="h-12 w-12 text-emerald-500" />
                  <p className="mt-4 font-medium">All caught up!</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    No violations pending review
                  </p>
                </CardContent>
              </Card>
            )}

            {selected && (
              <Card>
                <CardHeader>
                  <h3 className="font-semibold flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    Reviewer Comment
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Add a comment for the audit log (optional)
                  </p>
                </CardHeader>
                <CardContent>
                  <Input
                    placeholder="Enter your review comment..."
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    className="mb-4"
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={handleApprove}
                      disabled={!!statusChange}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                    >
                      {statusChange === "approved" ? (
                        <span className="flex items-center gap-2">
                          <Check className="h-4 w-4" /> Approved
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <Check className="h-4 w-4" /> Approve
                        </span>
                      )}
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleReject}
                      disabled={!!statusChange}
                      className="flex-1"
                    >
                      {statusChange === "rejected" ? (
                        <span className="flex items-center gap-2">
                          <X className="h-4 w-4" /> Rejected
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <X className="h-4 w-4" /> Reject
                        </span>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <h3 className="font-semibold">Pending Review</h3>
                <p className="text-sm text-muted-foreground">
                  {displayViolations.length} violations
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {displayViolations.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      onClick={() => setSelectedId(v.id)}
                      className={cn(
                        "w-full rounded-lg px-4 py-3 text-left transition-colors",
                        selectedIdResolved === v.id
                          ? "bg-primary/15 text-primary"
                          : "hover:bg-accent/50"
                      )}
                    >
                      <p className="text-sm font-medium line-clamp-1">
                        {v.clause}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {v.department}
                      </p>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h3 className="font-semibold flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Audit Log
                </h3>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {auditLog.map((entry) => (
                    <div
                      key={entry.id}
                      className="flex gap-3 border-l-2 border-muted pl-4"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{entry.action}</p>
                        <p className="text-xs text-muted-foreground">
                          {entry.user} • {entry.time}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
