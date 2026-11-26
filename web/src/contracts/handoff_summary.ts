/* Generated from contracts/schemas. Do not edit; run `make gen`. */

/**
 * At most 5 lines, shaped like Agoda's own case summary.
 */
export interface HandoffSummary {
  schema_version: "1.0.0";
  tenant_id: string;
  trace_id: string;
  call_id: string;
  who: string;
  booking_masked: string;
  customer_wants: string;
  ai_did: string;
  sentiment: "calm" | "concerned" | "angry" | "distressed";
  policy_refs: string[];
  next_best_action: string;
  reason: string;
  queue: string;
  /**
   * 48 h acknowledgement (REQ-CP-03).
   */
  sla_ack_due_at: string;
  /**
   * 30-day resolution (REQ-CP-03).
   */
  sla_resolve_due_at: string;
}
