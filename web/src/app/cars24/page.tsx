// /cars24: a short private note to Cars24 (D-037). Same rules as /agoda: every external fact is
// a <Src>, every number we measured is dated, estimates say so.
import type { ReactNode } from "react";
import { Measured, Spec, Src } from "@/components/claims";
import { BRAND } from "@/config/brand";
import recorded from "@/content/demo-runs/cars24_inspection.json";
import type { DemoRun } from "@/lib/demo-types";
import { DiscoveryList } from "../agoda/discovery";

export const metadata = { title: `${BRAND.name} for Cars24`, robots: { index: false, follow: false } };

const RUN = recorded as DemoRun;

function Section({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={`c${n}`} className="mt-12">
      <h2 id={`c${n}`}>
        {n}. {title}
      </h2>
      {children}
    </section>
  );
}

export default function Cars24Note() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <article className="prose-av">
        <p className="text-sm text-muted">Private and confidential. Prepared for Cars24, 28 November 2026.</p>
        <h1>Appointment confirmations for Cars24, checked before every dial</h1>
        <p>
          From Karn, founder, {BRAND.name} ({BRAND.legalEntity}). {BRAND.name} is an independent company and is not affiliated
          with or endorsed by Cars24 or Agoda. Names, bookings and times in this note are synthetic.
        </p>

        <Section n={1} title="What you already run">
          <p>
            You are ahead of most companies on voice. You build voice and chat agents across buying, selling, financing,
            follow-up and support <Src id="S-36">(vendor case study)</Src>; your voicebots handled 2.58 million connected minutes in
            a quarter <Src id="S-37">(July 2026)</Src>; and your stated aim is for AI to handle 30% of calls, with inspections,
            financing and after-sale service next <Src id="S-38">(vendor blog)</Src>. We are not proposing to replace any of it.
          </p>
        </Section>

        <Section n={2} title="What we would add">
          <p>
            One narrow job, built to a compliance standard you can audit: confirming the appointments your sellers and buyers have
            already booked. A seller books a free home inspection at the car&apos;s location; a buyer in some cities books a test
            drive at home <Src id="S-35">(Cars24 pages)</Src>. A missed or wrong slot costs an inspector&apos;s trip. Our agent
            calls about 18 hours before the slot, confirms the date, time and locality in the customer&apos;s language, reminds a
            seller to keep the RC, insurance and PUC ready (a buyer, their driving licence), takes a note for your team, and
            hands any reschedule to a person.
          </p>
          <p>
            Every call passes the same checks as our travel pilot before it is dialled: a declared caller ID in the right series,
            a recorded consent basis, the DND registry, the call window, attempt caps and cooldowns, then a single-use clearance.
            A fixed share of appointments is never called, so the effect on show-up rates is measured, not assumed. We do not make
            lending, EMI or collection calls.
          </p>
        </Section>

        <Section n={3} title="A call, from the engine">
          <p>Recorded in text mode with mock providers and a scripted seller:</p>
          <div className="not-prose my-6 space-y-3 rounded border border-line bg-surface p-4 text-sm">
            {RUN.transcript.map((t, i) => (
              <p key={i}>
                <span className="mr-2 text-xs uppercase tracking-wide text-muted">{t.speaker === "agent" ? "Agent" : "Customer"}</span>
                {t.text}
              </p>
            ))}
          </div>
          <p>
            QA on this run: {RUN.qa.score} out of 100 on {RUN.qa.checks.length} checks. The same engine passes its guardrail
            assertions on every scripted persona <Measured id="guardrails" />, including four Cars24 personas (confirm, reschedule,
            spouse answers, opt-out). No real phone call has been made yet.
          </p>
        </Section>

        <Section n={4} title="A pilot">
          <p>
            <Spec of="pilot.cars24">Six weeks, one or two cities, seller inspections and buyer test drives, a 10% no-call holdout</Spec>.
            Success is agreed in week 1: inspector no-show rate and reschedule rate against the holdout, complaint rate, and cost
            per confirmed appointment. Commercial terms follow the structure we offer other clients (a fixed pilot fee with part
            at risk against the holdout) and are to be agreed with you.
          </p>
        </Section>

        <Section n={5} title="What we need from you">
          <DiscoveryList only="Cars24" />
        </Section>

        <Section n={6} title="Who we are">
          <p>
            {BRAND.name} is a small company founded by Karn in Delhi-NCR; we would rather say so than have you find out. Contact:{" "}
            {BRAND.email}.
          </p>
        </Section>
      </article>
    </div>
  );
}
