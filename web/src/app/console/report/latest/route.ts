import { readFile } from "node:fs/promises";
import { latestReportPath } from "@/lib/reports";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  const path = await latestReportPath();
  if (path === null) return new Response("no eval report yet; run make eval", { status: 404 });
  const html = await readFile(path, "utf8");
  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      // The report is static; sandboxing it keeps any script inside it away from the console.
      "content-security-policy": "sandbox allow-same-origin",
    },
  });
}
