"use client";

// Left: the phone panel (pick a scenario, place the call) and a running campaign with the
// kill switch. Right: the live timeline of what the engine did on that call.
import { useState } from "react";
import { Button } from "@/components/ui";
import { SCENARIOS, type DemoRun, type ScenarioId } from "@/lib/demo-types";
import { paced } from "@/lib/playback";
import { Campaign } from "./campaign";
import { RunPanels } from "./run-panels";
import { postJson } from "./post";

export function DemoApp() {
  const [scenario, setScenario] = useState<ScenarioId>(SCENARIOS[0].id);
  const [run, setRun] = useState<DemoRun | null>(null);
  const [calling, setCalling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function call(): Promise<void> {
    setCalling(true);
    setError(null);
    try {
      setRun(paced(await postJson<DemoRun>("/api/demo/run", { scenario })));
    } catch (e) {
      setError(e instanceof Error ? e.message : "the call could not be placed");
    } finally {
      setCalling(false);
    }
  }

  return (
    <div className="mt-8 grid gap-8 lg:grid-cols-[20rem_1fr]">
      <div className="space-y-6">
        <section className="rounded-2xl border border-line bg-surface p-5" aria-label="Phone">
          <p className="text-xs uppercase tracking-wide text-muted">Scenario</p>
          <fieldset className="mt-3 space-y-1.5">
            <legend className="sr-only">Scenario</legend>
            {SCENARIOS.map((s) => (
              <label key={s.id} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="scenario"
                  value={s.id}
                  checked={scenario === s.id}
                  onChange={() => setScenario(s.id)}
                  data-testid={`scenario-${s.id}`}
                />
                {s.title}
              </label>
            ))}
          </fieldset>
          <Button className="mt-5 w-full" onClick={call} disabled={calling} data-testid="call">
            {calling ? "Calling..." : "Call"}
          </Button>
          {error ? (
            <p role="alert" className="mt-3 text-sm text-fail">
              {error}
            </p>
          ) : null}
        </section>
        <Campaign />
      </div>
      <div>{run ? <RunPanels key={run.run_id} run={run} /> : <EmptyState />}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full min-h-64 items-center justify-center rounded border border-dashed border-line p-8 text-sm text-muted">
      Pick a scenario and press Call. The timeline shows every check and action as the engine reports it.
    </div>
  );
}
