import Link from "next/link";
import { BRAND, disclaimer } from "@/config/brand";

const NAV: readonly { href: string; label: string }[] = [
  { href: "/voice", label: "Voice" },
  { href: "/voice/product", label: "Product" },
  { href: "/voice/security", label: "Security" },
  { href: "/voice/pricing", label: "Pricing" },
  { href: "/docs", label: "Docs" },
  { href: "/voice/changelog", label: "Changelog" },
  { href: "/company", label: "Company" },
];

export function SiteHeader() {
  return (
    <header data-site-header className="border-b border-line bg-paper">
      <div className="mx-auto flex max-w-page flex-wrap items-center justify-between gap-4 px-6 py-4">
        <Link href="/" className="font-display text-lg font-semibold tracking-tight" data-testid="brand">
          {BRAND.name}
        </Link>
        <nav aria-label="Main" className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="motion text-muted hover:text-ink">
              {n.label}
            </Link>
          ))}
          <Link
            href="/voice#book"
            className="motion rounded border border-ink px-3 py-1.5 text-ink hover:bg-ink hover:text-paper"
          >
            Book a call
          </Link>
        </nav>
      </div>
    </header>
  );
}

const LEGAL: readonly { href: string; label: string }[] = [
  { href: "/legal/terms", label: "Terms" },
  { href: "/legal/privacy", label: "Privacy" },
  { href: "/legal/dpa", label: "DPA" },
  { href: "/legal/subprocessors", label: "Sub-processors" },
  { href: "/legal/aup", label: "Acceptable use" },
  { href: "/.well-known/security.txt", label: "security.txt" },
  { href: "/status", label: "Status" },
];

export function SiteFooter() {
  return (
    <footer data-site-footer className="mt-32 border-t border-line">
      <div className="mx-auto grid max-w-page gap-8 px-6 py-12 text-sm text-muted md:grid-cols-12">
        <div className="md:col-span-6">
          <p className="font-display text-base text-ink">{BRAND.name}</p>
          <p className="mt-2" data-testid="disclaimer">
            {disclaimer()}
          </p>
          <address className="mt-4 not-italic leading-relaxed" data-testid="legal-identity">
            {BRAND.legalEntity}
            <br />
            GSTIN {BRAND.gstin}
            <br />
            {BRAND.address}
            <br />
            <a className="underline" href={`mailto:${BRAND.email}`}>
              {BRAND.email}
            </a>
          </address>
        </div>
        <nav aria-label="Legal" className="md:col-span-6">
          <ul className="grid grid-cols-2 gap-2">
            {LEGAL.map((l) => (
              <li key={l.href}>
                <a href={l.href} className="motion hover:text-ink">
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
