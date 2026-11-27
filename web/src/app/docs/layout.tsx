import Link from "next/link";
import type { ReactNode } from "react";
import { DOCS } from "@/content/docs-nav";

export const metadata = { title: { default: "Docs", template: "%s | Docs" } };

function DocsLinks() {
  return (
    <ul className="space-y-1.5">
      {DOCS.map((d) => (
        <li key={d.slug}>
          <Link href={d.slug ? `/docs/${d.slug}` : "/docs"} className="motion text-muted hover:text-ink">
            {d.title}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function DocsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-page px-6 py-12">
      <details className="mb-8 rounded border border-line bg-surface p-4 text-sm md:hidden">
        <summary className="cursor-pointer">Docs contents</summary>
        <nav aria-label="Docs (mobile)" className="mt-3">
          <DocsLinks />
        </nav>
      </details>
      <div className="flex gap-12">
        <nav aria-label="Docs" className="hidden w-52 shrink-0 text-sm md:block">
          <DocsLinks />
        </nav>
        <article className="prose-av min-w-0 flex-1">{children}</article>
      </div>
    </div>
  );
}
