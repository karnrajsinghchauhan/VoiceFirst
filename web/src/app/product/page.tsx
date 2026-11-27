import { MEASURED, MEASURED_NOTE } from "@/components/claims";
import { FlowDiagram } from "@/components/flow-diagram";
import { PageHeader, Section } from "@/components/section";
import { PROMISES } from "@/content/promises";

export const metadata = {
  title: "Product",
  description: "How one call works, the five promises and how each is enforced, and what we have measured so far.",
};

export default function ProductPage() {
  return (
    <>
      <PageHeader
        kicker="Product"
        title="Outbound service calls in Hindi, English and Hinglish, checked before every dial"
        intro="Two jobs: helping a customer finish a failed or pending payment, and confirming a booking before arrival. Every judgement call goes to a person."
      />
      <Section id="how" kicker="How one call works" title="Nothing is dialled until every check passes">
        <div className="grid gap-10 md:grid-cols-2">
          <FlowDiagram />
          <div className="max-w-xl space-y-4">
            <p>
              A booking event arrives. A fixed share of bookings is held out and never called, so the effect can be measured.
              Then consent, the DND registry, the declared caller ID and its number series, the call window and attempt caps are
              checked. Only if all pass does the compliance module issue a single-use clearance, the one thing the dialler accepts.
            </p>
            <p>
              The agent discloses that it is an AI and that the call is recorded, asks for the customer by name, and says nothing
              about the booking until they confirm. Payment happens on a hosted page sent by WhatsApp, never by voice.
            </p>
          </div>
        </div>
      </Section>
      <Section id="promises" kicker="Five promises" title="What the system will never do, and how that is enforced">
        <ol className="grid gap-8 md:grid-cols-2">
          {PROMISES.map((p) => (
            <li key={p.id} className="border-t border-line pt-4">
              <h3 className="font-display text-xl">{p.title}</h3>
              <p className="mt-2">{p.body}</p>
              <p className="mt-2 text-sm text-muted">{p.enforced}</p>
            </li>
          ))}
        </ol>
      </Section>
      <Section id="proof" kicker="Proof" title="Measured on test data, with method and date">
        <p className="max-w-3xl text-muted">{MEASURED_NOTE}</p>
        <dl className="mt-8 grid gap-6 md:grid-cols-2">
          {MEASURED.map((m) => (
            <div key={m.id} id={`proof-${m.id}`} className="scroll-mt-8 border-t border-line pt-4 target:bg-accent-soft">
              <dt className="text-sm text-muted">{m.label}</dt>
              <dd className="mt-1 font-display text-2xl" data-claim="measured">
                {m.value}
              </dd>
              <dd className="mt-1 text-sm text-muted">
                <time dateTime={m.date}>{m.date}</time>. {m.method}
              </dd>
            </div>
          ))}
        </dl>
      </Section>
      <Section id="demo" kicker="The recorded call" title="How the call on the home page was made">
        <p className="max-w-3xl">
          The home page replays a call recorded from the engine: the real gates, agent and post-call code, running in text mode
          with mock speech, a mock model and a scripted customer. Display times are spaced out for reading; the order and the
          words are exactly what the engine produced. A private live version runs every scenario on demand.
        </p>
      </Section>
      <Section id="deployment" kicker="Private deployment" title="Runs on your infrastructure when you want it to">
        <p className="max-w-3xl">
          One Python service and a Helm chart with no cloud-vendor dependencies. It speaks the Kafka API, writes cases to the CRM
          you use, and keeps data in India by default. Start as a managed service; move it onto your Kubernetes later.
        </p>
      </Section>
    </>
  );
}
