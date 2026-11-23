import Link from "next/link";
import type { ReactNode } from "react";
import { DOCS } from "@/content/docs-nav";

export const metadata = { title: "Docs | Agoda Voice" };

export default function DocsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto flex max-w-6xl gap-10 px-6 py-10">
      <nav aria-label="Docs" className="hidden w-48 shrink-0 text-sm sm:block">
        <ul className="space-y-1.5">
          {DOCS.map((d) => (
            <li key={d.slug}>
              <Link href={`/docs/${d.slug}`} className="text-muted hover:text-ink">
                {d.title}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <article className="prose-av min-w-0 max-w-3xl flex-1">{children}</article>
    </div>
  );
}
