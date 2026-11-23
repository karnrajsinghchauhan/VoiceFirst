"use client";

import { useCallback } from "react";
import { Badge, Card, Table } from "@/components/ui";
import { useConsole } from "./session";
import { useLoad } from "./use-load";
import { Loaded } from "./loaded";

export default function CampaignsPage() {
  const { api } = useConsole();
  const { result } = useLoad(useCallback(() => api.listCampaigns(), [api]));
  return (
    <Card title="Campaigns" testId="campaigns">
      <Loaded result={result}>
        {(campaigns) => (
          <Table
            head={["Campaign", "Purpose", "Status", "Eligible", "Held out", "Dialled", "Link sent", "Handed off"]}
            rows={campaigns.map((c) => [
              c.name,
              c.purpose,
              <Badge key="s" tone={c.status === "running" ? "ok" : "muted"}>
                {c.status}
              </Badge>,
              c.counts.eligible,
              c.counts.held_out,
              c.counts.dialled,
              c.counts.link_sent,
              c.counts.handed_off,
            ])}
          />
        )}
      </Loaded>
    </Card>
  );
}
