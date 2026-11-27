// RFC 9116 security.txt. Expires is a year ahead of each build; the contact comes from env.
import { BRAND } from "@/config/brand";

export const dynamic = "force-static";

export function GET(): Response {
  const expires = new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString();
  const body = [
    `Contact: mailto:${BRAND.securityEmail}`,
    `Expires: ${expires}`,
    "Preferred-Languages: en, hi",
    `Canonical: ${BRAND.siteUrl}/.well-known/security.txt`,
    `Policy: ${BRAND.siteUrl}/security#disclosure`,
    "",
  ].join("\n");
  return new Response(body, { headers: { "content-type": "text/plain; charset=utf-8" } });
}
