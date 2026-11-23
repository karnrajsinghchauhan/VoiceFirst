// Runs a demo scenario on the engine (or replays one recorded from it, in mock mode).
// The middleware has already checked the passcode cookie; the engine gets the passcode itself.
import { isScenario } from "@/lib/demo-types";
import { getEngine } from "@/lib/server/engine";
import { demoPasscode, jsonError, rateLimited } from "@/lib/server/security";

export const dynamic = "force-dynamic";

export async function POST(req: Request): Promise<Response> {
  if (await rateLimited("demo")) return jsonError(429, "rate_limited", "slow down");
  const passcode = demoPasscode();
  if (passcode === null) return jsonError(503, "gate", "demo passcode not configured");
  const body = (await req.json().catch(() => null)) as { scenario?: unknown } | null;
  if (!isScenario(body?.scenario)) return jsonError(422, "validation_error", "unknown scenario");
  return Response.json(await getEngine().demoRun(body.scenario, passcode));
}
