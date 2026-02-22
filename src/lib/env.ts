/**
 * Environment config for backend connection.
 * Set NEXT_PUBLIC_API_URL in .env.local to point to your API (e.g. https://api.example.com).
 * Leave unset to use mock data.
 */
function getApiUrl(): string {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_URL ?? "";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "";
}

export const config = {
  get apiUrl() {
    return getApiUrl().replace(/\/$/, ""); // no trailing slash
  },
  get useMock(): boolean {
    return !getApiUrl();
  },
};
