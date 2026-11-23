// Console view types: the shapes the console reads from the engine API (through the
// same-origin proxy at /api/console/*). Contract records come from src/contracts.
import type { CallOutcome } from "@/contracts/call_outcome";
import type { Role } from "./rbac";

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

// The engine attaches the QA scorecard total (S4) to each ended call.
export type CallRow = CallOutcome & { qa_score: number | null };

export interface KillSwitchState {
  engaged: boolean;
  actor: string;
  reason: string;
  changed_at: string;
}

export interface NumberRow {
  cli_e164: string;
  series: "140" | "1600" | "1601";
  purpose: "service" | "transactional" | "promotional";
  oap: string;
  declaration_ref: string | null;
  dlt_recorded_at: string | null;
  status: "active" | "paused" | "retired";
  complaints_10d: number;
  answer_rate: number | null;
  auto_paused: boolean;
  paused_reason: string | null;
}

export interface CostComponent {
  name: string;
  unit: string;
  unit_price: string;
  source_url: string;
  checked_at: string;
  per_minute_paise: number;
  estimate: boolean;
}

export interface CostBreakdown {
  as_of: string;
  currency: "INR";
  components: CostComponent[];
  per_minute_paise: number;
  per_resolved_contact_paise: number;
  assumptions: Record<string, string | number>;
  comparison: { vendor: string; price: string; unit: string; source_url: string; checked_at: string }[];
}

export interface StatusReport {
  overall: "operational" | "degraded" | "down";
  components: { name: string; status: "operational" | "degraded" | "down"; checked_at: string }[];
  history: { date: string; uptime_pct: number }[];
}
