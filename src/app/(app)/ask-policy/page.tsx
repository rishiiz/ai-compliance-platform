"use client";

import { useState, useCallback, useEffect } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { fetchPolicies, fetchPolicyAsk, fetchPolicyRagStatus, fetchPolicyReindex } from "@/api";
import { config } from "@/lib/env";
import type { ApiError } from "@/lib/api-client";
import { MessageCircle, Lock } from "lucide-react";

function getErrorMessage(e: unknown): string {
  if (e && typeof e === "object" && "message" in e && typeof (e as ApiError).message === "string") {
    return (e as ApiError).message;
  }
  if (e instanceof Error) return e.message;
  return "Request failed";
}

export default function AskPolicyPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [policyId, setPolicyId] = useState<string>("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | undefined>(undefined);
  const [policies, setPolicies] = useState<{ id: string; name: string; version: string }[]>([]);
  const [reindexing, setReindexing] = useState(false);
  const [reindexResult, setReindexResult] = useState<{
    indexed: number;
    total_with_text: number;
    hint?: string;
  } | null>(null);
  const [reindexError, setReindexError] = useState<string | null>(null);
  const [reindexErrorStatus, setReindexErrorStatus] = useState<number | undefined>(undefined);
  const [ragStatus, setRagStatus] = useState<{
    indexed_count: number;
    total_with_text: number;
    hint?: string;
  } | null>(null);
  const [autoIndexing, setAutoIndexing] = useState(false);

  useEffect(() => {
    if (!config.apiUrl) return;
    fetchPolicies()
      .then((list) =>
        setPolicies(
          list.map((p) => ({
            id: p.id,
            name: p.name,
            version: p.version,
          }))
        )
      )
      .catch(() => setPolicies([]));
  }, []);

  // Fetch RAG status on load; if policies exist but none indexed, auto-trigger reindex in background
  useEffect(() => {
    if (!config.apiUrl) return;
    fetchPolicyRagStatus()
      .then((status) => {
        setRagStatus({
          indexed_count: status.indexed_count,
          total_with_text: status.total_with_text,
          hint: status.hint,
        });
        if (status.total_with_text > 0 && status.indexed_count < status.total_with_text) {
          setAutoIndexing(true);
          setReindexError(null);
          fetchPolicyReindex()
            .then((res) => {
              setRagStatus((prev) =>
                prev ? { ...prev, indexed_count: res.indexed, total_with_text: res.total_with_text, hint: res.hint } : { indexed_count: res.indexed, total_with_text: res.total_with_text, hint: res.hint }
              );
              setReindexResult(res);
            })
            .catch((e) => {
              const msg = e && typeof e === "object" && "message" in e ? (e as ApiError).message : "Indexing failed";
              setReindexError(msg);
              setReindexResult({ indexed: 0, total_with_text: status.total_with_text, hint: status.hint });
            })
            .finally(() => setAutoIndexing(false));
        }
      })
      .catch(() => {});
  }, [config.apiUrl]);

  const handleAsk = useCallback(async () => {
    const q = query.trim();
    if (!q) {
      setError("Enter a question.");
      return;
    }
    setError(null);
    setErrorStatus(undefined);
    setAnswer(null);
    setLoading(true);
    try {
      const res = await fetchPolicyAsk(q, policyId ? Number(policyId) : null);
      setAnswer(res.answer);
    } catch (e) {
      const msg = getErrorMessage(e);
      const status = e && typeof e === "object" && "status" in e ? (e as ApiError).status : undefined;
      setErrorStatus(status);
      if (status === 401) {
        setError("Please sign in again. " + msg);
      } else if (status === 429) {
        setError(msg);
      } else if (status === 502) {
        setError("Answer could not be generated. Ensure GROQ_API_KEY is set in the backend and policies are indexed for RAG. " + msg);
      } else if (msg.includes("too long") || msg.includes("timed out")) {
        setError(msg + " If policies were just indexed, wait a moment and try again.");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [query, policyId]);

  const handleReindex = useCallback(async () => {
    if (!config.apiUrl) return;
    setReindexError(null);
    setReindexErrorStatus(undefined);
    setReindexResult(null);
    setReindexing(true);
    try {
      const res = await fetchPolicyReindex();
      setReindexResult(res);
      setRagStatus((prev) =>
        prev ? { ...prev, indexed_count: res.indexed, total_with_text: res.total_with_text, hint: res.hint } : { indexed_count: res.indexed, total_with_text: res.total_with_text, hint: res.hint }
      );
    } catch (e) {
      const msg = e && typeof e === "object" && "message" in e ? (e as ApiError).message : "Reindex failed";
      const status = e && typeof e === "object" && "status" in e ? (e as ApiError).status : undefined;
      setReindexErrorStatus(status);
      const displayMsg = status === 401 ? "Please sign in again. " + msg : msg;
      setReindexError(displayMsg + (msg.includes("longer than expected") ? " You can refresh the page in a minute to check status." : ""));
    } finally {
      setReindexing(false);
    }
  }, []);

  if (user?.role === "viewer") {
    return (
      <PageTransition>
        <div className="flex min-h-[50vh] flex-col items-center justify-center space-y-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
            <Lock className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-bold tracking-tight">Access restricted</h1>
            <p className="text-muted-foreground max-w-sm">
              Ask policy is available to Admin and Compliance Officer roles only. Viewers can access Dashboard, Profile, and Reports.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link href="/dashboard">Go to Dashboard</Link>
          </Button>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ask policy</h1>
          <p className="mt-1 text-muted-foreground">
            Ask a question about your compliance policies. Answers are based only on uploaded policy text (RAG).
          </p>
        </div>

        {!config.apiUrl && (
          <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
            <strong>Backend not connected.</strong> Set <strong>NEXT_PUBLIC_API_URL</strong> in <strong>.env.local</strong> to use Ask policy.
          </div>
        )}

        {config.apiUrl && policies.length > 0 && (
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground mb-3">
                Already uploaded policies? Index them so Ask policy can search their text (RAG).
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleReindex}
                disabled={reindexing || autoIndexing}
              >
                {reindexing ? "Indexing…" : autoIndexing ? "Indexing in background…" : "Index existing policies"}
              </Button>
              <p className="mt-1.5 text-xs text-muted-foreground">
                First time may take 1–2 min (model download). Later runs are faster. Indexing can start automatically when you open this page.
              </p>
              {(ragStatus !== null || reindexResult !== null) && (
                <div className="mt-2 space-y-2">
                  <p className="text-sm text-foreground">
                    {(() => {
                      const total = ragStatus?.total_with_text ?? reindexResult?.total_with_text ?? 0;
                      const indexed = ragStatus?.indexed_count ?? reindexResult?.indexed ?? 0;
                      if (total === 0)
                        return "No policies have stored text yet. Upload policy PDFs (Upload Policy) so they can be indexed for Q&A.";
                      if (indexed === total)
                        return `Indexed ${indexed} of ${total} policies. Try asking a question now.`;
                      return `Indexed ${indexed} of ${total} policies.`;
                    })()}
                  </p>
                  {ragStatus && ragStatus.indexed_count === 0 && ragStatus.total_with_text > 0 && ragStatus.hint && (
                    <div className="rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-400">
                      {ragStatus.hint}
                    </div>
                  )}
                  {reindexResult?.indexed === 0 && (reindexResult?.total_with_text ?? 0) > 0 && reindexResult?.hint && !ragStatus?.hint && (
                    <div className="rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-400">
                      {reindexResult.hint}
                    </div>
                  )}
                </div>
              )}
              {reindexError && (
                <div className="mt-2 text-sm text-destructive space-y-2">
                  <p>{reindexError}</p>
                  {reindexErrorStatus === 401 && (
                    <Link href="/login" className="inline-block font-medium text-primary underline underline-offset-2 hover:no-underline">
                      Sign in again
                    </Link>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <h3 className="font-semibold flex items-center gap-2">
              <MessageCircle className="h-4 w-4" />
              Ask about compliance
            </h3>
            <p className="text-sm text-muted-foreground">
              Example: &quot;What is the data retention period?&quot; or &quot;When must training be completed?&quot; If the index is still building, answers use policy text directly so you can ask right away.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-foreground">Question</label>
              <textarea
                className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                rows={3}
                placeholder="e.g. What is the maximum retention period for personal data?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                maxLength={500}
              />
              <p className="mt-1 text-xs text-muted-foreground">Max 500 characters. Rate limit applies per user.</p>
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">Scope to policy (optional)</label>
              <select
                className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={policyId}
                onChange={(e) => setPolicyId(e.target.value)}
              >
                <option value="">All policies</option>
                {policies.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (v{p.version})
                  </option>
                ))}
              </select>
            </div>
            {error && (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive space-y-2">
                <p>{error}</p>
                {errorStatus === 401 && (
                  <Link href="/login" className="inline-block font-medium text-primary underline underline-offset-2 hover:no-underline">
                    Sign in again
                  </Link>
                )}
              </div>
            )}
            <Button onClick={handleAsk} disabled={loading || !config.apiUrl}>
              {loading ? "Asking…" : "Ask"}
            </Button>
            {answer !== null && (
              <div className="rounded-md border border-border bg-muted/30 p-4">
                <p className="text-sm font-medium text-foreground mb-2">Answer</p>
                <p className="text-sm text-foreground whitespace-pre-wrap">{answer}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
