// Concierge questions. The message is passed to the engine and not logged here (PII minimisation).
import { getEngine } from "@/lib/server/engine";
import { jsonError, rateLimited } from "@/lib/server/security";

export const dynamic = "force-dynamic";

const MAX_CHARS = 600;

export async function POST(req: Request): Promise<Response> {
  if (await rateLimited("ask")) return jsonError(429, "rate_limited", "too many questions; try again in a minute");
  const body = (await req.json().catch(() => null)) as { session_id?: unknown; message?: unknown } | null;
  const message = typeof body?.message === "string" ? body.message.trim() : "";
  const session = typeof body?.session_id === "string" ? body.session_id : "";
  if (!message || message.length > MAX_CHARS || !/^[a-zA-Z0-9-]{8,64}$/.test(session))
    return jsonError(422, "validation_error", `message (1-${MAX_CHARS} chars) and session_id are required`);
  return Response.json(await getEngine().ask(session, message));
}
