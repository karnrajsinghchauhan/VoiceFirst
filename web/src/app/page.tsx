// BookedMeetings brand home. The voice product is its first subsection (/voice, D-034).
import Link from "next/link";
import { PageHeader, Section } from "@/components/section";
import { BRAND } from "@/config/brand";

export const metadata = {
  title: { absolute: BRAND.name },
  description: "AI systems that keep customer appointments and payments on track, in the customer's language.",
};

export default function BrandHome() {
  return (
    <>
      <PageHeader
        kicker={BRAND.name}
        title="AI that keeps appointments and payments on track, in the customer's language"
        intro={`${BRAND.name} builds and runs AI calling for consumer businesses in India: confirming what customers booked, helping them finish what they started, and handing every judgement call to a person.`}
      />
      <Section id="voice" kicker="Product" title="Voice: compliant service calls in Hindi, English and Hinglish">
        <div className="grid gap-8 md:grid-cols-2">
          <p className="max-w-xl text-lg">
            Outbound service calls that disclose they are AI, check every telecom and data-protection rule before dialling,
            never take card details by voice, and measure their effect against a group of customers who are never called.
          </p>
          <ul className="space-y-3">
            <li>
              <Link className="underline" href="/voice">
                How it works and a recorded call
              </Link>
            </li>
            <li>
              <Link className="underline" href="/voice/product">
                The five promises and what we have measured
              </Link>
            </li>
            <li>
              <Link className="underline" href="/voice/security">
                Security and data
              </Link>
            </li>
            <li>
              <Link className="underline" href="/voice/pricing">
                Pricing
              </Link>
            </li>
          </ul>
        </div>
      </Section>
      <Section id="contact" kicker="Contact" title="Talk to us">
        <p className="max-w-xl text-lg">
          Write to{" "}
          <a className="underline" href={`mailto:${BRAND.email}`}>
            {BRAND.email}
          </a>{" "}
          or book a call from the{" "}
          <Link className="underline" href="/voice#book">
            voice page
          </Link>
          .
        </p>
      </Section>
    </>
  );
}
