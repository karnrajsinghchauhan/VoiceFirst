/* Generated from contracts/schemas. Do not edit; run `make gen`. */

/**
 * A UCC complaint against one of our CLIs. Accepts DLT-forwarded complaints, including spam reports from call-management apps (REQ-TRAI-10).
 */
export interface Complaint {
  schema_version: "1.0.0";
  tenant_id: string;
  trace_id: string;
  complaint_id: string;
  cli_e164: string;
  complainant_hash: string;
  received_at: string;
  source: "dlt_forwarded" | "call_management_app_via_dlt" | "direct";
  ai_flagged: boolean;
  dlt_ref: string | null;
}
