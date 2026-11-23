"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui";

export default function ReportPage() {
  const [available, setAvailable] = useState<boolean | null>(null);
  useEffect(() => {
    fetch("/console/report/latest", { method: "HEAD" }).then(
      (r) => setAvailable(r.ok),
      () => setAvailable(false),
    );
  }, []);
  return (
    <Card title="Latest eval report" testId="eval-report">
      {available === null && <p className="text-muted">Loading</p>}
      {available === false && (
        <p className="text-muted">
          No eval report yet. Run <code>make eval</code>; it writes reports/&lt;timestamp&gt;/index.html.
        </p>
      )}
      {available && <iframe title="Eval report" src="/console/report/latest" className="h-[80vh] w-full rounded border border-line bg-white" />}
    </Card>
  );
}
