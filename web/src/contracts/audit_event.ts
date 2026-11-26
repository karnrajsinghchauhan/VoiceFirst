/* Generated from contracts/schemas. Do not edit; run `make gen`. */

/**
 * One privileged action. Append-only.
 */
export interface AuditEvent {
  schema_version: "1.0.0";
  tenant_id: string;
  trace_id: string;
  audit_id: string;
  at: string;
  actor: string;
  role: "admin" | "ops" | "auditor" | "read_only" | "system";
  action: string;
  target: string;
  reason: string;
}
