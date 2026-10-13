"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  intervalMs: number | null = null
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const result = await fetcherRef.current();
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (intervalMs === null) return;
    const id = window.setInterval(() => void refresh(), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs, refresh]);

  return { data, loading, error, refresh };
}