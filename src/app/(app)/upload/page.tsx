"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageTransition } from "@/components/layout/page-transition";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileUp, FileText, Check, X, FileArchive } from "lucide-react";
import { cn } from "@/lib/utils";
import { uploadPolicyFile, getSettings } from "@/api";
import { config } from "@/lib/env";
import PolicyZipUpload from "@/components/PolicyZipUpload";


type UploadState = "idle" | "dragging" | "uploading" | "processing" | "complete" | "error";

type ExtractedRule = { id: number; clause: string; severity: string };

const DEFAULT_MAX_FILE_SIZE_MB = 50;
const ALLOWED_EXTENSIONS = [".pdf", ".csv", ".txt"];

function isAllowedPolicyFile(file: File): boolean {
  const name = (file.name || "").toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export default function UploadPage() {
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [progress, setProgress] = useState(0);
  const [fileName, setFileName] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [extractedRules, setExtractedRules] = useState<ExtractedRule[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [maxFileSizeMb, setMaxFileSizeMb] = useState(DEFAULT_MAX_FILE_SIZE_MB);

  useEffect(() => {
    if (!config.apiUrl) return;
    getSettings().then((s) => {
      if ("policy_upload_max_file_size_mb" in s) {
        const val = Number(s.policy_upload_max_file_size_mb) || DEFAULT_MAX_FILE_SIZE_MB;
        setMaxFileSizeMb(Math.max(1, Math.min(500, val)));
      }
    });
  }, []);

  const runUpload = useCallback(async (file: File) => {
    setFileName(file.name);
    setUploadError(null);
    setUploadState("uploading");
    setProgress(0);
    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 8, 85));
    }, 400);
    try {
      if (config.apiUrl) {
        const rules = await uploadPolicyFile(file);
        clearInterval(progressInterval);
        setProgress(100);
        setUploadState("processing");
        await new Promise((r) => setTimeout(r, 200));
        setExtractedRules(
          rules.map((r) => ({
            id: r.id,
            clause:
              (r as { rule_data?: { policy_clause_text?: string } }).rule_data?.policy_clause_text ??
              (r as { policy_clause_text?: string }).policy_clause_text ??
              `Rule ${r.id}`,
            severity: (r.severity || "medium").toLowerCase(),
          }))
        );
      } else {
        await new Promise((r) => setTimeout(r, 800));
        for (let i = 0; i <= 100; i += 10) {
          await new Promise((r) => setTimeout(r, 150));
          setProgress(i);
        }
        setUploadState("processing");
        await new Promise((r) => setTimeout(r, 500));
        setExtractedRules([
          { id: 1, clause: "All personal data must be encrypted at rest using AES-256", severity: "critical" },
          { id: 2, clause: "Data retention periods must not exceed 7 years", severity: "high" },
          { id: 3, clause: "Third-party processors must sign DPAs before data transfer", severity: "high" },
        ]);
      }
      setUploadState("complete");
      setShowPreview(true);
    } catch (e) {
      clearInterval(progressInterval);
      const raw = e instanceof Error ? e.message : "Upload failed";
      const isApiKeyError =
        raw.includes("invalid_api_key") ||
        raw.includes("API key") ||
        raw.includes("Incorrect API key") ||
        raw.includes("GROQ") ||
        raw.includes("401") ||
        raw.includes("authentication");
      setUploadError(
        isApiKeyError
          ? "LLM API error: ensure GROQ_API_KEY is set in backend .env (this app uses Groq + Llama for rule extraction) and restart the server."
          : raw
      );
      setUploadState("error");
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && isAllowedPolicyFile(file)) {
        runUpload(file);
      } else {
        setUploadState("idle");
      }
    },
    [runUpload]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setUploadState("dragging");
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setUploadState("idle");
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file && isAllowedPolicyFile(file)) {
        runUpload(file);
      }
    },
    [runUpload]
  );

  const resetUpload = useCallback(() => {
    setUploadState("idle");
    setProgress(0);
    setFileName(null);
    setShowPreview(false);
    setUploadError(null);
    setExtractedRules([]);
  }, []);

  return (
    <PageTransition>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Upload Policy</h1>
          <p className="mt-1 text-muted-foreground">
            Upload PDF, CSV, or TXT policy documents for AI-powered rule extraction
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="overflow-hidden">
            <CardHeader>
              <h3 className="font-semibold">Policy Document</h3>
              <p className="text-sm text-muted-foreground">
                Drag and drop PDF, CSV, or TXT files or click to browse
              </p>
            </CardHeader>
            <CardContent>
              <motion.div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => uploadState === "idle" && document.getElementById("file-input")?.click()}
                className={cn(
                  "relative flex min-h-[280px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-all duration-300",
                  uploadState === "dragging" && "border-primary bg-primary/5 scale-[1.02]",
                  uploadState === "idle" && "border-muted-foreground/25 hover:border-primary/50 hover:bg-accent/20",
                  (uploadState === "uploading" || uploadState === "processing") && "border-primary/50 bg-accent/10 cursor-wait"
                )}
              >
                <input
                  id="file-input"
                  type="file"
                  accept=".pdf,.csv,.txt"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                <AnimatePresence mode="wait">
                  {uploadState === "idle" && (
                    <motion.div
                      key="idle"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex flex-col items-center gap-4 text-center"
                    >
                      <div className="rounded-full bg-primary/10 p-4">
                        <FileUp className="h-12 w-12 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">Drop PDF, CSV, or TXT here or click to upload</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          Max {maxFileSizeMb}MB. First upload may take 30–90s (AI extraction).
                        </p>
                      </div>
                    </motion.div>
                  )}
                  {(uploadState === "uploading" || uploadState === "processing" || uploadState === "error") && (
                    <motion.div
                      key="uploading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex w-full max-w-sm flex-col gap-4 px-6"
                    >
                      <div className="flex items-center gap-3">
                        <div className="rounded-lg bg-primary/20 p-2">
                          <FileText className="h-8 w-8 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="truncate font-medium">{fileName}</p>
                          <p className="text-sm text-muted-foreground">
                            {uploadState === "error"
                              ? uploadError
                              : uploadState === "uploading"
                                ? "Uploading & processing… (may take 30–90s)"
                                : "Extracting rules with AI…"}
                          </p>
                        </div>
                      </div>
                      {uploadState !== "error" && (
                        <div className="space-y-1">
                          <Progress value={uploadState === "processing" ? 100 : progress} />
                          <p className="text-xs text-muted-foreground">
                            {uploadState === "processing"
                              ? "Almost done…"
                              : "This may take 15–60s for large files."}
                          </p>
                        </div>
                      )}
                      {uploadState === "error" && (
                        <Button onClick={resetUpload} variant="outline" size="sm" className="mt-2">
                          Try again
                        </Button>
                      )}
                    </motion.div>
                  )}
                  {uploadState === "complete" && (
                    <motion.div
                      key="complete"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex flex-col items-center gap-4"
                    >
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", stiffness: 200 }}
                        className="rounded-full bg-emerald-500/20 p-4"
                      >
                        <Check className="h-12 w-12 text-emerald-500" />
                      </motion.div>
                      <div>
                        <p className="font-medium">Upload complete</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {fileName} processed successfully
                        </p>
                      </div>
                      <Button onClick={resetUpload} variant="outline">
                        Upload another
                      </Button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <h3 className="font-semibold">Extracted Rules</h3>
                <p className="text-sm text-muted-foreground">
                  AI-identified compliance rules from your policy
                </p>
              </div>
              {showPreview && (
                <Button size="sm" variant="outline" onClick={() => setShowPreview(false)}>
                  <X className="h-4 w-4 mr-1" />
                  Clear
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {showPreview ? (
                <ScrollArea className="h-[320px]">
                  <div className="space-y-3">
                    {extractedRules.map((rule, i) => (
                      <motion.div
                        key={rule.id}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="rounded-lg border border-border/50 bg-background/50 p-4"
                      >
                        <p className="text-sm font-medium">{rule.clause}</p>
                        <span
                          className={cn(
                            "mt-2 inline-block rounded px-2 py-0.5 text-xs font-medium",
                            rule.severity === "critical" && "bg-red-500/20 text-red-400",
                            rule.severity === "high" && "bg-amber-500/20 text-amber-400",
                            rule.severity === "medium" && "bg-blue-500/20 text-blue-400"
                          )}
                        >
                          {rule.severity}
                        </span>
                      </motion.div>
                    ))}
                  </div>
                </ScrollArea>
              ) : (
                <div className="flex h-[320px] flex-col items-center justify-center rounded-lg border border-dashed border-muted-foreground/25 text-center">
                  <FileText className="h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-2 text-sm text-muted-foreground">
                    Upload a policy to see extracted rules
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── ZIP Bundle Upload ───────────────────────────────────── */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-lg bg-violet-500/10 p-2">
              <FileArchive className="h-5 w-5 text-violet-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight">Upload Policy Bundle (ZIP)</h2>
              <p className="text-sm text-muted-foreground">
                Upload a ZIP containing PDFs, CSVs, and TXT files — each is validated by the AI compliance agent before being pushed to the database
              </p>
            </div>
          </div>
          <Card>
            <CardContent className="pt-6">
              <PolicyZipUpload />
            </CardContent>
          </Card>
        </div>

      </div>
    </PageTransition>
  );
}
