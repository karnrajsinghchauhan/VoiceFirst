"use client";

import { useCallback } from "react";
import { Badge, Card, Table } from "@/components/ui";
import { useConsole } from "../session";
import { useLoad } from "../use-load";
import { Loaded } from "../loaded";

function mask(bookingId: string): string {
  // 10.4: never show more than the last 4 characters of a booking ID.
  return `${"*".repeat(Math.max(1, bookingId.length - 4))}${bookingId.slice(-4)}`;
}

export default function CallsPage() {
  const { api } = useConsole();
  const live = useLoad(useCallback(() => api.listLiveCalls(), [api])).result;
  const ended = useLoad(useCallback(() => api.listCallOutcomes(), [api])).result;
  const handoffs = useLoad(useCallback(() => api.listHandoffs(), [api])).result;
  return (
    <div className="grid gap-6">
      <Card title="Live calls" testId="live-calls">
        <Loaded result={live}>
          {(calls) =>
            calls.length === 0 ? (
              <p className="text-muted">No live calls.</p>
            ) : (
              <Table
                head={["Call", "Booking", "Purpose", "Language", "Started", "Turns", "Trace"]}
                rows={calls.map((c) => [c.call_id, c.booking_masked, c.purpose, c.language, c.started_at, c.turns, <code key="t">{c.trace_id}</code>])}
              />
            )
          }
        </Loaded>
      </Card>
      <Card title="Recent outcomes">
        <Loaded result={ended}>
          {(rows) => (
            <Table
              head={["Call", "Booking", "Purpose", "Outcome", "Language", "p50 / p95 ms", "Trace"]}
              rows={rows.map((o) => [
                o.call_id,
                mask(o.booking_id),
                o.purpose,
                <Badge key="o" tone={o.outcome === "handed_off" || o.outcome === "error" ? "warn" : "ok"}>
                  {o.outcome}
                </Badge>,
                o.language_detected,
                `${o.latency_ms.p50} / ${o.latency_ms.p95}`,
                <code key="t">{o.trace_id}</code>,
              ])}
            />
          )}
        </Loaded>
      </Card>
      <Card title="Handoffs">
        <Loaded result={handoffs}>
          {(rows) => (
            <ul className="space-y-4">
              {rows.map((h) => (
                <li key={h.call_id} className="rounded border border-line p-3">
                  <p className="text-xs text-muted">
                    {h.queue} / {h.reason} / ack by {h.sla_ack_due_at}
                  </p>
                  <p>
                    <strong>{h.who}</strong>, booking {h.booking_masked}
                  </p>
                  <p>Wants: {h.customer_wants}</p>
                  <p>AI did: {h.ai_did}</p>
                  <p>
                    Sentiment: {h.sentiment}. Policy: {h.policy_refs.join(", ")}
                  </p>
                  <p>Next: {h.next_best_action}</p>
                </li>
              ))}
            </ul>
          )}
        </Loaded>
      </Card>
    </div>
  );
}
