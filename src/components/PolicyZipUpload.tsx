"use client";

import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    FileArchive,
    CheckCircle2,
    XCircle,
    ChevronDown,
    ChevronUp,
    ExternalLink,
    Lightbulb,
    AlertTriangle,
    Loader2,
    FileText,
    FileSpreadsheet,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { uploadPolicyZip, type ZipFileResult, type ZipUploadResponse } from "@/api";
import { config } from "@/lib/env";

type ZipState = "idle" | "dragging" | "uploading" | "complete" | "error";

function FileTypeIcon({ type }: { type: string }) {
    if (type === "pdf") return <FileText className="h-4 w-4 text-red-400 shrink-0" />;
    if (type === "csv") return <FileSpreadsheet className="h-4 w-4 text-emerald-400 shrink-0" />;
    return <FileText className="h-4 w-4 text-blue-400 shrink-0" />;
}

function ScoreBadge({ score }: { score: number }) {
    const pct = Math.round(score * 100);
    const color =
        pct >= 80 ? "text-emerald-400 bg-emerald-500/10" :
            pct >= 65 ? "text-amber-400 bg-amber-500/10" :
                "text-red-400 bg-red-500/10";
    return (
        <span className={cn("rounded px-2 py-0.5 text-xs font-semibold tabular-nums", color)}>
            {pct}%
        </span>
    );
}

function FileResultCard({ result }: { result: ZipFileResult }) {
    const [open, setOpen] = useState(!result.is_compliant);

    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                "rounded-xl border p-4 transition-colors",
                result.is_compliant
                    ? "border-emerald-500/30 bg-emerald-500/5"
                    : "border-red-500/30 bg-red-500/5"
            )}
        >
            {/* Header row */}
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                    <FileTypeIcon type={result.file_type} />
                    <span className="truncate text-sm font-medium">{result.filename}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <ScoreBadge score={result.compliance_score} />
                    {result.is_compliant ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                    ) : (
                        <XCircle className="h-5 w-5 text-red-400" />
                    )}
                </div>
            </div>

            {/* Status line */}
            <p className="mt-2 text-xs text-muted-foreground">
                {result.is_compliant
                    ? `✅ Approved & pushed to database  •  ${result.rules_count ?? 0} rules extracted`
                    : `❌ Not compliant — not added to database`}
            </p>

            {/* Summary */}
            {result.summary && (
                <p className="mt-2 text-xs text-muted-foreground/80 italic line-clamp-2">{result.summary}</p>
            )}

            {/* Storage link */}
            {result.storage_url && (
                <a
                    href={result.storage_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                    <ExternalLink className="h-3 w-3" />
                    View in Supabase Storage
                </a>
            )}

            {/* Error */}
            {result.error && (
                <p className="mt-2 text-xs text-red-400">{result.error}</p>
            )}

            {/* Issues & Suggestions toggle */}
            {!result.is_compliant && (result.issues.length > 0 || result.suggestions.length > 0) && (
                <div className="mt-3">
                    <button
                        onClick={() => setOpen((o) => !o)}
                        className="flex items-center gap-1 text-xs font-medium text-amber-400 hover:text-amber-300 transition-colors"
                    >
                        <Lightbulb className="h-3.5 w-3.5" />
                        AI Suggestions
                        {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                    </button>

                    <AnimatePresence>
                        {open && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: "auto", opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.2 }}
                                className="overflow-hidden"
                            >
                                <div className="mt-3 space-y-3">
                                    {result.issues.length > 0 && (
                                        <div>
                                            <p className="text-xs font-semibold text-red-400 mb-1">Issues found:</p>
                                            <ul className="space-y-1">
                                                {result.issues.map((issue, i) => (
                                                    <li key={i} className="flex gap-2 text-xs text-muted-foreground">
                                                        <AlertTriangle className="h-3.5 w-3.5 text-red-400 shrink-0 mt-0.5" />
                                                        {issue}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {result.suggestions.length > 0 && (
                                        <div>
                                            <p className="text-xs font-semibold text-amber-400 mb-1">Suggested fixes:</p>
                                            <ul className="space-y-1">
                                                {result.suggestions.map((s, i) => (
                                                    <li key={i} className="flex gap-2 text-xs text-muted-foreground">
                                                        <span className="text-amber-400 shrink-0">→</span>
                                                        {s}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            )}
        </motion.div>
    );
}

export default function PolicyZipUpload() {
    const [state, setState] = useState<ZipState>("idle");
    const [progress, setProgress] = useState(0);
    const [zipName, setZipName] = useState<string | null>(null);
    const [response, setResponse] = useState<ZipUploadResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const runUpload = useCallback(async (file: File) => {
        setZipName(file.name);
        setError(null);
        setResponse(null);
        setState("uploading");
        setProgress(0);

        try {
            if (!config.apiUrl) {
                setError("Set NEXT_PUBLIC_API_URL in .env.local to upload policy ZIPs.");
                setState("error");
                return;
            }
            const result = await uploadPolicyZip(file, (pct) => setProgress(pct));
            setResponse(result);
            setState("complete");
        } catch (e) {
            setError(e instanceof Error ? e.message : "ZIP upload failed");
            setState("error");
        }
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setState("idle");
            const file = e.dataTransfer.files[0];
            if (file?.name.toLowerCase().endsWith(".zip")) {
                runUpload(file);
            } else {
                setError("Please drop a .zip file.");
                setState("error");
            }
        },
        [runUpload]
    );

    const reset = useCallback(() => {
        setState("idle");
        setProgress(0);
        setZipName(null);
        setResponse(null);
        setError(null);
        if (inputRef.current) inputRef.current.value = "";
    }, []);

    return (
        <div className="space-y-6">
            {/* Drop zone */}
            <motion.div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setState("dragging"); }}
                onDragLeave={(e) => { e.preventDefault(); setState((s) => s === "dragging" ? "idle" : s); }}
                onClick={() => state === "idle" && inputRef.current?.click()}
                className={cn(
                    "relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed transition-all duration-300 gap-4 p-6",
                    state === "dragging" && "border-violet-500 bg-violet-500/10 scale-[1.02]",
                    state === "idle" && "border-muted-foreground/30 hover:border-violet-500/60 hover:bg-violet-500/5",
                    (state === "uploading") && "border-violet-500/50 bg-violet-500/5 cursor-wait",
                    state === "error" && "border-red-500/50 bg-red-500/5",
                    state === "complete" && "border-emerald-500/50 bg-emerald-500/5",
                )}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept=".zip"
                    className="hidden"
                    onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) runUpload(file);
                    }}
                />

                <AnimatePresence mode="wait">
                    {state === "idle" && (
                        <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-3 text-center">
                            <div className="rounded-full bg-violet-500/10 p-4">
                                <FileArchive className="h-10 w-10 text-violet-400" />
                            </div>
                            <div>
                                <p className="font-semibold text-sm">Drop ZIP bundle here or click to upload</p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                    Supports PDF, CSV, and TXT files inside the ZIP · Max 50 MB
                                </p>
                            </div>
                        </motion.div>
                    )}

                    {state === "dragging" && (
                        <motion.div key="dragging" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-3">
                            <FileArchive className="h-12 w-12 text-violet-400 animate-bounce" />
                            <p className="font-semibold text-sm text-violet-400">Release to upload</p>
                        </motion.div>
                    )}

                    {state === "uploading" && (
                        <motion.div key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex w-full max-w-sm flex-col gap-4">
                            <div className="flex items-center gap-3">
                                <Loader2 className="h-6 w-6 text-violet-400 animate-spin shrink-0" />
                                <div className="min-w-0">
                                    <p className="truncate text-sm font-medium">{zipName}</p>
                                    <p className="text-xs text-muted-foreground">
                                        {progress < 90 ? "Uploading & extracting files…" : "AI compliance validation running…"}
                                    </p>
                                </div>
                            </div>
                            <div className="space-y-1">
                                <Progress value={progress} className="h-2" />
                                <p className="text-xs text-right text-muted-foreground">{progress}%</p>
                            </div>
                        </motion.div>
                    )}

                    {state === "error" && (
                        <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-3 text-center">
                            <XCircle className="h-10 w-10 text-red-400" />
                            <p className="text-sm font-medium text-red-400">{error ?? "Upload failed"}</p>
                            <Button size="sm" variant="outline" onClick={reset}>Try again</Button>
                        </motion.div>
                    )}

                    {state === "complete" && (
                        <motion.div key="complete" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-3 text-center">
                            <CheckCircle2 className="h-10 w-10 text-emerald-400" />
                            <div>
                                <p className="font-semibold text-sm">Processing complete</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                    {response?.compliant_count} compliant · {response?.non_compliant_count} need revision
                                </p>
                            </div>
                            <Button size="sm" variant="outline" onClick={reset}>Upload another ZIP</Button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>

            {/* Results */}
            <AnimatePresence>
                {response && response.results.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="space-y-3"
                    >
                        <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold">
                                Results — {response.files_processed} file{response.files_processed !== 1 ? "s" : ""} processed
                            </h4>
                            <div className="flex gap-3 text-xs text-muted-foreground">
                                <span className="text-emerald-400">✅ {response.compliant_count} approved</span>
                                <span className="text-red-400">❌ {response.non_compliant_count} rejected</span>
                            </div>
                        </div>
                        <ScrollArea className="max-h-[480px] pr-2">
                            <div className="space-y-3">
                                {response.results.map((r, i) => (
                                    <FileResultCard key={i} result={r} />
                                ))}
                            </div>
                        </ScrollArea>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
