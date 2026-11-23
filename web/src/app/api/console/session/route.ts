// Console sign-in. The API token goes into an HttpOnly cookie; browser code never holds it.
import { getEngine } from "@/lib/server/engine";
import { clearSession, csrfValid, jsonError, rateLimited, sessionToken, setSession } from "@/lib/server/security";

export const dynamic = "force-dynamic";

// Always 200: signed out is a normal state, and the sign-in form needs to know the mode.
export async function GET(): Promise<Response> {
  const mode = getEngine().mode;
  const token = await sessionToken();
  if (token === null) return Response.json({ identity: null, mode });
  const res = await getEngine().console("GET", "/whoami", token, undefined);
  return Response.json({ identity: res.status === 200 ? res.body : null, mode });
}

export async function POST(req: Request): Promise<Response> {
  if (await rateLimited("session")) return jsonError(429, "rate_limited", "too many sign-in attempts");
  const body = (await req.json().catch(() => null)) as { token?: unknown } | null;
  const token = typeof body?.token === "string" ? body.token.trim() : "";
  if (!token) return jsonError(422, "validation_error", "token is required");
  const res = await getEngine().console("GET", "/whoami", token, undefined);
  if (res.status !== 200) return jsonError(401, "auth_error", "token not accepted");
  await setSession(token);
  return Response.json({ identity: res.body, mode: getEngine().mode });
}

export async function DELETE(): Promise<Response> {
  if (!(await csrfValid())) return jsonError(403, "csrf", "missing or wrong CSRF token");
  await clearSession();
  return new Response(null, { status: 204 });
}
