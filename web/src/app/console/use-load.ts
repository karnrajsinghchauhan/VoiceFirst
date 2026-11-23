"use client";

import { useCallback, useEffect, useState } from "react";

export type Load<T> = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; data: T };

// Errors are shown to the operator, never swallowed into an empty table.
export function useLoad<T>(fetcher: () => Promise<T>): { result: Load<T>; reload: () => void } {
  const [result, setResult] = useState<Load<T>>({ state: "loading" });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    fetcher().then(
      (data) => live && setResult({ state: "ready", data }),
      (e: unknown) => live && setResult({ state: "error", message: e instanceof Error ? e.message : String(e) }),
    );
    return () => {
      live = false;
    };
  }, [fetcher, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { result, reload };
}
