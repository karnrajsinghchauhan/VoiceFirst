/* Generated from contracts/schemas. Do not edit; run `make gen`. */

/**
 * Immutable; written before any dial, whether or not the call is cleared.
 */
export interface GateDecision {
  schema_version: "1.0.0";
  tenant_id: string;
  trace_id: string;
  decision_id: string;
  booking_event_id: string;
  phone_hash: string;
  evaluated_at: string;
  gates: {
    name:
      | "holdout"
      | "jurisdiction"
      | "kill_switch"
      | "consent"
      | "dnd"
      | "opt_out_lock"
      | "cli_declared"
      | "series"
      | "cli_status"
      | "window"
      | "cap_cooldown";
    passed: boolean;
    reason_code: string;
  }[];
  clearance_id: string | null;
}
