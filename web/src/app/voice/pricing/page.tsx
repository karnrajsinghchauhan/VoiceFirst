import { ContentSections } from "@/components/content-sections";
import { PageHeader } from "@/components/section";
import pricing from "@/content/pricing.json";

export const metadata = { title: "Pricing", description: pricing.intro };

export default function PricingPage() {
  return (
    <>
      <PageHeader kicker="Pricing" title={pricing.title} intro={pricing.intro} />
      <ContentSections kicker="Pricing" sections={pricing.sections} />
    </>
  );
}
