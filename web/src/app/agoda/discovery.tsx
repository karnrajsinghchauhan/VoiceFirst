// Rendered from docs/discovery-questions.md (npm run gen:content), so the letter and the
// repo never disagree about what is still unknown.
import discovery from "@/content/generated/discovery.json";

export function DiscoveryList() {
  return (
    <>
      {discovery.sections.map((s) => (
        <div key={s.heading}>
          <h3>{s.heading}</h3>
          <ul>
            {s.questions.map((q) => (
              <li key={q}>{q.replace(/`/g, "")}</li>
            ))}
          </ul>
        </div>
      ))}
    </>
  );
}
