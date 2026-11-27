import { PageHeader } from "@/components/section";
import { CHANGELOG } from "@/content/changelog";

export const metadata = { title: "Changelog", description: "What changed in the product, by date." };

export default function ChangelogPage() {
  return (
    <>
      <PageHeader kicker="Changelog" title="What changed, by date" />
      <ol className="mx-auto max-w-page space-y-8 px-6 pb-16">
        {CHANGELOG.map((c) => (
          <li key={`${c.date}-${c.title}`} className="max-w-3xl border-t border-line pt-6">
            <p className="text-sm text-muted">
              <time dateTime={c.date}>{c.date}</time>
            </p>
            <h2 className="mt-1 font-display text-xl">{c.title}</h2>
            <p className="mt-2">{c.body}</p>
          </li>
        ))}
      </ol>
    </>
  );
}
