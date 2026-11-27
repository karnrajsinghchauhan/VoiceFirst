// Fed by the engine's live checks (GET /status); in mock mode it says there is no live service.
import { Badge } from "@/components/ui";
import { PageHeader } from "@/components/section";
import { getEngine } from "@/lib/server/engine";

export const metadata = { title: "Status", description: "Live health of the service." };
export const dynamic = "force-dynamic";

export default async function StatusPage() {
  const report = await getEngine().status();
  return (
    <>
      <PageHeader kicker="Status" title={`Overall: ${report.overall}`} intro="Checked live when this page loads." />
      <div className="mx-auto max-w-page px-6 pb-16">
        <table className="w-full max-w-3xl text-sm" data-testid="status">
          <thead>
            <tr className="border-b border-line text-left">
              <th scope="col" className="py-2">
                Component
              </th>
              <th scope="col">State</th>
              <th scope="col">Checked</th>
            </tr>
          </thead>
          <tbody>
            {report.components.map((c) => (
              <tr key={c.name} className="border-b border-line">
                <td className="py-2">{c.name}</td>
                <td>
                  <Badge tone={c.status === "operational" ? "ok" : c.status === "degraded" ? "warn" : "warn"}>{c.status}</Badge>
                </td>
                <td>
                  <time dateTime={c.checked_at}>{c.checked_at.slice(0, 19).replace("T", " ")} UTC</time>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-6 max-w-3xl text-sm text-muted">
          {report.history.length ? "" : "No uptime history is recorded yet; we will not show one until it is measured."}
        </p>
      </div>
    </>
  );
}
