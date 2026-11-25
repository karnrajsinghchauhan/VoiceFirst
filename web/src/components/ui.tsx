// Small shadcn-style primitives written locally so the app has no registry dependency.
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "outline" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-white hover:opacity-90",
  outline: "border border-line bg-white hover:bg-paper",
  danger: "bg-warn text-white hover:opacity-90",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={`rounded px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
    />
  );
}

export function Card({ title, children, testId }: { title: string; children: ReactNode; testId?: string }) {
  return (
    <section className="rounded border border-line bg-white p-5" data-testid={testId}>
      <h2 className="font-serif text-lg">{title}</h2>
      <div className="mt-3 text-sm">{children}</div>
    </section>
  );
}

export function Badge({ tone, children }: { tone: "ok" | "warn" | "muted"; children: ReactNode }) {
  const cls = tone === "ok" ? "bg-accent-soft text-accent" : tone === "warn" ? "bg-warn-soft text-warn" : "bg-paper text-muted";
  return <span className={`inline-block rounded px-2 py-0.5 text-xs ${cls}`}>{children}</span>;
}

export function Table({ head, rows, testId }: { head: readonly string[]; rows: readonly (readonly ReactNode[])[]; testId?: string }) {
  return (
    <table className="w-full text-left text-sm" data-testid={testId}>
      <thead>
        <tr className="border-b border-line text-xs uppercase tracking-wide text-muted">
          {head.map((h) => (
            <th key={h} className="py-2 pr-4 font-normal">
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
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/30" role="presentation">
      <div role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-md rounded bg-white p-6 shadow">
        <h2 id="confirm-title" className="font-serif text-lg">
          {title}
        </h2>
        <div className="mt-3 text-sm text-muted">{body}</div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
