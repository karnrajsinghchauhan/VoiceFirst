import Link from "next/link";
import type { ReactNode } from "react";
import { FlowDiagram } from "@/components/flow-diagram";
import { PROMISES } from "@/content/promises";
import demoCall from "@/content/demo-call.json";

// Placeholder contact address; replace with the real ProsperOps inbox before publishing.
const CONTACT = "mailto:hello@prosperops.example";

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="mx-auto max-w-5xl px-6 pt-20">
      <h2 className="font-serif text-2xl tracking-tight">{title}</h2>
      <div className="mt-5 text-[1.02rem] leading-relaxed text-ink">{children}</div>
    </section>
  );
}

interface DemoTurn {
  speaker: string;
  text: string;
}

const FAQ: readonly { q: string; a: string }[] = [
  {
    q: "Is this an Agoda product?",
    a: "No. Agoda Voice is built and operated by ProsperOps as a managed service, designed to transfer onto the client's own Kubernetes.",
  },
  {
    q: "Are AI calls allowed in India?",
    a: "Automated calls are A2P calls under TRAI's TCCCPR and must be declared and placed from the correct number series with a recorded consent basis. Agoda Voice enforces those rules in code before any dial. This is engineering guidance; Indian counsel signs off before go-live.",
  },
  {
    q: "Does the AI take card details or OTPs?",
    a: "Never. Card numbers and OTPs are detected and redacted before they reach the model or storage, the agent stops the customer politely, and payment happens only on an Agoda-hosted page via a WhatsApp link.",
  },
  {
    q: "Does J2 sell add-ons?",
    a: "No. Service calls carry no promotional content. If a customer asks about add-ons, the agent sends an app link with no persuasion and logs the request.",
  },
  {
    q: "How do you prove it works?",
    a: "A fixed 10% of eligible bookings is never called. Recovery and confirmation rates are compared against that holdout with a two-proportion test and a 95% confidence interval.",
  },
  {
    q: "What happens when the AI is unsure?",
    a: "It hands off. Disputes, refunds, legal or fraud mentions, two angry turns, VIP flags, safety and two failed attempts at the same step all go to a human with a summary.",
  },
];

export default function Home() {
  const turns = demoCall.turns as DemoTurn[];
  return (
    <div>
      <section className="mx-auto max-w-5xl px-6 pt-20">
        <p className="text-sm uppercase tracking-widest text-muted">Payment rescue and pre-arrival confirmation</p>
        <h1 className="mt-4 max-w-3xl font-serif text-4xl leading-tight tracking-tight sm:text-5xl">
          The India layer for outbound service calls: Hinglish, compliant, and measured against a holdout.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-muted">
          Agoda Voice places disclosed AI service calls in Hindi, English and Hinglish, sends payment links over
          WhatsApp, and hands every judgement call to a human.
        </p>
        <div className="mt-8 flex gap-4">
          <a href={CONTACT} className="rounded bg-accent px-5 py-2.5 text-sm text-white hover:opacity-90">
            Talk to ProsperOps
          </a>
          <Link href="/docs" className="rounded border border-line px-5 py-2.5 text-sm hover:bg-white">
            Read the docs
          </Link>
        </div>
      </section>

      <Section id="problem" title="The problem">
        <p className="max-w-3xl">
          Failed and pending payments, and unconfirmed arrivals, cost bookings. Generic voice platforms are not built
          for Indian telecom rules, Indian numbering or code-switched speech. MakeMyTrip reported that 70% of voice
          queries to its assistant come in Hinglish (The Hans India, 2026). An outbound call that misreads an amount,
          skips a disclosure or dials outside the permitted window is a compliance incident, not a missed sale.
        </p>
      </Section>

      <Section id="how" title="How it works">
        <div className="rounded border border-line bg-white p-4">
          <FlowDiagram />
        </div>
        <p className="mt-4 max-w-3xl text-muted">
          The dialer only accepts a single-use clearance that the compliance module mints after every gate passes:
          holdout, jurisdiction, kill switch, consent, DND, opt-out lock, CLI declaration, number series, CLI status,
          call window and attempt caps. The decision is recorded whether or not the call is cleared.
        </p>
      </Section>

      <Section id="promises" title="Five promises">
        <ol className="grid gap-4 sm:grid-cols-2" data-testid="promises">
          {PROMISES.map((p) => (
            <li key={p.id} className="rounded border border-line bg-white p-5">
              <p className="text-xs text-muted">{p.id}</p>
              <h3 className="mt-1 font-serif text-lg">{p.title}</h3>
              <p className="mt-2 text-sm text-muted">{p.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section id="holdout" title="Proof by holdout, not by containment alone">
        <p className="max-w-3xl">
          Every booking is assigned a stable bucket from a salted hash of its ID. Bucket 0 to 9, ten percent, is never
          called, whatever the gates say. Lift is the difference in recovery rate between called and held-out
          bookings, reported with a 95% confidence interval from a two-proportion test, alongside resolution time and
          customer satisfaction.
        </p>
        <p className="mt-3 max-w-3xl text-muted">
          We publish no lift figure here: the number comes from the pilot. The containment target for the pilot is
          35 to 55% (target, not a result).
        </p>
      </Section>

      <Section id="demo" title="A recorded mock call">
        <div className="rounded border border-line bg-white p-5" data-testid="demo-call">
          <p className="text-xs uppercase tracking-widest text-warn">{demoCall.label}</p>
          <p className="mt-1 text-sm text-muted">
            {demoCall.journey}. {demoCall.note}
          </p>
          <ol className="mt-4 space-y-3">
            {turns.map((t, i) => (
              <li key={i} className={t.speaker === "tool" ? "font-mono text-xs text-muted" : "text-sm"}>
                {t.speaker !== "tool" && (
                  <span className="mr-2 inline-block w-20 text-xs uppercase tracking-wide text-muted">
                    {t.speaker === "agent" ? "AI agent" : "Customer"}
                  </span>
                )}
                {t.text}
              </li>
            ))}
          </ol>
          <ul className="mt-5 list-disc pl-5 text-xs text-muted">
            {demoCall.annotations.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
      </Section>

      <Section id="private" title="Runs on your infrastructure">
        <p className="max-w-3xl">
          ProsperOps runs Agoda Voice as a managed service first. The same Helm chart then installs on the
          client&apos;s own Kubernetes: events speak the Kafka API, storage is Postgres, the chart carries no
          cloud-vendor dependencies, and each provider role (speech, voice, model, telephony, WhatsApp, CRM) is one
          implementation chosen by configuration. The code is written to be read and taken over by the client&apos;s
          engineers.
        </p>
      </Section>

      <Section id="pricing" title="Pricing">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded border border-line bg-white p-5">
            <h3 className="font-serif text-lg">Pilot</h3>
            <p className="mt-2 text-3xl">$20k fixed</p>
            <p className="mt-2 text-sm text-muted">Half of the fee is at risk against the agreed pilot metrics.</p>
          </div>
          <div className="rounded border border-line bg-white p-5">
            <h3 className="font-serif text-lg">After the pilot</h3>
            <p className="mt-2 text-base">$6k per month plus Rs 25 per AI-resolved contact</p>
            <p className="mt-1 text-sm text-muted">or $0.09 per outbound minute.</p>
            <p className="mt-2 text-sm text-muted">Containment target 35 to 55% (target).</p>
          </div>
        </div>
      </Section>

      <Section id="faq" title="Questions">
        <dl className="max-w-3xl space-y-5">
          {FAQ.map((f) => (
            <div key={f.q}>
              <dt className="font-semibold">{f.q}</dt>
              <dd className="mt-1 text-muted">{f.a}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section id="contact" title="Start a pilot">
        <p>
          Write to <a className="text-accent underline" href={CONTACT}>hello@prosperops.example</a>.
        </p>
      </Section>
    </div>
  );
}
