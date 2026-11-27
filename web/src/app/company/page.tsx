import { PageHeader, Section } from "@/components/section";
import { BRAND } from "@/config/brand";

export const metadata = { title: "Company", description: "Who builds this, and how to reach us." };

export default function CompanyPage() {
  return (
    <>
      <PageHeader
        kicker="Company"
        title="A small team that builds for handover"
        intro={`${BRAND.name} is built and run by ${BRAND.legalEntity}, founded by Karn in Delhi-NCR.`}
      />
      <Section id="how" kicker="How we work" title="Small, and honest about it">
        <div className="max-w-3xl space-y-4 text-lg">
          <p>
            We are a small company. We design for that: the client holds the kill switch from day one, the failure mode is no call
            rather than a bad call, and the code is one typed service whose safety rules are enforced by tests, so a client&apos;s own
            engineers can read it, run it and take it over.
          </p>
          <p>We hold no security certification yet and say so on the security page.</p>
        </div>
      </Section>
      <Section id="details" kicker="Details" title="Company details">
        <dl className="grid max-w-xl grid-cols-[10rem_1fr] gap-y-2">
          <dt className="text-muted">Legal entity</dt>
          <dd>{BRAND.legalEntity}</dd>
          <dt className="text-muted">GSTIN</dt>
          <dd>{BRAND.gstin}</dd>
          <dt className="text-muted">Address</dt>
          <dd>{BRAND.address}</dd>
          <dt className="text-muted">Contact</dt>
          <dd>
            <a className="underline" href={`mailto:${BRAND.email}`}>
              {BRAND.email}
            </a>
          </dd>
          <dt className="text-muted">Security reports</dt>
          <dd>
            <a className="underline" href="/.well-known/security.txt">
              security.txt
            </a>
          </dd>
        </dl>
      </Section>
    </>
  );
}
