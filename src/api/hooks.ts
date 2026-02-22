"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchAnalytics, fetchViolations, fetchRules, fetchNotifications } from "@/api";
import {
  getCached,
  setCached,
  cacheKeyAnalytics,
  cacheKeyNotifications,
  cacheKeyViolations,
  cacheKeyRules,
} from "@/lib/api-cache";
import type { Analytics, Violation, Rule, NotificationItem } from "@/types";

// --- Analytics (dashboard, reports) ---
export function useAnalytics(): {
  data: Analytics | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const cacheKey = cacheKeyAnalytics();
  const cached = getCached<Analytics>(cacheKey);
  const [data, setData] = useState<Analytics | null>(() => cached);
  const [isLoading, setIsLoading] = useState(!cached);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      const d = await fetchAnalytics();
      setData(d);
      setCached(cacheKey, d);
    } catch (e) {
      setError(e instanceof Error ? e : new Error("Failed to load analytics"));
    } finally {
      setIsLoading(false);
    }
  }, [cacheKey]);

  useEffect(() => {
    load(!cached);
  }, []);

  return { data, isLoading, error, refetch: () => load(true) };
}

// --- Notifications ---
export function useNotifications(): {
  data: NotificationItem[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const cacheKey = cacheKeyNotifications();
  const cached = getCached<NotificationItem[]>(cacheKey);
  const [data, setData] = useState<NotificationItem[]>(() => cached ?? []);
  const [isLoading, setIsLoading] = useState(cached === null);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      const d = await fetchNotifications();
      setData(d);
      setCached(cacheKey, d);
    } catch (e) {
      setError(e instanceof Error ? e : new Error("Failed to load notifications"));
    } finally {
      setIsLoading(false);
    }
  }, [cacheKey]);

  useEffect(() => {
    load(cached === null);
  }, []);

  return { data, isLoading, error, refetch: () => load(true) };
}

// --- Violations ---
export function useViolations(params?: {
  severity?: string;
  department?: string;
  search?: string;
}): {
  data: Violation[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const severity = params?.severity;
  const department = params?.department;
  const search = params?.search;
  const cacheKey = cacheKeyViolations(severity, department, search);
  const cached = getCached<Violation[]>(cacheKey);
  const [data, setData] = useState<Violation[]>(() => cached ?? []);
  const [isLoading, setIsLoading] = useState(cached === null);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      const d = await fetchViolations({ severity, department, search });
      setData(d);
      setCached(cacheKey, d);
    } catch (e) {
      setError(e instanceof Error ? e : new Error("Failed to load violations"));
    } finally {
      setIsLoading(false);
    }
  }, [severity, department, search, cacheKey]);

  useEffect(() => {
    const c = getCached<Violation[]>(cacheKey);
    load(c === null);
  }, [cacheKey]);

  return { data, isLoading, error, refetch: () => load(true) };
}

// --- Rules ---
export function useRules(params?: { status?: string; severity?: string }): {
  data: Rule[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
} {
  const status = params?.status;
  const severity = params?.severity;
  const cacheKey = cacheKeyRules(status, severity);
  const cached = getCached<Rule[]>(cacheKey);
  const [data, setData] = useState<Rule[]>(() => cached ?? []);
  const [isLoading, setIsLoading] = useState(cached === null);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      const d = await fetchRules({ status, severity });
      setData(d);
      setCached(cacheKey, d);
    } catch (e) {
      setError(e instanceof Error ? e : new Error("Failed to load rules"));
    } finally {
      setIsLoading(false);
    }
  }, [status, severity, cacheKey]);

  useEffect(() => {
    const c = getCached<Rule[]>(cacheKey);
    load(c === null);
  }, [cacheKey]);

  return { data, isLoading, error, refetch: () => load(true) };
}
