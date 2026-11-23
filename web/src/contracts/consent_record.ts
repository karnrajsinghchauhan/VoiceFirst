/* Generated from contracts/schemas. Do not edit; run `make gen`. */

export interface ConsentRecord {
  schema_version: "1.0.0";
  tenant_id: string;
  trace_id: string;
  consent_id: string;
  phone_e164: string;
  basis: "transaction" | "explicit" | "inquiry";
  purpose: "J1" | "J2";
  channel: "voice" | "whatsapp" | "sms" | "web" | "dca";
  obtained_at: string;
  /**
   * Null only for basis=transaction, which lasts while the booking is live.
   */
  expires_at: string | null;
  revoked_at: string | null;
  source_ref: string;
  /**
   * REQ-DPDP-08: placeholder for a DPDP Consent Manager.
   */
  consent_manager_id: string | null;
  artefact_ref: string | null;
  evidence_uri: string | null;
}
