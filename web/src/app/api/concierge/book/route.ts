// Meeting booking. Consent must be explicit; a filled honeypot field marks a bot.
import { getEngine } from "@/lib/server/engine";
import { jsonError, rateLimited } from "@/lib/server/security";

export const dynamic = "force-dynamic";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export async function POST(req: Request): Promise<Response> {
  if (await rateLimited("book")) return jsonError(429, "rate_limited", "too many booking attempts");
  const b = (await req.json().catch(() => null)) as Record<string, unknown> | null;
  if (b === null) return jsonError(422, "validation_error", "a JSON body is required");
  if (typeof b.website === "string" && b.website !== "") return jsonError(422, "validation_error", "rejected");
  const field = (k: string, max: number): string | null => {
    const v = b[k];
    return typeof v === "string" && v.trim() && v.length <= max ? v.trim() : null;
  };
  const name = field("name", 120);
  const email = field("email", 200);
  const company = field("company", 160);
  const slot = field("slot", 40);
  const session = field("session_id", 64);
  if (b.consent !== true) return jsonError(422, "consent_required", "consent to be contacted is required");
  if (!name || !email || !EMAIL.test(email) || !company || !slot || !session)
    return jsonError(422, "validation_error", "name, a valid email, company and slot are required");
  return Response.json(await getEngine().book({ session_id: session, name, email, company, slot, consent: true }));
}
