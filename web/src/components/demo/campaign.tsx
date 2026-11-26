"use client";

// A small running campaign: the engine places one call every two seconds until the kill
// switch stops it. The stop time shown is measured, from the click to the first refused dial.
import { useEffect, useRef, useState } from "react";
import { Badge, Button } from "@/components/ui";
import type { DemoRun, KillSwitchResult, ScenarioId } from "@/lib/demo-types";
import { postJson } from "./post";

const INTERVAL_MS = 2000;
const ROTATION: ScenarioId[] = ["failed_upi", "confirmation", "stop_calling"];

type State = "idle" | "running" | "stopping" | "stopped";

interface Stop {
  engineMs: number;
  endToEndMs: number;
}

export function Campaign() {
  const [state, setState] = useState<State>("idle");
  const [placed, setPlaced] = useState(0);
  const [stop, setStop] = useState<Stop | null>(null);
  const [error, setError] = useState<string | null>(null);
  const live = useRef(false);
  const killedAt = useRef<number | null>(null);
  const engineMs = useRef(0);

  useEffect(() => () => void (live.current = false), []);

  async function loop(): Promise<void> {
    for (let i = 0; live.current; i += 1) {
      const run = await postJson<DemoRun>("/api/demo/run", { scenario: ROTATION[i % ROTATION.length] });
      if (run.transcript.length === 0) {
        // The engine refused to dial: the kill switch has taken effect.
        const startedAt = killedAt.current ?? performance.now();
        setStop({ engineMs: engineMs.current, endToEndMs: Math.round(performance.now() - startedAt) });
        setState("stopped");
        live.current = false;
        return;
      }
      setPlaced((n) => n + 1);
      await new Promise((r) => setTimeout(r, killedAt.current === null ? INTERVAL_MS : 0));
    }
  }

  function guard(p: Promise<unknown>): void {
    p.catch((e: unknown) => {
      live.current = false;
      setState("idle");
      setError(e instanceof Error ? e.message : "request failed");
    });
  }

  function start(): void {
    setError(null);
    setPlaced(0);
    setStop(null);
    killedAt.current = null;
    live.current = true;
    setState("running");
    guard(loop());
  }

  function kill(): void {
    killedAt.current = performance.now();
    setState("stopping");
    guard(
      postJson<KillSwitchResult>("/api/demo/killswitch", {}).then((r) => {
        engineMs.current = r.stopped_in_ms;
      }),
    );
  }

  function release(): void {
    guard(postJson<KillSwitchResult>("/api/demo/killswitch/release", {}).then(() => setState("idle")));
  }

  return (
    <section className="rounded border border-line bg-surface p-5 text-sm" aria-label="Campaign" data-testid="campaign" data-state={state}>
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-wide text-muted">Campaign</p>
        <Badge tone={state === "running" ? "ok" : state === "idle" ? "muted" : "warn"}>{state}</Badge>
      </div>
      <p className="mt-3">
        Calls placed: <span data-testid="placed">{placed}</span>
      </p>
      {stop ? (
        <p className="mt-2" data-testid="stopped">
          Stopped in <span data-testid="stop-ms">{stop.endToEndMs}</span> ms from the click to the first refused dial (engine:{" "}
          {stop.engineMs} ms). Queued calls were dropped.
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        {state === "idle" ? (
          <Button onClick={start} data-testid="start-campaign">
            Start campaign
          </Button>
        ) : null}
        {state === "running" ? (
          <Button variant="danger" onClick={kill} data-testid="kill">
            Kill switch
          </Button>
        ) : null}
        {state === "stopped" ? (
          <Button variant="outline" onClick={release} data-testid="release">
            Release kill switch
          </Button>
        ) : null}
      </div>
      {error ? (
        <p role="alert" className="mt-3 text-fail">
          {error}
        </p>
      ) : null}
    </section>
  );
}
