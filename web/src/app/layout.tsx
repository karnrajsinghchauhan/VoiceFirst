import type { Metadata } from "next";
import { headers } from "next/headers";
import type { ReactNode } from "react";
import "./globals.css";
import { fraunces, inter, mukta } from "./fonts";
import { SiteFooter, SiteHeader } from "@/components/site-chrome";
import { Concierge } from "@/components/concierge";
import { BRAND } from "@/config/brand";

export const metadata: Metadata = {
  metadataBase: new URL(BRAND.siteUrl),
  title: { default: BRAND.name, template: `%s | ${BRAND.name}` },
  description:
    "Compliant Hindi, English and Hinglish service calls that recover failed payments and confirm bookings, measured against a no-call holdout.",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  // Reading the request makes every page render per request, so Next can stamp the CSP
  // nonce from middleware onto its scripts. Static HTML could not carry a fresh nonce.
  await headers();
  return (
    <html lang="en" className={`${inter.variable} ${fraunces.variable} ${mukta.variable}`}>
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <SiteHeader />
        <main id="main">{children}</main>
        <SiteFooter />
        <Concierge />
      </body>
    </html>
  );
}
