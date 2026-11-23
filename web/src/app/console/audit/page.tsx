"use client";

import { useCallback } from "react";
import { Button, Card, Table } from "@/components/ui";
import { auditCsv, auditJson, download } from "@/lib/audit-export";
import { can } from "@/lib/rbac";
import { useConsole } from "../session";
import { useLoad } from "../use-load";
import { Loaded } from "../loaded";

export default function AuditPage() {
  const { api, identity } = useConsole();
  const allowed = can(identity.role, "view_audit");
  const { result } = useLoad(useCallback(() => (allowed ? api.listAudit() : Promise.resolve([])), [api, allowed]));
  if (!allowed) {
    return (
      <Card title="Audit log">
        <p className="text-muted">Your role ({identity.role}) cannot view the audit log.</p>
      </Card>
    );
  }
  const stamp = new Date().toISOString().slice(0, 10);
  return (
    <Loaded result={result}>
      {(rows) => (
        <Card
          title="Audit log"
          testId="audit-log"
          actions={
            can(identity.role, "export_audit") ? (
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => download(`audit-${stamp}.csv`, "text/csv", auditCsv(rows))}>
                  Export CSV
                </Button>
                <Button variant="outline" onClick={() => download(`audit-${stamp}.json`, "application/json", auditJson(rows))}>
                  Export JSON
                </Button>
              </div>
            ) : null
          }
        >
          <Table
            head={["At", "Actor", "Role", "Action", "Target", "Reason", "Trace"]}
            rows={rows.map((a) => [a.at, a.actor, a.role, a.action, a.target, a.reason, <code key="t">{a.trace_id}</code>])}
          />
        </Card>
      )}
    </Loaded>
  );
}
