"use client";

import { useState } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { Button } from "@/components/ui/button";
import { Download, FileSpreadsheet } from "lucide-react";
import { downloadReport } from "@/api";
import { config } from "@/lib/env";

export default function ReportsPage() {
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = async (format: "pdf" | "csv") => {
    if (!config.apiUrl) {
      setExportError("API not configured. Set NEXT_PUBLIC_API_URL in .env.local.");
      return;
    }
    setExportError(null);
    setExporting(format);
    try {
      await downloadReport(format);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(null);
    }
  };

  return (
    <PageTransition>
      <div className="space-y-8">
        {!config.apiUrl && (
          <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
            <strong>Backend not connected.</strong> Set <strong>NEXT_PUBLIC_API_URL</strong> in <strong>.env.local</strong> (e.g.{" "}
            <code className="rounded bg-muted px-1">http://localhost:8000</code>) and restart the dev server to enable exports.
          </div>
        )}

        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="mt-1 text-muted-foreground">
            Compliance analytics and export options
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button
            onClick={() => handleExport("pdf")}
            disabled={!!exporting}
            variant="gradient"
            className="gap-2"
            id="reports-download-pdf"
          >
            <Download className="h-4 w-4" />
            {exporting === "pdf" ? "Generating…" : "Download PDF Report"}
          </Button>
          <Button
            onClick={() => handleExport("csv")}
            disabled={!!exporting}
            variant="outline"
            className="gap-2"
            id="reports-export-csv"
          >
            <FileSpreadsheet className="h-4 w-4" />
            {exporting === "csv" ? "Exporting…" : "Export CSV"}
          </Button>
        </div>

        {exportError && (
          <p className="text-sm text-destructive">{exportError}</p>
        )}
      </div>
    </PageTransition>
  );
}
