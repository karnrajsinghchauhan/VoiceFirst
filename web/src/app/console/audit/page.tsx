"use client";

import { useCallback } from "react";
import { Card, Table } from "@/components/ui";
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
  return (
    <Card title="Audit log" testId="audit-log">
      <Loaded result={result}>
        {(rows) => (
          <Table
            head={["At", "Actor", "Role", "Action", "Target", "Reason", "Trace"]}
            rows={rows.map((a) => [a.at, a.actor, a.role, a.action, a.target, a.reason, <code key="t">{a.trace_id}</code>])}
          />
        )}
      </Loaded>
    </Card>
  );
}
