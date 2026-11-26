// The engine finishes a mock call in milliseconds, so a run is paced for people to read:
// checks before the call, then one turn at a time, then what happened after it.
// Only display times change; order and content are exactly what the engine returned.
import type { DemoRun } from "@/lib/demo-types";

const CHECK_MS = 220;
const TURN_MS = 1100;
const AFTER_MS = 350;
const PRE_CALL = new Set(["holdout", "gate", "clearance"]);

export function paced(run: DemoRun): DemoRun {
  const pre = run.events.filter((e) => PRE_CALL.has(e.kind));
  const post = run.events.filter((e) => !PRE_CALL.has(e.kind));
  const callStart = pre.length * CHECK_MS;
  const callEnd = callStart + run.transcript.length * TURN_MS;
  return {
    ...run,
    events: [
      ...pre.map((e, i) => ({ ...e, t_ms: i * CHECK_MS })),
      ...post.map((e, i) => ({ ...e, t_ms: e.kind === "disclosure" ? callStart : callEnd + i * AFTER_MS })),
    ],
    transcript: run.transcript.map((t, i) => ({ ...t, t_ms: callStart + i * TURN_MS })),
  };
}
