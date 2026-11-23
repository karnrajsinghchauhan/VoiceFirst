/* Generated from contracts/schemas. Do not edit; run `make gen`. */

export interface Cli {
  schema_version: "1.0.0";
  tenant_id: string;
  trace_id: string;
  cli_e164: string;
  series: "140" | "1600" | "1601";
  purpose: "service" | "transactional" | "promotional";
  oap: string;
  a2p_declared: boolean;
  declaration_ref: string | null;
  dlt_recorded_at: string | null;
  status: "active" | "paused" | "retired";
  paused_reason: string | null;
}
