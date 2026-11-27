import { getEngine } from "@/lib/server/engine";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  return Response.json(await getEngine().slots());
}
