// Small primitives written locally so the app has no component-registry dependency.
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "outline" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-paper hover:bg-accent",
  outline: "border border-line bg-surface hover:border-ink",
  danger: "bg-fail text-white hover:opacity-90",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={`motion rounded px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
    />
  );
}

export function Card({ title, children, testId, actions }: { title: string; children: ReactNode; testId?: string; actions?: ReactNode }) {
  return (
    <section className="rounded border border-line bg-surface p-6" data-testid={testId}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-lg">{title}</h2>
        {actions}
      </div>
      <div className="mt-4 text-sm">{children}</div>
    </section>
  );
}

// Green and red carry meaning only: pass/ok and fail/needs attention.
export function Badge({ tone, children }: { tone: "ok" | "warn" | "muted"; children: ReactNode }) {
  const cls = tone === "ok" ? "bg-pass-soft text-pass" : tone === "warn" ? "bg-fail-soft text-fail" : "bg-paper text-muted";
  return <span className={`inline-block rounded px-2 py-0.5 text-xs ${cls}`}>{children}</span>;
}

export function Table({ head, rows, testId }: { head: readonly string[]; rows: readonly (readonly ReactNode[])[]; testId?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm" data-testid={testId}>
        <thead>
          <tr className="border-b border-line text-xs uppercase tracking-wide text-muted">
            {head.map((h) => (
              <th key={h} scope="col" className="py-2 pr-4 font-normal">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-line align-top">
              {r.map((c, j) => (
                <td key={j} className="py-2 pr-4">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-ink/40" role="presentation">
      <div role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-md rounded bg-surface p-6">
        <h2 id="confirm-title" className="font-display text-lg">
          {title}
        </h2>
        <div className="mt-3 text-sm text-muted">{body}</div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} autoFocus>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
