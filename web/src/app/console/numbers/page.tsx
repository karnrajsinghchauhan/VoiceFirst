"use client";

import { useCallback } from "react";
import { Badge, Card, Table } from "@/components/ui";
import { useConsole } from "../session";
import { useLoad } from "../use-load";
import { Loaded } from "../loaded";

export default function NumbersPage() {
  const { api } = useConsole();
  const { result } = useLoad(useCallback(() => api.listNumbers(), [api]));
  return (
    <Card title="Numbers" testId="numbers">
      <p className="mb-4 text-muted">
        Every caller ID the system can dial from. A complaint pauses the number automatically; a paused number cannot be
        cleared for a call until an operator reviews it.
      </p>
      <Loaded result={result}>
        {(rows) => (
          <Table
            head={["Caller ID", "Series", "Purpose", "Operator", "A2P declaration", "Status", "Complaints (rolling window)", "Answer rate", "Auto-pause"]}
            rows={rows.map((n) => [
              <code key="c">{n.cli_e164}</code>,
              n.series,
              n.purpose,
              n.oap,
              n.declaration_ref ? (
                <span key="d">
                  {n.declaration_ref}
                  <span className="block text-xs text-muted">{n.dlt_recorded_at?.slice(0, 10) ?? "no date"}</span>
                </span>
              ) : (
                <Badge key="d" tone="warn">
                  not declared
                </Badge>
              ),
              <Badge key="s" tone={n.status === "active" ? "ok" : "warn"}>
                {n.status}
              </Badge>,
              n.complaints_10d,
              n.answer_rate === null ? "none yet" : `${Math.round(n.answer_rate * 100)}%`,
              n.auto_paused ? (
                <span key="p">
                  paused<span className="block text-xs text-muted">{n.paused_reason}</span>
                </span>
              ) : (
                "no"
              ),
            ])}
          />
        )}
      </Loaded>
    </Card>
  );
}
