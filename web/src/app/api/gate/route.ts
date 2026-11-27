// Passcode gate for /demo and /agoda. A plain form POST so it works without JavaScript.
import { jsonError, passcodeMatches, rateLimited, setGate } from "@/lib/server/security";

export const dynamic = "force-dynamic";

const NEXT_ALLOWED = new Set(["/demo", "/agoda", "/cars24"]);

export async function POST(req: Request): Promise<Response> {
  if (await rateLimited("gate")) return jsonError(429, "rate_limited", "too many attempts; wait a minute");
  const form = await req.formData();
  const passcode = String(form.get("passcode") ?? "");
  const requested = String(form.get("next") ?? "/demo");
  // Only redirect to our own private pages, never to a supplied URL.
  const next = NEXT_ALLOWED.has(requested) ? requested : "/demo";
  const back = new URL(req.url);
  if (!passcodeMatches(passcode)) {
    back.pathname = "/gate";
    back.search = `?next=${encodeURIComponent(next)}&error=1`;
    return Response.redirect(back, 303);
  }
  await setGate(passcode);
  back.pathname = next;
  back.search = "";
  return new Response(null, { status: 303, headers: { location: back.pathname } });
}
