import Link from "next/link";
import { FlowDiagram } from "@/components/flow-diagram";
import { HeroTimeline } from "@/components/timeline";
import { Measured, MEASURED_NOTE, Rich, Spec, Src } from "@/components/claims";
import { Section } from "@/components/section";
import { PROMISES } from "@/content/promises";
import { FAQ } from "@/content/faq";
import { BookCall } from "@/components/book-call";
import recorded from "@/content/demo-runs/failed_upi.json";
import type { DemoRun } from "@/lib/demo-types";

const HERO_RUN = recorded as DemoRun;

const PROOF_IDS = ["proof", "race", "guardrails", "critical", "holdout", "killswitch"] as const;

export default function Home() {
  return (
    <>
      <section className="mx-auto max-w-page px-6 pb-16 pt-16 md:pt-24">
        <div className="grid gap-12 md:grid-cols-12">
          <div className="md:col-span-5">
            <h1 className="font-display text-3xl tracking-tight md:text-4xl">
              Calls that recover payments and confirm bookings, in the customer&apos;s language.
            </h1>
            <p className="mt-6 text-lg text-muted">
              An AI calling service for India in Hindi, English and Hinglish. It discloses itself, never takes card details,
              hands every money decision to a person, and is measured against a group of bookings it never calls.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="#book" className="motion rounded bg-ink px-4 py-2.5 text-sm text-paper hover:bg-accent">
                Book a call
              </Link>
              <a href="#concierge" className="motion rounded border border-ink px-4 py-2.5 text-sm hover:bg-surface" data-open-concierge>
                Ask the concierge
              </a>
            </div>
          </div>
          <figure className="rounded border border-line bg-surface p-6 md:col-span-7" aria-label="A recorded call from the engine">
            <HeroTimeline run={HERO_RUN} />
            <figcaption className="mt-4 border-t border-line pt-3 text-xs text-muted">
              Recorded from the engine on <Spec of="recorded_at">{HERO_RUN.recorded_at}</Spec>, text mode with mock
              providers. Names, bookings and amounts are synthetic. <Link className="underline" href="/product#demo">How this was made</Link>.
            </figcaption>
          </figure>
        </div>
      </section>

      <Section id="problem" kicker="The problem" title="A failed payment is a booking you are about to lose.">
        <div className="grid gap-8 md:grid-cols-3">
          <p>
            A UPI payment times out. A Book Now, Pay Later date passes. The customer meant to pay and forgot. An email is easy
            to miss; a short call in the language they speak at home is not.
          </p>
          <p>
            Calling at scale in India is regulated. TRAI&apos;s amended rules treat an AI-placed call from an undeclared number
            as unsolicited commercial communication (<Src id="S-24">notified 18 Sep 2026</Src>). Consent, DND, call windows and
            caps have to be enforced by the system, not remembered by a team.
          </p>
          <p>
            Customers mix languages. MakeMyTrip reports that <Src id="S-23">70% of voice queries come in Hinglish</Src>. A
            voice agent that only handles English, or formal Hindi, will mishear the people it is calling.
          </p>
        </div>
      </Section>

      <Section id="how" kicker="How a call works" title="Nothing is dialled until every gate has passed.">
        <div className="grid gap-10 md:grid-cols-12">
          <div className="md:col-span-7">
            <FlowDiagram />
          </div>
          <div className="space-y-4 md:col-span-5">
            <p>
              Each gate is a small, pure function: holdout, jurisdiction, kill switch, consent, DND, opt-out, declared caller ID,
              number series, caller ID status, call window, attempt cap and cooldown. If any fails, the decision is recorded and
              nothing is dialled.
            </p>
            <p>
              When all pass, the system issues a single-use clearance that expires within a minute. The dialler accepts nothing
              else. It is consumed in the same database transaction that places the call.
            </p>
            <p>
              On the call, the first sentence says it is an AI assistant and that the call is recorded. Then it asks to speak to
              the booker by name, and says nothing about the booking until they confirm.
            </p>
          </div>
        </div>
      </Section>

      <Section id="promises" kicker="Five promises" title="What the system will never do, and how we check.">
        <ol className="grid gap-x-12 gap-y-8 md:grid-cols-2">
          {PROMISES.map((p) => (
            <li key={p.id}>
              <h3 className="font-display text-lg">{p.title}</h3>
              <p className="mt-2 text-muted">{p.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section id="proof" kicker="Proof" title="Measured on test data, with the method and the date.">
        <p className="max-w-prose text-muted">{MEASURED_NOTE}</p>
        <dl className="mt-8 grid gap-px overflow-hidden rounded border border-line bg-line md:grid-cols-3">
          {PROOF_IDS.map((id) => (
            <div key={id} className="bg-surface p-6">
              <dt className="text-sm text-muted">
                <ProofLabel id={id} />
              </dt>
              <dd className="mt-2 font-display text-xl">
                <Measured id={id} />
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-sm">
          <Link className="underline" href="/product#proof">
            Every result, with how it was measured
          </Link>
        </p>
      </Section>

      <Section id="deploy" kicker="Private deployment" title="Run it with us first. Then run it yourself.">
        <div className="grid gap-8 md:grid-cols-3">
          <p>
            We set it up, run it and review it with you every week. When you are ready, the same Helm chart installs on your own
            Kubernetes. No cloud-vendor dependencies: Postgres, a Kafka-API event bus, and containers.
          </p>
          <p>
            Events speak the Kafka API, so the service plugs into an existing event backbone. Handoffs land in Zendesk,
            Salesforce or HubSpot through one adapter per CRM.
          </p>
          <p>
            Data stays in India by default. The service refuses to start if a configured provider processes data outside the
            regions you allow.
          </p>
        </div>
      </Section>

      <Section id="pricing" kicker="Pricing" title="Paid for outcomes we can measure.">
        <div className="grid gap-8 md:grid-cols-2">
          <p>
            <Rich text="An eight-week pilot at a fixed [[spec:offer.pilot_fee|USD 20,000]], with [[spec:offer.pilot_at_risk|half]] at risk against success metrics we agree up front and measure against the holdout." />
          </p>
          <p>
            <Rich text="After the pilot, either [[spec:offer.retainer|USD 6,000 a month]] plus [[spec:offer.per_resolved|Rs 25 per contact the AI resolves]], or [[spec:offer.per_minute|USD 0.09 per outbound minute]]. " />
            <Link className="underline" href="/pricing">
              How the pricing works
            </Link>
            .
          </p>
        </div>
      </Section>

      <Section id="faq" kicker="Questions" title="Frequently asked">
        <dl className="divide-y divide-line border-y border-line">
          {FAQ.map((f) => (
            <div key={f.q} className="grid gap-2 py-6 md:grid-cols-12">
              <dt className="font-medium md:col-span-5">{f.q}</dt>
              <dd className="text-muted md:col-span-7">
                <Rich text={f.a} />
              </dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section id="book" kicker="Next step" title="Talk to us.">
        <div className="grid gap-10 md:grid-cols-12">
          <div className="space-y-4 md:col-span-5">
            <p>
              The concierge answers questions about the product from these pages and cites the page it used. It will tell you
              when it does not know.
            </p>
            <p>Or book a call with the founder.</p>
          </div>
          <div className="md:col-span-7">
            <BookCall />
          </div>
        </div>
      </Section>
    </>
  );
}

function ProofLabel({ id }: { id: (typeof PROOF_IDS)[number] }) {
  const labels: Record<(typeof PROOF_IDS)[number], string> = {
    proof: "Compliance proof: a call is placed only when every gate passes",
    race: "Single-use clearance under concurrency",
    guardrails: "Guardrails held across the persona suite",
    critical: "Refund bait, legal threats, child, injection, card, OTP",
    holdout: "Holdout never called",
    killswitch: "Kill switch stops new dials",
  };
  return <>{labels[id]}</>;
}
