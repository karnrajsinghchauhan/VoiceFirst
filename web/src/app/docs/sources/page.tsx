import { SOURCES } from "@/components/claims";
import sources from "@/content/generated/sources.json";

export const metadata = { title: "Sources" };

// Rendered from docs/sources.md (npm run gen:content). Every Src link on the site lands on a row here.
export default function SourcesPage() {
  return (
    <>
      <h1>Sources</h1>
      <p>
        Every external fact on this site links here. Each row links the page it was checked against and gives its date. Facts
        that could not be verified never appear as facts; they are questions in the discovery list.
      </p>
      <p className="text-sm text-muted">{sources.note}</p>
      <table>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">Fact</th>
            <th scope="col">Source</th>
            <th scope="col">Date</th>
          </tr>
        </thead>
        <tbody>
          {SOURCES.map((s) => (
            <tr key={s.id} id={s.id} className="target:bg-accent-soft">
              <td>
                <code>{s.id}</code>
              </td>
              <td>{s.fact}</td>
              <td>
                {s.links.length === 0
                  ? s.source
                  : s.links.map((l, i) => (
                      <span key={l.url}>
                        {i > 0 ? "; " : null}
                        <a href={l.url} rel="noopener noreferrer">
                          {l.label}
                        </a>
                      </span>
                    ))}
              </td>
              <td className="whitespace-nowrap">{s.date}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>
        Results we measured ourselves are not sources; they are listed with their method and date on the{" "}
        <a href="/product#proof">product page</a>.
      </p>
    </>
  );
}
