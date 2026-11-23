// Public brand and legal identity. Every value comes from env at build time; until Karn
// decides, the placeholders are deliberately obvious so nothing ships looking finished.
// "Agoda Voice" is used only on the private pitch pages (/agoda, /demo): see PITCH_NAME.

function env(name: string, value: string | undefined, placeholder: string): string {
  return value && value.trim() ? value.trim() : placeholder;
}

export const BRAND = {
  name: env("NEXT_PUBLIC_BRAND_NAME", process.env.NEXT_PUBLIC_BRAND_NAME, "[BRAND_NAME]"),
  legalEntity: env("NEXT_PUBLIC_LEGAL_ENTITY_NAME", process.env.NEXT_PUBLIC_LEGAL_ENTITY_NAME, "[LEGAL_ENTITY_NAME]"),
  gstin: env("NEXT_PUBLIC_LEGAL_GSTIN", process.env.NEXT_PUBLIC_LEGAL_GSTIN, "[LEGAL_GSTIN]"),
  address: env("NEXT_PUBLIC_LEGAL_ADDRESS", process.env.NEXT_PUBLIC_LEGAL_ADDRESS, "[LEGAL_ADDRESS]"),
  email: env("NEXT_PUBLIC_CONTACT_EMAIL", process.env.NEXT_PUBLIC_CONTACT_EMAIL, "[CONTACT_EMAIL]"),
  securityEmail: env("NEXT_PUBLIC_SECURITY_EMAIL", process.env.NEXT_PUBLIC_SECURITY_EMAIL, "[SECURITY_EMAIL]"),
  // D-701: ownermeetings.com as instructed; an enterprise voice product may deserve its own domain.
  siteUrl: env("NEXT_PUBLIC_SITE_URL", process.env.NEXT_PUBLIC_SITE_URL, "https://ownermeetings.com"),
} as const;

export const PITCH_NAME = "Agoda Voice";

export function disclaimer(): string {
  return `${BRAND.name} is an independent product by ${BRAND.legalEntity}. Not affiliated with or endorsed by Agoda.`;
}

export function isPlaceholder(value: string): boolean {
  return value.startsWith("[") && value.endsWith("]");
}
