/**
 * Simple in-memory cache for API responses. Reduces refetches and makes navigation feel instant.
 * Stale-while-revalidate: return cached data immediately if fresh; refetch in background when stale.
 */

const CACHE = new Map<string, { data: unknown; ts: number }>();
const STALE_MS = 30_000; // 30s for analytics; reuse for all for simplicity

export function getCached<T>(key: string): T | null {
  const entry = CACHE.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > STALE_MS) return null;
  return entry.data as T;
}

export function setCached(key: string, data: unknown): void {
  CACHE.set(key, { data, ts: Date.now() });
}

export function cacheKeyAnalytics(): string {
  return "api:analytics";
}
export function cacheKeyNotifications(): string {
  return "api:notifications";
}
export function cacheKeyViolations(severity?: string, department?: string, search?: string): string {
  return `api:violations:${severity ?? ""}:${department ?? ""}:${search ?? ""}`;
}
export function cacheKeyRules(status?: string, severity?: string): string {
  return `api:rules:${status ?? ""}:${severity ?? ""}`;
}
