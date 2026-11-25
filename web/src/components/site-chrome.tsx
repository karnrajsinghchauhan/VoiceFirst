import Link from "next/link";
import { DISCLAIMER } from "./disclaimer";

export function SiteHeader() {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-serif text-lg tracking-tight">
          Agoda Voice <span className="text-muted">by ProsperOps</span>
        </Link>
        <nav className="flex gap-5 text-sm text-muted">
          <Link href="/#how" className="hover:text-ink">How it works</Link>
          <Link href="/#pricing" className="hover:text-ink">Pricing</Link>
          <Link href="/docs" className="hover:text-ink">Docs</Link>
          <Link href="/console" className="hover:text-ink">Console</Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto max-w-5xl px-6 py-8 text-sm text-muted">
        <p data-testid="disclaimer">{DISCLAIMER}</p>
        <p className="mt-2">Agoda is a trademark of its owner. Names are used only to describe the intended customer.</p>
      </div>
    </footer>
  );
}
