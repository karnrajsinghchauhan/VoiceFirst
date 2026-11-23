import reference from "@/content/generated/api-reference.json";
import { BRAND } from "@/config/brand";

export const metadata = { title: "API reference" };

interface Op {
  method: string;
  path: string;
  summary: string;
  tag: string;
  auth: boolean;
  request: string | null;
  response: string | null;
}

// Generated at build time from contracts/openapi.yaml, the contract the server is tested against.
export default function ApiReference() {
  const ops = reference.operations as Op[];
  const tags = [...new Set(ops.map((o) => o.tag))];
  return (
    <>
      <h1>API reference</h1>
      <p>
        The {BRAND.name} engine exposes a JSON HTTP API. This page is generated from <code>contracts/openapi.yaml</code>, which
        CI checks against the running application and fuzzes with schemathesis. Every endpoint except <code>/healthz</code>{" "}
        needs a bearer token; the token decides the role (admin, ops, auditor, read-only).
      </p>
      <pre>
        <code>{`curl -H "Authorization: Bearer $AV_TOKEN" https://<engine-host>/whoami`}</code>
      </pre>
      <p>
        Errors share one shape: <code>{`{"error": "<code>", "detail": "<message>"}`}</code>. Request bodies are strict: a field of
        the wrong type is rejected, never coerced.
      </p>
      {tags.map((tag) => (
        <section key={tag}>
          <h2 id={tag}>{tag}</h2>
          <table>
            <thead>
              <tr>
                <th scope="col">Method</th>
                <th scope="col">Path</th>
                <th scope="col">Summary</th>
                <th scope="col">Body</th>
                <th scope="col">Returns</th>
              </tr>
            </thead>
            <tbody>
              {ops
                .filter((o) => o.tag === tag)
                .map((o) => (
                  <tr key={`${o.method} ${o.path}`}>
                    <td>
                      <code>{o.method}</code>
                    </td>
                    <td>
                      <code>{o.path}</code>
                    </td>
                    <td>{o.summary}</td>
                    <td>{o.request ? <code>{o.request}</code> : ""}</td>
                    <td>{o.response ? <code>{o.response}</code> : ""}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </section>
      ))}
      <p>
        Record schemas (BookingEvent, CallOutcome, GateDecision, HandoffSummary and others) are JSON Schema 2020-12 files in{" "}
        <code>contracts/schemas/</code>; Python and TypeScript types are generated from them and CI fails on drift.
      </p>
    </>
  );
}
