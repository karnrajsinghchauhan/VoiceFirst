"use client";

import { useCallback, useState } from "react";
import { Badge, Button, Card, ConfirmDialog, Table } from "@/components/ui";
import { can } from "@/lib/rbac";
import { useConsole } from "../session";
import { useLoad } from "../use-load";
import { Loaded } from "../loaded";

export default function KillSwitchPage() {
  const { api, identity } = useConsole();
  const allowed = can(identity.role, "operate_kill_switch");
  const state = useLoad(useCallback(() => api.getKillSwitch(), [api]));
  const audit = useLoad(useCallback(() => (allowed ? api.listAudit() : Promise.resolve([])), [api, allowed]));
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!allowed) {
    return (
      <Card title="Kill switch">
        <p className="text-muted">Your role ({identity.role}) cannot operate the kill switch.</p>
      </Card>
    );
  }

  const apply = async (engaged: boolean) => {
    setConfirming(null);
    try {
      await api.setKillSwitch(engaged, reason.trim());
      setReason("");
      setError(null);
      state.reload();
      audit.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="grid gap-6">
      <Card title="Kill switch" testId="kill-switch">
        <Loaded result={state.result}>
          {(ks) => (
            <div>
              <p>
                State:{" "}
                <span data-testid="kill-switch-state">
                  <Badge tone={ks.engaged ? "warn" : "ok"}>{ks.engaged ? "engaged" : "released"}</Badge>
                </span>{" "}
                <span className="text-muted">
                  by {ks.actor} at {ks.changed_at}: {ks.reason}
                </span>
              </p>
              <p className="mt-2 text-muted">
                Engaging pauses every campaign, drops queued dials within five seconds and ends live calls with a short,
                polite close. The action is audit-logged with your name and reason.
              </p>
              <label htmlFor="reason" className="mt-4 block text-xs uppercase tracking-wide text-muted">
                Reason (required)
              </label>
              <input
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="mt-1 w-full rounded border border-line px-3 py-2"
              />
              <div className="mt-4 flex gap-3">
                <Button variant="danger" disabled={ks.engaged || reason.trim() === ""} onClick={() => setConfirming(true)}>
                  Engage kill switch
                </Button>
                <Button variant="outline" disabled={!ks.engaged || reason.trim() === ""} onClick={() => setConfirming(false)}>
                  Release
                </Button>
              </div>
              {error && (
                <p role="alert" className="mt-3 text-warn">
                  {error}
                </p>
              )}
            </div>
          )}
        </Loaded>
      </Card>
      <Card title="Recent audit entries" testId="kill-switch-audit">
        <Loaded result={audit.result}>
          {(rows) => (
            <Table head={["At", "Actor", "Action", "Reason"]} rows={rows.slice(0, 5).map((a) => [a.at, `${a.actor} (${a.role})`, a.action, a.reason])} />
          )}
        </Loaded>
      </Card>
      <ConfirmDialog
        open={confirming !== null}
        title={confirming ? "Engage the kill switch?" : "Release the kill switch?"}
        body={confirming ? "All campaigns pause and live calls end politely." : "Campaigns may resume dialling after release."}
        confirmLabel={confirming ? "Engage" : "Release"}
        onCancel={() => setConfirming(null)}
        onConfirm={() => void apply(confirming === true)}
      />
    </div>
  );
}
