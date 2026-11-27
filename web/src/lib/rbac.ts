// Roles mirror the server's audit roles (contracts/schemas/audit_event.json) minus "system".
// The engine enforces RBAC; this copy keeps the console honest about what it can show.
import type { AuditEvent } from "@/contracts/audit_event";

export type Role = Exclude<AuditEvent["role"], "system">;

export type Action =
  | "view_console"
  | "view_audit"
  | "export_audit"
  | "view_calls"
  | "view_costs"
  | "operate_kill_switch"
  | "view_report";

const GRANTS: Record<Role, readonly Action[]> = {
  admin: ["view_console", "view_audit", "export_audit", "view_calls", "view_costs", "operate_kill_switch", "view_report"],
  ops: ["view_console", "view_audit", "view_calls", "view_costs", "operate_kill_switch", "view_report"],
  auditor: ["view_console", "view_audit", "export_audit", "view_calls", "view_costs", "view_report"],
  read_only: ["view_console", "view_calls", "view_report"],
};

export function isRole(value: unknown): value is Role {
  return value === "admin" || value === "ops" || value === "auditor" || value === "read_only";
}

export function can(role: Role, action: Action): boolean {
  return GRANTS[role].includes(action);
}

export class ForbiddenActionError extends Error {
  constructor(role: Role, action: Action) {
    super(`role ${role} may not ${action}`);
    this.name = "ForbiddenActionError";
  }
}

export function assertCan(role: Role, action: Action): void {
  if (!can(role, action)) throw new ForbiddenActionError(role, action);
}
