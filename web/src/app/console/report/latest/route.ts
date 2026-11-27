import { readFile } from "node:fs/promises";
import { latestReportPath } from "@/lib/reports";
import { getEngine } from "@/lib/server/engine";
import { sessionToken } from "@/lib/server/security";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  // The report names personas and test results; only a signed-in console user may read it.
  const token = await sessionToken();
  const who = token === null ? null : await getEngine().console("GET", "/whoami", token, undefined);
  if (who === null || who.status !== 200) return new Response("sign in to the console first", { status: 401 });
  const path = await latestReportPath();
  if (path === null) return new Response("no eval report yet; run make eval", { status: 404 });
  const html = await readFile(path, "utf8");
  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      // Sandboxed: scripts inside the report cannot reach the console; only the console may frame it.
      "content-security-policy": "sandbox allow-same-origin; frame-ancestors 'self'",
    },
  });
}
