"use client";

// Replays a DemoRun (live from the engine or recorded from it) as a timeline. Events
// appear when their t_ms has elapsed; the transcript fills in alongside.
import { useEffect, useRef, useState } from "react";
import type { DemoEvent, DemoRun } from "@/lib/demo-types";

const KIND_LABEL: Record<DemoEvent["kind"], string> = {
  holdout: "Holdout",
  gate: "Gate",
  clearance: "Clearance",
  disclosure: "Disclosure",
  tool: "Tool",
  whatsapp: "WhatsApp",
  crm: "CRM",
  qa: "QA",
  cost: "Cost",
  end: "Outcome",
};

function StatusDot({ status }: { status: DemoEvent["status"] }) {
  const cls = status === "pass" ? "bg-pass" : status === "fail" ? "bg-fail" : "bg-line";
  const label = status === "pass" ? "passed" : status === "fail" ? "failed" : "info";
  return <span className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${cls}`} role="img" aria-label={label} />;
}

export function useElapsed(running: boolean, endMs: number, speed: number): number {
  const [elapsed, setElapsed] = useState(0);
  const start = useRef<number | null>(null);
  useEffect(() => {
    if (!running) return;
    start.current = null;
    setElapsed(0);
    let frame = 0;
    const tick = (now: number) => {
      start.current ??= now;
      const t = (now - start.current) * speed;
      setElapsed(Math.min(t, endMs));
      if (t < endMs) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [running, endMs, speed]);
  return elapsed;
}

export function runEnd(run: DemoRun): number {
  return Math.max(...run.events.map((e) => e.t_ms), ...run.transcript.map((t) => t.t_ms)) + 1;
}

export function EventList({ events, elapsed, compact = false }: { events: DemoEvent[]; elapsed: number; compact?: boolean }) {
  const shown = events.filter((e) => e.t_ms <= elapsed);
  return (
    <ol className="space-y-1.5 text-sm" aria-live="polite" data-testid="timeline">
      {shown.map((e, i) => (
        <li key={`${e.t_ms}-${i}`} className="flex gap-3" data-kind={e.kind} data-status={e.status}>
          <StatusDot status={e.status} />
          <span className="w-20 shrink-0 text-xs uppercase tracking-wide text-muted">{KIND_LABEL[e.kind]}</span>
          <span className={compact ? "truncate" : ""}>{e.label}</span>
        </li>
      ))}
    </ol>
  );
}

export function Transcript({ run, elapsed }: { run: DemoRun; elapsed: number }) {
  const shown = run.transcript.filter((t) => t.t_ms <= elapsed);
  return (
    <ol className="space-y-3 text-sm" data-testid="transcript">
      {shown.map((t, i) => (
        <li key={i} className={t.speaker === "agent" ? "pr-8" : "pl-8 text-right"}>
          <span className="block text-xs uppercase tracking-wide text-muted">{t.speaker === "agent" ? "AI assistant" : "Customer"}</span>
          <span className={`mt-1 inline-block rounded px-3 py-2 ${t.speaker === "agent" ? "bg-surface border border-line" : "bg-accent-soft"}`}>
            {t.text}
          </span>
        </li>
      ))}
    </ol>
  );
}

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function HeroCycle({ run, onDone }: { run: DemoRun; onDone: () => void }) {
  const end = runEnd(run);
  const elapsed = useElapsed(true, end, 1);
  useEffect(() => {
    if (elapsed < end) return;
    const t = setTimeout(onDone, 4000);
    return () => clearTimeout(t);
  }, [elapsed, end, onDone]);
  return <HeroPanels run={run} elapsed={elapsed} />;
}

function HeroPanels({ run, elapsed }: { run: DemoRun; elapsed: number }) {
  // Fixed heights: items appear inside the panels without moving anything below them.
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">What the system does</p>
        <div className="mt-3 h-96 overflow-hidden">
          <EventList events={run.events} elapsed={elapsed} compact />
        </div>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">What the customer hears</p>
        <div className="mt-3 h-96 overflow-hidden">
          <Transcript run={run} elapsed={elapsed} />
        </div>
      </div>
    </div>
  );
}

/** Hero: the complete run renders on the server; in the browser it replays on a loop. */
export function HeroTimeline({ run }: { run: DemoRun }) {
  const [cycle, setCycle] = useState<number | null>(null);
  useEffect(() => {
    if (!prefersReducedMotion()) setCycle(0);
  }, []);
  if (cycle === null) return <HeroPanels run={run} elapsed={runEnd(run)} />;
  return <HeroCycle key={cycle} run={run} onDone={() => setCycle((c) => (c ?? 0) + 1)} />;
}
