// Console API client. Talks only to the same-origin proxy (/api/console/*); the proxy holds
// the token in an HttpOnly cookie and decides http-vs-mock on the server (lib/server/engine.ts).
import type { AuditEvent } from "@/contracts/audit_event";
import type { HandoffSummary } from "@/contracts/handoff_summary";
import type { CallRow, Campaign, CostBreakdown, Identity, KillSwitchState, LiveCall, NumberRow } from "./console-types";
import { assertCan, isRole } from "./rbac";

export type { CallRow, Campaign, CostBreakdown, Identity, KillSwitchState, LiveCall, NumberRow } from "./console-types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function csrfToken(): string {
  const m = document.cookie.match(/(?:^|;\s*)av_csrf=([^;]+)/);
  if (!m?.[1]) throw new ApiError(403, "no CSRF cookie; sign in again");
  return m[1];
}

// Every mutation carries the CSRF header, except sign-in, which happens before the cookie exists.
async function call<T>(path: string, init: RequestInit = {}, csrf = (init.method ?? "GET") !== "GET"): Promise<T> {
  const method = init.method ?? "GET";
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (csrf) headers["x-csrf-token"] = csrfToken();
  const res = await fetch(path, { ...init, headers, credentials: "same-origin", cache: "no-store" });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(res.status, body?.detail ?? `${method} ${path} -> ${res.status}`);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export interface SessionInfo {
  identity: Identity;
  mode: "http" | "mock";
}

function asSession(raw: { identity: { actor: unknown; role: unknown }; mode: "http" | "mock" }): SessionInfo {
  if (typeof raw.identity.actor !== "string" || !isRole(raw.identity.role)) throw new ApiError(502, "engine returned an unknown role");
  return { identity: { actor: raw.identity.actor, role: raw.identity.role }, mode: raw.mode };
}

export const session = {
  async current(): Promise<{ info: SessionInfo | null; mode: "http" | "mock" }> {
    const raw = await call<{ identity: { actor: unknown; role: unknown } | null; mode: "http" | "mock" }>("/api/console/session");
    return { info: raw.identity ? asSession({ identity: raw.identity, mode: raw.mode }) : null, mode: raw.mode };
  },
  async signIn(token: string): Promise<SessionInfo> {
    return asSession(await call("/api/console/session", { method: "POST", body: JSON.stringify({ token }) }, false));
  },
  async signOut(): Promise<void> {
    await call("/api/console/session", { method: "DELETE" });
  },
};

export class ConsoleApi {
  constructor(readonly identity: Identity) {}

  listCampaigns(): Promise<Campaign[]> {
    return call("/api/console/campaigns");
  }

  listLiveCalls(): Promise<LiveCall[]> {
    return call("/api/console/calls?state=live");
  }

  listCallOutcomes(): Promise<CallRow[]> {
    return call("/api/console/calls?state=ended");
  }

  listHandoffs(): Promise<HandoffSummary[]> {
    return call("/api/console/handoff");
  }

  listNumbers(): Promise<NumberRow[]> {
    return call("/api/console/numbers");
  }

  getCosts(): Promise<CostBreakdown> {
    assertCan(this.identity.role, "view_costs");
    return call("/api/console/costs");
  }

  listAudit(): Promise<AuditEvent[]> {
    assertCan(this.identity.role, "view_audit");
    return call("/api/console/audit");
  }

  getKillSwitch(): Promise<KillSwitchState> {
    return call("/api/console/killswitch");
  }

  setKillSwitch(engaged: boolean, reason: string): Promise<KillSwitchState> {
    // The engine enforces RBAC too; refusing here keeps the UI honest about what it can do.
    assertCan(this.identity.role, "operate_kill_switch");
    return call("/api/console/killswitch", { method: "POST", body: JSON.stringify({ engaged, reason }) });
  }
}
