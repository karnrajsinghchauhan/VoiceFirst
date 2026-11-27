// Audit log export (S7): CSV and JSON of every privileged action, built in the browser from GET /audit.
import type { AuditEvent } from "@/contracts/audit_event";

const COLUMNS = ["at", "actor", "role", "action", "target", "reason", "trace_id", "audit_id", "tenant_id"] as const;

function csvCell(value: string): string {
  // Quote everything; a leading = + - @ would be read as a formula by spreadsheet apps.
  const safe = /^[=+\-@]/.test(value) ? `'${value}` : value;
  return `"${safe.replace(/"/g, '""')}"`;
}

export function auditCsv(rows: readonly AuditEvent[]): string {
  const lines = [COLUMNS.join(",")];
  for (const r of rows) lines.push(COLUMNS.map((c) => csvCell(String(r[c]))).join(","));
  return `${lines.join("\n")}\n`;
}

export function auditJson(rows: readonly AuditEvent[]): string {
  return `${JSON.stringify(rows, null, 2)}\n`;
}

export function download(name: string, type: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
