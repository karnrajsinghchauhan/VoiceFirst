"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { can, type Action } from "@/lib/rbac";
import { useConsole } from "./session";

const LINKS: readonly { href: string; label: string; needs: Action }[] = [
  { href: "/console", label: "Campaigns", needs: "view_console" },
  { href: "/console/calls", label: "Calls", needs: "view_calls" },
  { href: "/console/numbers", label: "Numbers", needs: "view_console" },
  { href: "/console/costs", label: "Costs", needs: "view_costs" },
  { href: "/console/kill-switch", label: "Kill switch", needs: "operate_kill_switch" },
  { href: "/console/audit", label: "Audit log", needs: "view_audit" },
  { href: "/console/report", label: "Eval report", needs: "view_report" },
];

export function ConsoleNav() {
  const { identity, mode, signOut } = useConsole();
  const path = usePathname();
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
      <nav className="flex flex-wrap gap-4 text-sm" aria-label="Console">
        {LINKS.filter((l) => can(identity.role, l.needs)).map((l) => (
          <Link
            key={l.href}
            href={l.href}
            aria-current={path === l.href ? "page" : undefined}
            className={path === l.href ? "text-ink underline underline-offset-4" : "motion text-muted hover:text-ink"}
          >
            {l.label}
          </Link>
        ))}
      </nav>
      <div className="flex items-center gap-3 text-xs text-muted">
        {mode === "mock" && <span className="rounded bg-fail-soft px-2 py-0.5 text-fail">mock data</span>}
        <span data-testid="role">
          {identity.actor} ({identity.role})
        </span>
        <button className="underline" onClick={signOut}>
          Sign out
        </button>
      </div>
    </div>
  );
}
