import { ContentSections } from "@/components/content-sections";
import { PageHeader } from "@/components/section";
import trust from "@/content/trust.json";

export const metadata = { title: "Security", description: trust.intro };

export default function SecurityPage() {
  return (
    <>
      <PageHeader kicker="Trust centre" title={trust.title} intro={trust.intro} />
      <ContentSections kicker="Security" sections={trust.sections} />
    </>
  );
}
