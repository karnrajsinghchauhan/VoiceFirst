"use client";

// One call: the paced timeline and transcript, then the artefacts the engine produced.
import { useState } from "react";
import { EventList, Transcript, runEnd, useElapsed } from "@/components/timeline";
import { Badge, Button } from "@/components/ui";
import type { DemoRun } from "@/lib/demo-types";

export function RunPanels({ run }: { run: DemoRun }) {
  const end = runEnd(run);
  const [skipped, setSkipped] = useState(false);
  const playing = useElapsed(!skipped, end, 1);
  const elapsed = skipped ? end : playing;
  const done = elapsed >= end;
  return (
    <div className="space-y-6" data-testid="run" data-run-id={run.run_id} data-done={done ? "true" : "false"}>
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs text-muted">{run.method}</p>
        {done ? null : (
          <Button variant="outline" onClick={() => setSkipped(true)} data-testid="skip">
            Show all
          </Button>
        )}
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">What the system does</p>
          <div className="mt-3">
            <EventList events={run.events} elapsed={elapsed} />
          </div>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">What the customer hears</p>
          <div className="mt-3">
            {run.transcript.length ? <Transcript run={run} elapsed={elapsed} /> : <p className="text-sm text-muted">No call was placed.</p>}
          </div>
        </div>
      </div>
      {done ? <Artefacts run={run} /> : null}
    </div>
  );
}

function Artefacts({ run }: { run: DemoRun }) {
  const failed = run.qa.checks.filter((c) => !c.passed);
  return (
    <div className="grid gap-4 md:grid-cols-2" data-testid="artefacts">
      <Box title="WhatsApp message">
        {run.whatsapp_preview ? (
          <div data-testid="whatsapp">
            <p className="text-xs text-muted">
              Utility template {run.whatsapp_preview.template} ({run.whatsapp_preview.language})
            </p>
            <p className="mt-2 rounded bg-accent-soft px-3 py-2 [overflow-wrap:anywhere]">{run.whatsapp_preview.body}</p>
          </div>
        ) : (
          <p className="text-muted">None sent.</p>
        )}
      </Box>
      <Box title="CRM ticket">
        {run.crm_ticket ? (
          <p data-testid="crm">
            {run.crm_ticket.ticket_id}: {run.crm_ticket.subject} <Badge tone="muted">{run.crm_ticket.priority}</Badge>
          </p>
        ) : (
          <p className="text-muted">None opened.</p>
        )}
      </Box>
      <Box title="QA score">
        <p data-testid="qa-score">
          <span className="font-display text-2xl">{run.qa.score}</span> / 100 on {run.qa.checks.length} checks
        </p>
        {failed.length ? <p className="mt-1 text-fail">Failed: {failed.map((c) => c.name).join(", ")}</p> : null}
      </Box>
      <Box title="Cost and latency">
        <p data-testid="cost">
          {run.cost_paise.total} paise (telephony {run.cost_paise.telephony}, STT {run.cost_paise.stt}, TTS {run.cost_paise.tts}, LLM{" "}
          {run.cost_paise.llm}, WhatsApp {run.cost_paise.whatsapp})
        </p>
        <p className="mt-1 text-muted" data-testid="latency">
          Engine time per agent turn: {run.latency_ms.per_turn.length ? run.latency_ms.per_turn.join(", ") : "none"} ms
        </p>
      </Box>
    </div>
  );
}

function Box({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded border border-line bg-surface p-4 text-sm">
      <h3 className="text-xs uppercase tracking-wide text-muted">{title}</h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}
