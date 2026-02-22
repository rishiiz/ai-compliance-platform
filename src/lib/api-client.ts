/**
 * Backend-friendly API client.
 * Uses NEXT_PUBLIC_API_URL when set; otherwise app uses mock data via services.
 */

const defaultHeaders: Record<string, string> = {
  "Content-Type": "application/json",
};

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return defaultHeaders;
  const token = localStorage.getItem("auth_token");
  if (!token) return defaultHeaders;
  return { ...defaultHeaders, Authorization: `Bearer ${token}` };
}

export interface ApiError {
  message: string;
  status?: number;
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = { ...getAuthHeaders(), ...options?.headers } as Record<string, string>;

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      window.dispatchEvent(new CustomEvent("session-expired"));
    }
    const err: ApiError = {
      message: res.statusText || "Request failed",
      status: res.status,
    };
    try {
      const body = await res.json();
      if (body?.detail != null) {
        err.message = typeof body.detail === "string" ? body.detail : body.detail[0]?.msg ?? body.detail[0] ?? err.message;
      } else if (body?.message) {
        err.message = body.message;
      }
    } catch {
      // ignore
    }
    if (res.status === 401 && err.message.toLowerCase().includes("token")) {
      err.message = "Your session expired. Please sign in again.";
    }
    throw err;
  }

  const contentType = res.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return res.text() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};
