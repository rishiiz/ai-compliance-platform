/**
 * API layer: fetches from backend only.
 * Set NEXT_PUBLIC_API_URL (e.g. http://localhost:8000) to connect the frontend to the backend.
 */

import { config } from "@/lib/env";
import { api } from "@/lib/api-client";
import type {
  Analytics,
  Violation,
  Rule,
  Policy,
  LoginResponse,
  LoginCredentials,
  NotificationItem,
} from "@/types";

// --- Backend response shapes ---

interface DashboardSummary {
  total_policies: number;
  total_rules: number;
  total_violations: number;
  pending_violations: number;
  high_severity: number;
  recent_violations: Array<{
    id: number;
    rule_id: number;
    record_id: string;
    status: string;
    severity: string | null;
    explanation: string;
    detected_at: string | null;
  }>;
  last_scan_timestamp: string | null;
  last_scan_status: string | null;
  total_violations_found: number;
  scan_duration_seconds: number | null;
  last_scan_created_at: string | null;
  trend_data: Array<{ date: string; score: number; violations: number }>;
}

interface BackendViolation {
  id: number;
  rule_id: number;
  policy_id: number | null;
  policy_name: string | null;
  record_id: string;
  status: string;
  severity: string | null;
  explanation: string;
  suggested_remediation: string | null;
  policy_clause_text: string | null;
  evidence_snapshot: unknown;
  detected_at: string | null;
  created_at: string | null;
  reviewer_notes: string | null;
}

interface BackendRule {
  id: number;
  policy_id: number;
  policy_name: string | null;
  rule_data: unknown;
  severity: string;
  created_at: string | null;
  policy_clause_text: string;
}

interface BackendPolicy {
  id: number;
  name: string;
  version: number;
  is_active: boolean;
  uploaded_at: string | null;
  rules_count: number;
}

// --- Mappers: backend -> frontend types ---

function mapDashboardToAnalytics(d: DashboardSummary): Analytics {
  const total = d.total_violations || 1;
  const pending = d.pending_violations ?? 0;
  const complianceScore = Math.round(100 - (pending / total) * 100);
  return {
    complianceScore: Number.isFinite(complianceScore) ? complianceScore : 100,
    totalPolicies: d.total_policies,
    activeViolations: d.total_violations,
    criticalAlerts: d.high_severity,
    trendData: d.trend_data ?? [],
    departmentRiskHeatmap: [],
    recentViolations: d.recent_violations.map((v) => ({
      id: String(v.id),
      severity: v.severity ?? "medium",
      department: "—",
      description: v.explanation?.slice(0, 80) ?? "Violation",
    })),
    reportMetrics: {
      policiesReviewed: d.total_policies,
      violationsResolved: d.total_violations - pending,
      averageResolutionTime:
        d.scan_duration_seconds != null ? `${d.scan_duration_seconds}s` : "—",
      complianceTrend: d.last_scan_status === "success" ? "Stable" : "—",
    },
  };
}

function mapViolation(v: BackendViolation): Violation {
  return {
    id: String(v.id),
    ruleId: String(v.rule_id),
    policyId: v.policy_id != null ? String(v.policy_id) : "",
    policyName: v.policy_name ?? "—",
    clause: v.policy_clause_text ?? v.explanation?.slice(0, 100) ?? "—",
    severity: v.severity ?? "medium",
    department: "—",
    discoveredAt: v.detected_at ?? v.created_at ?? "",
    status: v.status,
    evidence:
      typeof v.evidence_snapshot === "object" && v.evidence_snapshot !== null
        ? JSON.stringify(v.evidence_snapshot)
        : String(v.evidence_snapshot ?? ""),
    aiExplanation: v.explanation ?? "",
    suggestedRemediation: v.suggested_remediation ?? undefined,
    affectedResource: v.record_id,
    assignee: v.reviewer_notes ?? "—",
  };
}

function mapRule(r: BackendRule): Rule {
  return {
    id: String(r.id),
    policyId: String(r.policy_id),
    policyName: r.policy_name ?? "—",
    clause: r.policy_clause_text ?? "",
    severity: r.severity,
    status: "active",
    version: "1",
    department: "—",
    createdAt: r.created_at ?? "",
    category: "—",
  };
}

function mapPolicy(p: BackendPolicy): Policy {
  return {
    id: String(p.id),
    name: p.name,
    version: String(p.version),
    status: p.is_active ? "active" : "inactive",
    uploadDate: p.uploaded_at ?? "",
    department: "—",
    rulesCount: p.rules_count,
    lastReviewed: null,
  };
}

// --- Empty / default when no API URL ---

const emptyAnalytics: Analytics = {
  complianceScore: 100,
  totalPolicies: 0,
  activeViolations: 0,
  criticalAlerts: 0,
  trendData: [],
  departmentRiskHeatmap: [],
  recentViolations: [],
  reportMetrics: {
    policiesReviewed: 0,
    violationsResolved: 0,
    averageResolutionTime: "—",
    complianceTrend: "—",
  },
};

// --- API fetchers (backend only) ---

export async function fetchAnalytics(): Promise<Analytics> {
  if (!config.apiUrl) return emptyAnalytics;
  const summary = await api.get<DashboardSummary>("/dashboard/summary");
  return mapDashboardToAnalytics(summary);
}

const SCAN_TIMEOUT_MS = 120_000; // 2 min – scan can run many rules + LLM per violation

/** Run compliance scan against connected database. Returns summary. */
export async function runScan(): Promise<{
  message: string;
  rules_checked: number;
  total_violations: number;
  resolved_count: number;
  by_rule: unknown[];
  scan_duration_seconds?: number;
}> {
  if (!config.apiUrl) throw new Error("API not configured");
  const base = config.apiUrl.replace(/\/$/, "");
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), SCAN_TIMEOUT_MS);
  try {
    const res = await fetch(`${base}/scan/run`, {
      method: "POST",
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      let message = res.statusText || "Scan failed";
      try {
        const body = await res.json();
        if (body?.detail != null) message = typeof body.detail === "string" ? body.detail : body.detail[0]?.msg ?? body.detail[0] ?? message;
      } catch {
        // ignore
      }
      const err = new Error(message) as Error & { status?: number };
      err.status = res.status;
      throw err;
    }
    return res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Scan is taking too long. The backend may still be running—check the server terminal for progress.");
    }
    throw e;
  }
}

/** Get database connection status and last-used details (for pre-fill and "Connected to host / db_name"). */
export async function fetchDatabaseStatus(): Promise<{
  connected: boolean;
  host?: string;
  db_name?: string;
  username?: string;
  port?: string;
  dialect?: string;
}> {
  if (!config.apiUrl) return { connected: false };
  try {
    return await api.get<{ connected: boolean; host?: string; db_name?: string; username?: string; port?: string; dialect?: string }>("/database/status");
  } catch {
    return { connected: false };
  }
}

/** Connect external company database (PostgreSQL, MySQL, or any DB) via credentials. */
export async function connectDatabase(credentials: {
  host: string;
  username: string;
  password: string;
  db_name: string;
  port?: number;
  dialect?: "postgresql" | "mysql";
}): Promise<{ message: string }> {
  if (!config.apiUrl) throw new Error("API not configured");
  return api.post<{ message: string }>("/database/connect", credentials);
}

/** Fetched company database data (after connect): username, host, db_name, count, documents. */
export interface CompanyDatabaseData {
  connected: boolean;
  host?: string;
  db_name?: string;
  username?: string;
  port?: string;
  dialect?: string;
  count?: number;
  documents?: Array<{ id: unknown; title: string | null }>;
  data_error?: string;
}

/** Get company database connection status and fetched data (policy_documents count + list). */
export async function fetchCompanyDatabaseData(): Promise<CompanyDatabaseData> {
  if (!config.apiUrl) return { connected: false };
  try {
    return await api.get<CompanyDatabaseData>("/database/company-data");
  } catch {
    return { connected: false };
  }
}

export async function fetchViolations(params?: {
  severity?: string;
  department?: string;
  search?: string;
}): Promise<Violation[]> {
  if (!config.apiUrl) return [];
  try {
    const searchParams = new URLSearchParams();
    if (params?.severity && params.severity !== "all")
      searchParams.set("severity", params.severity);
    const query = searchParams.toString();
    const list = await api.get<BackendViolation[]>(
      `/violations${query ? `?${query}` : ""}`
    );
    let result = list.map(mapViolation);
    if (params?.search?.trim()) {
      const q = params.search.toLowerCase();
      result = result.filter(
        (v) =>
          v.clause.toLowerCase().includes(q) ||
          v.policyName.toLowerCase().includes(q) ||
          v.aiExplanation.toLowerCase().includes(q)
      );
    }
    return result;
  } catch {
    return [];
  }
}

export async function fetchRules(params?: {
  status?: string;
  severity?: string;
}): Promise<Rule[]> {
  if (!config.apiUrl) return [];
  try {
    const searchParams = new URLSearchParams();
    if (params?.severity && params.severity !== "all")
      searchParams.set("severity", params.severity);
    const query = searchParams.toString();
    const list = await api.get<BackendRule[]>(
      `/rules${query ? `?${query}` : ""}`
    );
    return list.map(mapRule);
  } catch {
    return [];
  }
}

/** Create a rule manually (policy_id, severity, policy_clause_text). */
export async function createRule(body: {
  policy_id: number;
  severity?: string;
  policy_clause_text?: string;
}): Promise<Rule> {
  if (!config.apiUrl) throw new Error("API not configured");
  const created = await api.post<BackendRule>("/rules", {
    policy_id: body.policy_id,
    severity: body.severity ?? "medium",
    policy_clause_text: body.policy_clause_text ?? "",
  });
  return mapRule(created);
}

/** Delete a rule by id. */
export async function deleteRule(ruleId: string): Promise<void> {
  if (!config.apiUrl) throw new Error("API not configured");
  await api.delete(`/rules/${ruleId}`);
}

export async function fetchPolicies(): Promise<Policy[]> {
  if (!config.apiUrl) return [];
  try {
    const list = await api.get<BackendPolicy[]>("/policy");
    return list.map(mapPolicy);
  } catch {
    return [];
  }
}

/** Policy compare response (rule diff + impact). */
export interface PolicyCompareResult {
  old_policy: { id: number; name: string; version: number };
  new_policy: { id: number; name: string; version: number };
  only_in_old: Array<{ id: number; policy_id: number; rule_data: unknown; severity: string; policy_clause_text: string }>;
  only_in_new: Array<{ id: number; policy_id: number; rule_data: unknown; severity: string; policy_clause_text: string }>;
  in_both: Array<{ id: number; policy_id: number; rule_data: unknown; severity: string; policy_clause_text: string }>;
  impact: { new_violations_count: number | null; message: string };
}

/** Compare two policy versions; returns rule diff and optional new violations count. */
export async function fetchPolicyCompare(
  oldPolicyId: string,
  newPolicyId: string,
  computeImpact = true
): Promise<PolicyCompareResult> {
  if (!config.apiUrl) throw new Error("API not configured");
  const params = new URLSearchParams({
    old_policy_id: oldPolicyId,
    new_policy_id: newPolicyId,
    compute_impact: String(computeImpact),
  });
  return api.get<PolicyCompareResult>(`/policy/compare?${params.toString()}`);
}

const ASK_TIMEOUT_MS = 60_000;   // 1 min for Ask (RAG + Groq)
const REINDEX_TIMEOUT_MS = 180_000; // 3 min for reindex (model load + embed)
const HEALTH_CHECK_TIMEOUT_MS = 8_000; // 8 s to see if backend is reachable

/** Check if the backend API is reachable (GET /health, no auth). Use to show "API connected" or "API not reachable". */
export async function fetchApiHealth(): Promise<{ ok: boolean; status?: string }> {
  if (!config.apiUrl) return { ok: false };
  const base = config.apiUrl;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT_MS);
  try {
    const res = await fetch(`${base}/health`, { method: "GET", signal: controller.signal });
    clearTimeout(timeoutId);
    const data = (await res.json()) as { status?: string };
    return { ok: res.ok, status: data?.status };
  } catch {
    clearTimeout(timeoutId);
    return { ok: false };
  }
}

/** RAG: Ask a natural-language question about compliance policy. Requires auth; rate limited. Timeout 1 min. */
export async function fetchPolicyAsk(query: string, policyId: number | null = null): Promise<{ answer: string }> {
  if (!config.apiUrl) throw new Error("API not configured");
  const base = config.apiUrl;
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ASK_TIMEOUT_MS);
  try {
    const res = await fetch(`${base}/policy/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify({ query: query.trim(), policy_id: policyId }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      let message = res.statusText || "Request failed";
      try {
        const body = await res.json();
        if (body?.detail != null) message = typeof body.detail === "string" ? body.detail : body.detail[0]?.msg ?? body.detail[0] ?? message;
      } catch {
        // ignore
      }
      const err: { message: string; status?: number } = { message, status: res.status };
      throw err;
    }
    return res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    if (e && typeof e === "object" && "status" in e) throw e;
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("The request took too long. Please try again or check that policies are indexed.");
    }
    throw e;
  }
}

/** RAG: Get index status (indexed count, total policies with text). Used to show status and auto-trigger reindex. */
export async function fetchPolicyRagStatus(): Promise<{
  indexed_count: number;
  total_with_text: number;
  rag_available?: boolean;
  hint?: string;
}> {
  if (!config.apiUrl) throw new Error("API not configured");
  return api.get<{ indexed_count: number; total_with_text: number; rag_available?: boolean; hint?: string }>("/policy/rag-status");
}

/** RAG: Index all policies that have stored text into the vector store. Timeout 3 min (first run can be slow). */
export async function fetchPolicyReindex(): Promise<{
  indexed: number;
  total_with_text: number;
  rag_available?: boolean;
  hint?: string;
}> {
  if (!config.apiUrl) throw new Error("API not configured");
  const base = config.apiUrl;
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REINDEX_TIMEOUT_MS);
  try {
    const res = await fetch(`${base}/policy/reindex`, {
      method: "POST",
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      let message = res.statusText || "Reindex failed";
      try {
        const body = await res.json();
        if (body?.detail != null) message = typeof body.detail === "string" ? body.detail : body.detail[0]?.msg ?? body.detail[0] ?? message;
      } catch {
        // ignore
      }
      const err: { message: string; status?: number } = { message, status: res.status };
      throw err;
    }
    return res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    if (e && typeof e === "object" && "status" in e) throw e;
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Indexing is taking longer than expected. The backend may still be processing—refresh in a moment or try again.");
    }
    throw e;
  }
}

/** Fetch notifications for bell dropdown. */
export async function fetchNotifications(): Promise<NotificationItem[]> {
  if (!config.apiUrl) return [];
  try {
    const list = await api.get<Array<{ id: number; type: string; title: string; body: string | null; policy_name?: string; read: boolean; created_at: string | null }>>(
      "/notifications"
    );
    return list.map((n) => ({
      id: String(n.id),
      type: (n.type === "critical" || n.type === "warning" || n.type === "success" || n.type === "info" ? n.type : "info") as NotificationItem["type"],
      title: n.title,
      body: n.body ?? null,
      policy_name: n.policy_name ?? undefined,
      read: n.read,
      createdAt: n.created_at ?? "",
    }));
  } catch {
    return [];
  }
}

/** Mark notification as read. */
export async function markNotificationRead(notificationId: string): Promise<void> {
  if (!config.apiUrl) return;
  await api.patch(`/notifications/${notificationId}/read`);
}

/** Upload policy PDF; returns extracted rules from backend. Timeout 3 min (RAG indexing + rule extraction). */
const UPLOAD_TIMEOUT_MS = 180_000;

export async function uploadPolicyFile(file: File): Promise<Array<{ id: number; policy_clause_text?: string; severity: string }>> {
  if (!config.apiUrl) throw new Error("API not configured");
  const formData = new FormData();
  formData.append("file", file);
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);

  try {
    const res = await fetch(`${base}/policy/upload`, {
      method: "POST",
      headers,
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      let message = "Upload failed";
      try {
        const body = await res.json();
        if (body?.detail) message = typeof body.detail === "string" ? body.detail : body.detail[0] ?? message;
      } catch {
        // ignore
      }
      throw new Error(message);
    }
    return res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Upload is taking longer than expected. The server may still be processing—check Rules in a moment.");
    }
    throw e;
  }
}

// --- ZIP Upload types ---
export interface ZipFileResult {
  filename: string;
  file_type: string;
  storage_url: string;
  is_compliant: boolean;
  compliance_score: number;
  summary: string;
  issues: string[];
  suggestions: string[];
  policy_id: number | null;
  rules_count: number | null;
  error: string;
}

export interface ZipUploadResponse {
  zip_filename: string;
  files_processed: number;
  compliant_count: number;
  non_compliant_count: number;
  results: ZipFileResult[];
}

/**
 * Upload a ZIP archive containing policy files (PDF, CSV, TXT).
 * Reports upload progress via onProgress callback (0–100).
 * Returns per-file compliance results from the AI validation agent.
 */
export function uploadPolicyZip(
  file: File,
  onProgress?: (pct: number) => void
): Promise<ZipUploadResponse> {
  return new Promise((resolve, reject) => {
    if (!config.apiUrl) {
      reject(new Error("API not configured"));
      return;
    }
    const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${base}/policy/upload-zip`, true);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 90)); // 90% for upload; last 10% for server processing
      }
    };

    xhr.onload = () => {
      onProgress?.(100);
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as ZipUploadResponse);
        } catch {
          reject(new Error("Invalid response from server"));
        }
      } else {
        let message = "ZIP upload failed";
        try {
          const body = JSON.parse(xhr.responseText);
          if (body?.detail) message = typeof body.detail === "string" ? body.detail : (body.detail[0]?.msg ?? body.detail[0] ?? message);
        } catch {
          // ignore
        }
        reject(new Error(message));
      }
    };

    xhr.onerror = () => reject(new Error("Network error during ZIP upload"));
    xhr.ontimeout = () => reject(new Error("ZIP upload timed out (the server may still be processing)"));
    xhr.timeout = 300_000; // 5 min for large ZIPs with multiple files

    xhr.send(formData);
  });
}


/** Get app settings (email_alerts, slack_webhook, etc.). */
export async function getSettings(): Promise<Record<string, string>> {
  if (!config.apiUrl) return {};
  try {
    return await api.get<Record<string, string>>("/settings");
  } catch {
    return {};
  }
}

/** Update app settings (only provided keys). */
export async function updateSettings(updates: {
  scan_frequency?: string;
  severity_threshold?: number;
  risk_threshold?: number;
  email_alerts?: boolean;
  slack_webhook?: string;
  ai_model?: string;
  confidence_threshold?: number;
  policy_upload_max_file_size_mb?: number;
  policy_upload_max_per_hour?: number;
}): Promise<Record<string, string>> {
  if (!config.apiUrl) return {};
  return api.patch<Record<string, string>>("/settings", updates);
}

/** List users (admin). */
export async function fetchUsers(): Promise<Array<{ id: number; email: string; name: string; role: string; department: string; two_fa_enabled: boolean; created_at: string | null }>> {
  if (!config.apiUrl) return [];
  try {
    return await api.get<Array<{ id: number; email: string; name: string; role: string; department: string; two_fa_enabled: boolean; created_at: string | null }>>("/users");
  } catch {
    return [];
  }
}

/** Create user (admin). Optional password sets their login password. */
export async function createUser(body: { email: string; name: string; role?: string; department?: string; password?: string }): Promise<{ id: number; email: string; name: string; role: string; department: string }> {
  if (!config.apiUrl) throw new Error("API not configured");
  return api.post<{ id: number; email: string; name: string; role: string; department: string }>("/users", {
    email: body.email,
    name: body.name,
    role: body.role ?? "Viewer",
    department: body.department ?? undefined,
    password: body.password ?? undefined,
  });
}

/** Set or reset a user's login password (admin). */
export async function setUserPassword(userId: number, password: string): Promise<{ id: number; email: string; name: string; role: string; department: string }> {
  if (!config.apiUrl) throw new Error("API not configured");
  return api.patch<{ id: number; email: string; name: string; role: string; department: string }>(`/users/${userId}/password`, { password });
}

/** Delete a user (admin only). Fails if deleting the last admin. */
export async function deleteUser(userId: number): Promise<{ ok: boolean; id: number }> {
  if (!config.apiUrl) throw new Error("API not configured");
  return api.delete<{ ok: boolean; id: number }>(`/users/${userId}`);
}

/** Download report as file (PDF or CSV). Triggers browser download; throws on error. */
export async function downloadReport(format: "pdf" | "csv"): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
  if (!base) throw new Error("API not configured");
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${base}/reports/export/${format}`, { headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Export failed");
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition");
  const match = disposition?.match(/filename=(.+)/);
  const filename = match ? match[1].replace(/^["']|["']$/g, "") : `compliance-report.${format === "pdf" ? "pdf" : "csv"}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Update violation status. Backend: PATCH /violations/{id} (status: approved | dismissed). */
export async function updateViolationStatus(
  violationId: string,
  status: "approved" | "dismissed" | "rejected",
  reviewerNotes?: string | null
): Promise<void> {
  if (!config.apiUrl) return;
  const backendStatus = status === "rejected" ? "dismissed" : status;
  await api.patch(`/violations/${violationId}`, {
    status: backendStatus,
    reviewer_notes: reviewerNotes ?? undefined,
  });
}

// --- Auth ---

export async function loginApi(
  credentials: LoginCredentials
): Promise<LoginResponse | null> {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
  if (!base) return null;
  const res = await fetch(`${base}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
      role: credentials.role ?? undefined,
    }),
  });
  if (!res.ok) {
    let message = "Login failed";
    try {
      const body = await res.json();
      if (body?.detail) message = typeof body.detail === "string" ? body.detail : body.detail[0] ?? message;
    } catch {
      // ignore
    }
    const err = new Error(message) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  const data = (await res.json()) as { user: unknown; token: string };
  if (data?.token && typeof window !== "undefined") {
    localStorage.setItem("auth_token", data.token);
  }
  return { user: data.user, token: data.token } as LoginResponse;
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

/** Call backend logout to record "Signed out" in audit; then clear token. */
export async function logoutApi(): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
  if (!base) return;
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  if (!token) return;
  try {
    await fetch(`${base}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    // ignore; still clear token
  }
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("auth_token");
}

// --- Current user (for 2FA status etc.) ---

export interface AuthMeUser {
  id: number;
  email: string;
  name: string;
  role: string;
  department: string;
  two_fa_enabled: boolean;
}

export async function fetchAuthMe(): Promise<AuthMeUser | null> {
  if (!config.apiUrl) return null;
  try {
    const res = await api.get<{ user: AuthMeUser }>("/auth/me");
    return res.user;
  } catch {
    return null;
  }
}

// --- Profile activity (audit log for Recent activity) ---

export interface ProfileActivityItem {
  id: string;
  action: string;
  time: string;
}

const ACTION_LABELS: Record<string, string> = {
  policy_uploaded: "Policy uploaded",
  status_changed: "Violation status updated",
  scan_run: "Compliance scan run",
  login: "Signed in",
  logout: "Signed out",
  password_change: "Password updated",
  password_updated: "Password updated",
  report_viewed: "Report viewed",
  export: "Report exported",
};

function actionTypeToLabel(actionType: string): string {
  return ACTION_LABELS[actionType] ?? actionType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);
  if (diffSec < 60) return "Just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffHr < 24) return `${diffHr} hour${diffHr !== 1 ? "s" : ""} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? "s" : ""} ago`;
  return date.toLocaleDateString();
}

/** Profile activity metrics for current month (logins, reports_viewed, exports). */
export async function fetchProfileMetrics(): Promise<{
  logins: number;
  reports_viewed: number;
  exports: number;
}> {
  if (!config.apiUrl) return { logins: 0, reports_viewed: 0, exports: 0 };
  try {
    return await api.get<{ logins: number; reports_viewed: number; exports: number }>("/profile/metrics");
  } catch {
    return { logins: 0, reports_viewed: 0, exports: 0 };
  }
}

/** Track that the user viewed the Reports page (for activity metrics). */
export async function trackReportViewed(): Promise<void> {
  if (!config.apiUrl) return;
  try {
    await api.post("/profile/track", { action_type: "report_viewed" });
  } catch {
    // ignore
  }
}

/** Fetch recent activity for the current user. Default: last 24 hours, max 50 items. */
export async function fetchProfileActivity(limit = 50, hours = 24): Promise<ProfileActivityItem[]> {
  if (!config.apiUrl) return [];
  try {
    const list = await api.get<Array<{
      id: number;
      action_type: string;
      entity_type: string | null;
      entity_id: string | null;
      performed_by: string | null;
      timestamp: string | null;
      meta: unknown;
    }>>(`/profile/activity?limit=${limit}&hours=${hours}`);
    return list.map((r) => ({
      id: String(r.id),
      action: actionTypeToLabel(r.action_type),
      time: formatRelativeTime(r.timestamp),
    }));
  } catch {
    return [];
  }
}

// --- 2FA ---

export interface TwoFAEnableResult {
  secret: string;
  qr_uri: string;
}

export async function enable2FA(): Promise<TwoFAEnableResult> {
  if (!config.apiUrl) throw new Error("API not configured");
  return api.post<TwoFAEnableResult>("/auth/2fa/enable");
}

export async function verify2FA(code: string): Promise<{ enabled: boolean }> {
  if (!config.apiUrl) throw new Error("API not configured");
  return api.post<{ enabled: boolean }>("/auth/2fa/verify", { code: code.trim() });
}

export async function disable2FA(): Promise<{ enabled: boolean }> {
  if (!config.apiUrl) throw new Error("API not configured");
  return api.post<{ enabled: boolean }>("/auth/2fa/disable");
}

