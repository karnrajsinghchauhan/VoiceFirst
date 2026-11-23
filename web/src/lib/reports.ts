// Server-only: finds the newest eval report written by `make eval` (reports/<ts>/index.html).
import { readdir, stat } from "node:fs/promises";
import { join, resolve } from "node:path";

export function reportsDir(): string {
  return resolve(process.env.AV_REPORTS_DIR ?? join(process.cwd(), "..", "reports"));
}

export async function latestReportPath(): Promise<string | null> {
  const dir = reportsDir();
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch (e) {
    // No reports directory simply means `make eval` has not run yet.
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw e;
  }
  // Timestamped directory names sort lexically in time order.
  for (const name of entries.sort().reverse()) {
    const candidate = join(dir, name, "index.html");
    const info = await stat(candidate).catch((e: NodeJS.ErrnoException) => {
      if (e.code === "ENOENT") return null;
      throw e;
    });
    if (info?.isFile()) return candidate;
  }
  return null;
}
