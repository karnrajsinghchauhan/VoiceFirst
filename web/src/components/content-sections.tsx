// Renders a content JSON file (trust.json, pricing.json) as page sections. Claims inside the
// text use the [[tag|text]] marks that <Rich> turns into sourced, measured or estimate spans.
import { Rich } from "@/components/claims";
import { Section } from "@/components/section";

export interface ContentSection {
  id: string;
  heading: string;
  body: string;
  points?: string[];
}

export function ContentSections({ kicker, sections }: { kicker: string; sections: readonly ContentSection[] }) {
  return (
    <>
      {sections.map((s) => (
        <Section key={s.id} id={s.id} kicker={kicker} title={s.heading}>
          <p className="max-w-3xl text-lg">
            <Rich text={s.body} />
          </p>
          {s.points?.length ? (
            <ul className="mt-6 max-w-3xl list-disc space-y-2 pl-5">
              {s.points.map((p) => (
                <li key={p}>
                  <Rich text={p} />
                </li>
              ))}
            </ul>
          ) : null}
        </Section>
      ))}
    </>
  );
}
