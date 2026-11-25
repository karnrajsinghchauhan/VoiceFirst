// Typed console API client. One interface, two implementations, chosen once from
// NEXT_PUBLIC_AV_API_MODE at build time: "http" talks to the FastAPI server at
// NEXT_PUBLIC_AV_API; "mock" is a deterministic in-browser data layer for dev and tests.
// There is no runtime fallback between them.
import type { AuditEvent } from "@/contracts/audit_event";
import type { CallOutcome } from "@/contracts/call_outcome";
import type { HandoffSummary } from "@/contracts/handoff_summary";
import { assertCan, type Role } from "./rbac";
import { MockBackend } from "./mock-backend";

export interface Identity {
  actor: string;
  role: Role;
}

export interface Campaign {
  campaign_id: string;
  name: string;
  purpose: "J1" | "J2";
  status: "draft" | "running" | "paused";
  created_at: string;
  counts: { eligible: number; held_out: number; dialled: number; link_sent: number; handed_off: number };
}

export interface LiveCall {
  call_id: string;
  trace_id: string;
  booking_masked: string;
  purpose: "J1" | "J2";
  language: CallOutcome["language_detected"];
  started_at: string;
  turns: number;
}

export interface KillSwitchState {
  engaged: boolean;
  actor: string;
  reason: string;
  changed_at: string;
}

export interface ConsoleApi {
  whoami(): Promise<Identity>;
  listCampaigns(): Promise<Campaign[]>;
  listLiveCalls(): Promise<LiveCall[]>;
  listCallOutcomes(): Promise<CallOutcome[]>;
  listHandoffs(): Promise<HandoffSummary[]>;
  listAudit(): Promise<AuditEvent[]>;
  getKillSwitch(): Promise<KillSwitchState>;
  setKillSwitch(engaged: boolean, reason: string): Promise<KillSwitchState>;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

class HttpApi implements ConsoleApi {
  private identity: Identity | null = null;

  constructor(
    private readonly baseUrl: string,
    private readonly token: string,
  ) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: { ...init.headers, authorization: `Bearer ${this.token}`, "content-type": "application/json" },
    });
    if (!res.ok) throw new ApiError(res.status, `${init.method ?? "GET"} ${path} -> ${res.status}`);
    return (await res.json()) as T;
  }

  async whoami(): Promise<Identity> {
    this.identity = await this.request<Identity>("/whoami");
    return this.identity;
  }

  listCampaigns(): Promise<Campaign[]> {
    return this.request("/campaigns");
  }

  listLiveCalls(): Promise<LiveCall[]> {
    return this.request("/calls?state=live");
  }

  listCallOutcomes(): Promise<CallOutcome[]> {
    return this.request("/calls?state=ended");
  }

  listHandoffs(): Promise<HandoffSummary[]> {
    return this.request("/handoff");
  }

  async listAudit(): Promise<AuditEvent[]> {
    assertCan((await this.role()), "view_audit");
    return this.request("/audit");
  }

  getKillSwitch(): Promise<KillSwitchState> {
    return this.request("/killswitch");
  }

  async setKillSwitch(engaged: boolean, reason: string): Promise<KillSwitchState> {
    // The server enforces RBAC too; refusing here keeps the UI honest about what it can do.
    assertCan((await this.role()), "operate_kill_switch");
    return this.request("/killswitch", { method: "POST", body: JSON.stringify({ engaged, reason }) });
  }

  private async role(): Promise<Role> {
    return (this.identity ?? (await this.whoami())).role;
  }
}

class MockApi implements ConsoleApi {
  constructor(
    private readonly backend: MockBackend,
    private readonly token: string,
  ) {}

  async whoami(): Promise<Identity> {
    return this.backend.identify(this.token);
  }

  async listCampaigns(): Promise<Campaign[]> {
    return this.backend.campaigns;
  }

  async listLiveCalls(): Promise<LiveCall[]> {
    return this.backend.liveCalls();
  }

  async listCallOutcomes(): Promise<CallOutcome[]> {
    return this.backend.outcomes;
  }

  async listHandoffs(): Promise<HandoffSummary[]> {
    return this.backend.handoffs;
  }

  async listAudit(): Promise<AuditEvent[]> {
    assertCan(this.backend.identify(this.token).role, "view_audit");
    return this.backend.audit();
  }

  async getKillSwitch(): Promise<KillSwitchState> {
    return this.backend.killSwitch();
  }

  async setKillSwitch(engaged: boolean, reason: string): Promise<KillSwitchState> {
    const who = this.backend.identify(this.token);
    assertCan(who.role, "operate_kill_switch");
    return this.backend.setKillSwitch(who, engaged, reason);
  }
}

export type ApiMode = "http" | "mock";

export function apiMode(): ApiMode {
  const mode = process.env.NEXT_PUBLIC_AV_API_MODE ?? "mock";
  if (mode !== "http" && mode !== "mock") throw new Error(`NEXT_PUBLIC_AV_API_MODE must be http or mock, got ${mode}`);
  return mode;
}

export function makeApi(token: string): ConsoleApi {
  if (apiMode() === "mock") return new MockApi(MockBackend.shared(), token);
  const base = process.env.NEXT_PUBLIC_AV_API;
  if (!base) throw new Error("NEXT_PUBLIC_AV_API is required when NEXT_PUBLIC_AV_API_MODE=http");
  return new HttpApi(base, token);
}
