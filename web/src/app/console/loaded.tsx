"use client";

import type { ReactNode } from "react";
import type { Load } from "./use-load";

export function Loaded<T>({ result, children }: { result: Load<T>; children: (data: T) => ReactNode }) {
  if (result.state === "loading") return <p className="text-muted">Loading</p>;
  if (result.state === "error")
    return (
      <p role="alert" className="text-fail">
        {result.message}
      </p>
    );
  return <>{children(result.data)}</>;
}
