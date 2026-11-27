import { getEngine } from "@/lib/server/engine";
import { demoPasscode, jsonError, rateLimited } from "@/lib/server/security";

export const dynamic = "force-dynamic";

export async function POST(): Promise<Response> {
  if (await rateLimited("demo")) return jsonError(429, "rate_limited", "slow down");
  const passcode = demoPasscode();
  if (passcode === null) return jsonError(503, "gate", "demo passcode not configured");
  return Response.json(await getEngine().demoKill(passcode));
}
