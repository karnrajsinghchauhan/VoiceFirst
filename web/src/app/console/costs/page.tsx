"use client";

import { useCallback } from "react";
import { Badge, Card, Table } from "@/components/ui";
import { can } from "@/lib/rbac";
import { useConsole } from "../session";
import { useLoad } from "../use-load";
import { Loaded } from "../loaded";

function rupees(paise: number): string {
  return `Rs ${(paise / 100).toFixed(2)}`;
}

export default function CostsPage() {
  const { api, identity } = useConsole();
  const allowed = can(identity.role, "view_costs");
  const { result } = useLoad(useCallback(() => (allowed ? api.getCosts() : Promise.reject(new Error(`Your role (${identity.role}) cannot view costs.`))), [api, allowed, identity.role]));
  return (
    <Loaded result={result}>
      {(c) => (
        <div className="grid gap-6">
          <Card title="Cost per minute and per resolved contact" testId="costs">
            <dl className="grid gap-6 md:grid-cols-2">
              <div>
                <dt className="text-muted">Per minute of call</dt>
                <dd className="font-display text-2xl" data-testid="cost-per-minute">{rupees(c.per_minute_paise)}</dd>
              </div>
              <div>
                <dt className="text-muted">Per contact the AI resolves</dt>
                <dd className="font-display text-2xl" data-testid="cost-per-resolved">{rupees(c.per_resolved_contact_paise)}</dd>
              </div>
            </dl>
            <p className="mt-4 text-xs text-muted">
              As of {c.as_of}. Unit prices come from configuration; items marked estimate are not from a dated source. Re-check
              every price before quoting.
            </p>
          </Card>
          <Card title="Components">
            <Table
              testId="cost-components"
              head={["Component", "Unit price", "Unit", "Per minute", "Source", "Checked"]}
              rows={c.components.map((k) => [
                k.name,
                k.unit_price,
                k.unit,
                rupees(k.per_minute_paise),
                k.estimate ? (
                  <Badge key="s" tone="warn">
                    estimate
                  </Badge>
                ) : (
                  <span key="s">{k.source_url}</span>
                ),
                k.checked_at,
              ])}
            />
          </Card>
          <Card title="Assumptions">
            <ul className="list-disc pl-5">
              {Object.entries(c.assumptions).map(([k, v]) => (
                <li key={k}>
                  <code>{k}</code>: {String(v)}
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Published list prices of other platforms">
            <p className="mb-3 text-muted">Shown only as published; not a like-for-like comparison and not re-verified here.</p>
            <Table
              head={["Platform", "Price", "Unit", "Source", "Checked"]}
              rows={c.comparison.map((v) => [v.vendor, v.price, v.unit, v.source_url, v.checked_at])}
            />
          </Card>
        </div>
      )}
    </Loaded>
  );
}
