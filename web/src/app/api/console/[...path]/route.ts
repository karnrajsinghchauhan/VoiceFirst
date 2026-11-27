// Same-origin proxy to the engine's console endpoints. Adds the bearer token from the
// HttpOnly session cookie; mutations must carry the CSRF header (double-submit).
import { getEngine } from "@/lib/server/engine";
import { csrfValid, jsonError, sessionToken } from "@/lib/server/security";

export const dynamic = "force-dynamic";

// Only the console's own read and write paths are proxied; nothing else on the engine is reachable.
const ALLOWED = new Set(["GET /campaigns", "GET /calls", "GET /handoff", "GET /numbers", "GET /costs", "GET /audit", "GET /killswitch", "POST /killswitch"]);

async function forward(req: Request, segments: string[]): Promise<Response> {
  const route = `/${segments.join("/")}`;
  if (!ALLOWED.has(`${req.method} ${route}`)) return jsonError(404, "http_404", `no console route ${req.method} ${route}`);
  const token = await sessionToken();
  if (token === null) return jsonError(401, "auth_error", "not signed in");
  if (req.method !== "GET" && !(await csrfValid())) return jsonError(403, "csrf", "missing or wrong CSRF token");
  const query = new URL(req.url).search;
  const body = req.method === "GET" ? undefined : await req.json().catch(() => null);
  const res = await getEngine().console(req.method, `${route}${query}`, token, body);
  return Response.json(res.body, { status: res.status });
}

export async function GET(req: Request, ctx: { params: Promise<{ path: string[] }> }): Promise<Response> {
  return forward(req, (await ctx.params).path);
}

export async function POST(req: Request, ctx: { params: Promise<{ path: string[] }> }): Promise<Response> {
  return forward(req, (await ctx.params).path);
}
