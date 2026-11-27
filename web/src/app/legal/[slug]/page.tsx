import { notFound } from "next/navigation";
import { PageHeader } from "@/components/section";
import { LEGAL_PAGES } from "@/content/legal";

export function generateStaticParams() {
  return Object.keys(LEGAL_PAGES).map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return { title: LEGAL_PAGES[slug]?.title ?? "Legal" };
}

export default async function LegalPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = LEGAL_PAGES[slug];
  if (!page) notFound();
  return (
    <>
      <PageHeader kicker="Legal" title={page.title} intro="Template; requires legal review before it binds anyone." />
      <div className="mx-auto max-w-page space-y-4 px-6 pb-16">
        {page.paragraphs.map((p) => (
          <p key={p} className="max-w-3xl">
            {p}
          </p>
        ))}
      </div>
    </>
  );
}
