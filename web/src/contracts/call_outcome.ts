/* Generated from contracts/schemas. Do not edit; run `make gen`. */

export interface CallOutcome {
  schema_version: "1.0.0";
  tenant_id: string;
  trace_id: string;
  call_id: string;
  clearance_id: string;
  booking_id: string;
  purpose: "J1" | "J2";
  cli: string;
  started_at: string;
  answered: boolean;
  amd_result: "human" | "machine-ivr" | "machine-vm" | "machine-unavailable" | "uncertain" | "not_run";
  language_detected: "hi" | "en" | "hinglish" | "unknown";
  disclosure_played_at: string | null;
  turns: number;
  tools_called: {
    name:
      | "get_booking_summary"
      | "send_payment_link"
      | "confirm_details"
      | "record_special_request"
      | "log_case"
      | "schedule_callback"
      | "warm_transfer"
      | "mark_dnc"
      | "end_call"
      | "send_app_link";
    args_hash: string;
    result_code: string;
  }[];
  outcome:
    | "link_sent"
    | "details_confirmed"
    | "callback_scheduled"
    | "handed_off"
    | "opted_out"
    | "wrong_person"
    | "minor_on_line"
    | "no_answer"
    | "voicemail"
    | "declined"
    | "abandoned"
    | "error";
  handoff: null | {
    reason: string;
    summary: string;
    queue: string;
  };
  latency_ms: {
    p50: number;
    p95: number;
  };
  /**
   * Minor units (paise).
   */
  cost: {
    telephony: number;
    stt: number;
    tts: number;
    llm: number;
    whatsapp: number;
  };
  redaction_applied: boolean;
  sensitive_data_spoken: boolean;
  /**
   * REQ-CP-03.
   */
  grievance_channel: string;
  /**
   * REQ-AI-01.
   */
  ai_generated: true;
  model_ids: {
    [k: string]: string;
  };
  provenance_hash: string;
}
