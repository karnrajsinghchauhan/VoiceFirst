// Rendered from docs/discovery-questions.md (npm run gen:content), so the letter and the
// repo never disagree about what is still unknown.
import discovery from "@/content/generated/discovery.json";

// `only` picks one client's section; without it, every section except other clients' lists.
export function DiscoveryList({ only }: { only?: string }) {
  const sections = discovery.sections.filter((s) => (only ? s.heading === only : s.heading !== "Cars24"));
  return (
    <>
      {sections.map((s) => (
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
