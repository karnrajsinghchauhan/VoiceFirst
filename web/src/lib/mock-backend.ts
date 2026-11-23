// Deterministic mock data layer behind ConsoleApi. Seeded data only: no real people,
// bookings or numbers. Mutable state (kill switch, audit log) is persisted to
// sessionStorage so it survives client navigation between console pages.
import type { AuditEvent } from "@/contracts/audit_event";
import type { CallOutcome } from "@/contracts/call_outcome";
import type { HandoffSummary } from "@/contracts/handoff_summary";
import type { Campaign, Identity, KillSwitchState, LiveCall } from "./api";
import type { Role } from "./rbac";

// Mirrors the server's dev tokens (server/app/core/config.py Settings.api_tokens).
const DEV_TOKENS: Record<string, Role> = {
  "dev-admin-token": "admin",
  "dev-ops-token": "ops",
  "dev-auditor-token": "auditor",
  "dev-ro-token": "read_only",
};

const TENANT = "agoda-in";
const HASH = "0".repeat(64);
const STORAGE_KEY = "av-mock-state-v1";

interface MutableState {
  killSwitch: KillSwitchState;
  audit: AuditEvent[];
}

export class UnknownTokenError extends Error {
  constructor() {
    super("unknown token");
    this.name = "UnknownTokenError";
  }
}

function traceId(n: number): string {
  return n.toString(16).padStart(32, "0");
}

function outcome(n: number, partial: Partial<CallOutcome> & Pick<CallOutcome, "outcome" | "purpose">): CallOutcome {
  return {
    schema_version: "1.0.0",
    tenant_id: TENANT,
    trace_id: traceId(n),
    call_id: `call_mock${n}`,
    clearance_id: `clr_mock${n}`,
    booking_id: `BK0000${1000 + n}`,
    cli: "+911600123456",
    started_at: `2026-11-23T0${4 + (n % 5)}:1${n % 10}:00Z`,
    answered: true,
    amd_result: "human",
    language_detected: "hinglish",
    disclosure_played_at: `2026-11-23T0${4 + (n % 5)}:1${n % 10}:01Z`,
    turns: 6,
    tools_called: [],
    handoff: null,
    latency_ms: { p50: 640, p95: 1180 },
    cost: { telephony: 190, stt: 245, tts: 120, llm: 60, whatsapp: 14 },
    redaction_applied: true,
    sensitive_data_spoken: false,
    grievance_channel: "Agoda grievance officer: [CD: grievance contact]",
    ai_generated: true,
    model_ids: { stt: "mock", tts: "mock", llm: "mock" },
    provenance_hash: HASH,
    ...partial,
  };
}

const CAMPAIGNS: Campaign[] = [
  {
    campaign_id: "cmp_j1_pilot",
    name: "J1 payment rescue, pilot",
    purpose: "J1",
    status: "running",
    created_at: "2026-11-20T04:00:00Z",
    counts: { eligible: 1000, held_out: 97, dialled: 612, link_sent: 344, handed_off: 41 },
  },
  {
    campaign_id: "cmp_j2_pilot",
    name: "J2 pre-arrival confirmation, pilot",
    purpose: "J2",
    status: "draft",
    created_at: "2026-11-22T04:00:00Z",
    counts: { eligible: 0, held_out: 0, dialled: 0, link_sent: 0, handed_off: 0 },
  },
];

const OUTCOMES: CallOutcome[] = [
  outcome(1, { purpose: "J1", outcome: "link_sent" }),
  outcome(2, {
    purpose: "J1",
    outcome: "handed_off",
    handoff: { reason: "refund_request", summary: "Customer reports a double debit and wants a refund.", queue: "payments-l2" },
  }),
  outcome(3, { purpose: "J1", outcome: "opted_out" }),
  outcome(4, { purpose: "J2", outcome: "details_confirmed", language_detected: "hi" }),
  outcome(5, { purpose: "J1", outcome: "no_answer", answered: false, amd_result: "not_run", disclosure_played_at: null, turns: 0 }),
];

const HANDOFFS: HandoffSummary[] = [
  {
    schema_version: "1.0.0",
    tenant_id: TENANT,
    trace_id: traceId(2),
    call_id: "call_mock2",
    who: "Booker, first name on record, Hinglish",
    booking_masked: "******1002",
    customer_wants: "Refund of a suspected double debit on a BNPL booking",
    ai_did: "Disclosed AI and recording, confirmed identity, did not discuss refund, logged a case",
    sentiment: "concerned",
    policy_refs: ["P1", "REQ-CP-03"],
    next_best_action: "Check payment gateway for duplicate capture and call back",
    reason: "refund_request",
    queue: "payments-l2",
    sla_ack_due_at: "2026-11-25T05:12:00Z",
    sla_resolve_due_at: "2026-12-23T05:12:00Z",
  },
];

const LIVE: LiveCall[] = [
  {
    call_id: "call_live1",
    trace_id: traceId(101),
    booking_masked: "******2207",
    purpose: "J1",
    language: "hinglish",
    started_at: "2026-11-23T06:29:10Z",
    turns: 3,
  },
];

function initialState(): MutableState {
  return {
    killSwitch: { engaged: false, actor: "system", reason: "initial state", changed_at: "2026-11-20T04:00:00Z" },
    audit: [
      {
        schema_version: "1.0.0",
        tenant_id: TENANT,
        trace_id: traceId(900),
        audit_id: "aud_seed1",
        at: "2026-11-20T04:00:00Z",
        actor: "karn",
        role: "admin",
        action: "campaign.start",
        target: "campaign:cmp_j1_pilot",
        reason: "pilot start",
      },
    ],
  };
}

function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.sessionStorage;
}

export class MockBackend {
  private static instance: MockBackend | null = null;
  private state: MutableState;

  readonly campaigns = CAMPAIGNS;
  readonly outcomes = OUTCOMES;
  readonly handoffs = HANDOFFS;

  private constructor() {
    const saved = storage()?.getItem(STORAGE_KEY);
    this.state = saved ? (JSON.parse(saved) as MutableState) : initialState();
  }

  static shared(): MockBackend {
    MockBackend.instance ??= new MockBackend();
    return MockBackend.instance;
  }

  identify(token: string): Identity {
    const role = DEV_TOKENS[token];
    if (!role) throw new UnknownTokenError();
    return { actor: `${role}-user`, role };
  }

  liveCalls(): LiveCall[] {
    // Engaging the kill switch ends live calls, so the mock shows none.
    return this.state.killSwitch.engaged ? [] : LIVE;
  }

  killSwitch(): KillSwitchState {
    return this.state.killSwitch;
  }

  audit(): AuditEvent[] {
    return [...this.state.audit].sort((a, b) => b.at.localeCompare(a.at));
  }

  setKillSwitch(who: Identity, engaged: boolean, reason: string): KillSwitchState {
    if (reason.trim().length === 0) throw new Error("a reason is required");
    const at = new Date().toISOString();
    this.state.killSwitch = { engaged, actor: who.actor, reason, changed_at: at };
    this.state.audit.push({
      schema_version: "1.0.0",
      tenant_id: TENANT,
      trace_id: traceId(1000 + this.state.audit.length),
      audit_id: `aud_mock${this.state.audit.length + 1}`,
      at,
      actor: who.actor,
      role: who.role,
      action: engaged ? "kill_switch.engage" : "kill_switch.release",
      target: `tenant:${TENANT}`,
      reason,
    });
    storage()?.setItem(STORAGE_KEY, JSON.stringify(this.state));
    return this.state.killSwitch;
  }
}
