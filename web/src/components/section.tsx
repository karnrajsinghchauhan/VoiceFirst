import type { ReactNode } from "react";

// One idea per section: a kicker, a headline, and the content.
export function Section({ id, kicker, title, children }: { id: string; kicker: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="mx-auto max-w-page scroll-mt-8 border-t border-line px-6 py-16 md:py-24">
      <p className="text-xs uppercase tracking-wide text-accent">{kicker}</p>
      <h2 id={`${id}-title`} className="mt-3 max-w-3xl font-display text-2xl tracking-tight md:text-3xl">
        {title}
      </h2>
      <div className="mt-10">{children}</div>
    </section>
  );
}

export function PageHeader({ kicker, title, intro }: { kicker: string; title: string; intro?: ReactNode }) {
  return (
    <header className="mx-auto max-w-page px-6 pb-8 pt-16 md:pt-24">
      <p className="text-xs uppercase tracking-wide text-accent">{kicker}</p>
      <h1 className="mt-3 max-w-3xl font-display text-3xl tracking-tight md:text-4xl">{title}</h1>
      {intro && <div className="mt-6 max-w-2xl text-lg text-muted">{intro}</div>}
    </header>
  );
}
