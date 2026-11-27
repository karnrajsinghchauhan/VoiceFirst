// /agoda: the long-form letter to Agoda's CX leadership (brief v3, section 7).
// Private: the middleware gates it behind the passcode and every response is noindex.
// Every external fact is a <Src> into docs/sources.md; every number we measured is a
// <Measured> with its date and method; estimates say so.
import type { ReactNode } from "react";
import { Est, Measured, Spec, Src } from "@/components/claims";
import { FlowDiagram } from "@/components/flow-diagram";
import { BRAND, PITCH_NAME } from "@/config/brand";
import recorded from "@/content/demo-runs/failed_upi.json";
import type { DemoRun } from "@/lib/demo-types";
import { DiscoveryList } from "./discovery";

export const metadata = { title: `${PITCH_NAME}: a letter to Agoda`, robots: { index: false, follow: false } };

const RUN = recorded as DemoRun;
const LETTER_DATE = "27 November 2026";

function Section({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={`s${n}`} className="mt-12">
      <h2 id={`s${n}`}>
        {n}. {title}
      </h2>
      {children}
    </section>
  );
}

export default function AgodaLetter() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <article className="prose-av">
        <p className="text-sm text-muted">
          Private and confidential. Prepared for Agoda&apos;s customer experience leadership, {LETTER_DATE}.
        </p>
        <h1>A voice layer for Agoda&apos;s customers in India</h1>
        <p>
          From Karn, founder, {BRAND.legalEntity}. {PITCH_NAME} is an independent ProsperOps product and is not affiliated with or
          endorsed by Agoda. Names, bookings and amounts in this letter are synthetic.
        </p>

        <Section n={1} title="What we built">
          <p>
            We built a system that places outbound service calls to Agoda customers in India in Hindi, English and Hinglish, for
            two jobs: helping a customer finish a payment that failed or is still pending, and confirming a booking a couple of
            days before arrival. The AI never takes card details by voice; it sends an Agoda-hosted payment link over WhatsApp
            once the customer says yes. It hands every judgement call to a person. It checks every call against India&apos;s
            telecom and data-protection rules before dialling, and refuses to dial if any check fails. A fixed share of
            bookings is never called, so the effect of the calls can be measured against bookings that were left alone. The
            code is a single Python service and a Helm chart with no cloud-vendor dependencies, written so that Agoda engineers
            can read it, run it and, if you choose, take it over.
          </p>
        </Section>

        <Section n={2} title="What Agoda already does well">
          <p>
            We are writing to a team that already runs AI in service, so we start with what you have, because it shaped what we
            built.
          </p>
          <ul>
            <li>
              Your customer service leadership has said publicly that AI is now central to how you scale support but that people
              stay in charge of the outcome, that disputes stay with humans, and that the measures that matter are case
              resolution time and customer satisfaction <Src id="S-07">(August 2026)</Src>. We took that literally: our handoff
              summary is written in the shape of a case summary, we report resolution time and CSAT rather than containment
              alone, and no dispute is ever resolved by the AI.
            </li>
            <li>
              The Property AMA bot answers more than 30,000 hotel questions a day <Src id="S-08">(August 2025)</Src>, and the
              in-app AI Assistant is live in <Src id="S-09">21 markets</Src>. You have also connected to Meta&apos;s Muse in
              Singapore and Japan <Src id="S-10">(October 2026)</Src>.
            </li>
            <li>
              Your CEO has said Agoda already uses AI voice agents in conversations with suppliers <Src id="S-11">(May 2026)</Src>,
              and that the business is being rebuilt from the bottom up with interacting agents{" "}
              <Src id="S-12">(April 2026)</Src>. You build voice in-house. We are not proposing to replace that.
            </li>
            <li>
              Across Booking Holdings, voice AI now handles the majority of eligible inbound traveller calls and customer service
              cost per booking is falling at a double-digit rate <Src id="S-20">(Q2 2026 call)</Src>.
            </li>
          </ul>
          <p>
            So the question is not whether Agoda should use AI in service. It is whether there is a specific layer that is
            expensive to build well and that matters for one market. We think there is: outbound voice for India customers,
            where the language, the telecom rules and the payment habits are different enough to need their own work. What
            follows is that layer, built, tested and ready for an eight-week pilot on your traffic.
          </p>
        </Section>

        <Section n={3} title="Why India needs its own layer">
          <h3>Language</h3>
          <p>
            Indian customers do not speak a clean Hindi or a clean English on the phone; they mix them, often within one
            sentence. MakeMyTrip reports that about 70% of the voice queries to its assistant are in Hinglish{" "}
            <Src id="S-23">(May 2026)</Src>. A system tuned on English or on formal Hindi mishears amounts, dates and, most
            dangerously, refusals. Our agent mirrors the customer&apos;s language by its second turn, reads amounts back in words in
            that language (&ldquo;do hazaar saat sau unnees rupaye&rdquo;), and treats &ldquo;hmm&rdquo; or &ldquo;achha&rdquo;
            said over it as listening, not consent. Your India customers also travel in ways the system has to expect: 19% of
            Indians in your 2026 Travel Outlook weigh spiritual experiences when they plan, the highest share in Asia{" "}
            <Src id="S-17">(survey of October 2025)</Src>; Prayagraj accommodation searches rose 233% during the 2025 Maha Kumbh{" "}
            <Src id="S-18">(April 2025)</Src>; and Goa, Puri and Udaipur led domestic festive searches this year{" "}
            <Src id="S-19">(November 2026)</Src>. Our test bookings are set in Varanasi, Prayagraj, Puri, Haridwar, Shirdi and
            Udaipur for that reason.
          </p>
          <h3>Telecom rules</h3>
          <p>
            In September 2026 TRAI notified the third amendment to its commercial communications regulations{" "}
            <Src id="S-24">(05 of 2026)</Src>. Its consultation draft required automated calls, including AI voice, to be declared
            in advance, with undeclared calls treated as unsolicited commercial communication. We treat every call as an
            automated call: it must come from a declared caller ID in the right number series for its purpose, with a recorded
            consent basis, after a check of the DND registry, inside a call window, under attempt caps and cooldowns. A
            complaint pauses the caller ID; two complaints in ten days pause every campaign and page a person. None of this is
            legal advice; Indian counsel must sign off before the first live call.
          </p>
          <h3>Data protection</h3>
          <p>
            The DPDP Rules were notified on 13 November 2025; the Consent Manager provisions apply from November 2026 and the
            remaining duties from May 2027 <Src id="S-25">(phased)</Src>. We built to the full standard now: purpose limitation on
            every field the agent can read, notice in the first sentence, withdrawal by one sentence or one WhatsApp reply,
            rights requests with timers, retention by purpose, and India residency by default. Separately, the IT Rules
            amendment on synthetically generated information came into force on 20 February 2026 <Src id="S-26">(G.S.R. 120(E))</Src>;
            whether outbound AI calls are in scope is a question for counsel, but our first sentence says &ldquo;AI
            assistant&rdquo; regardless, and every recording carries a provenance hash.
          </p>
        </Section>

        <Section n={4} title="How one call works">
          <figure>
            <FlowDiagram />
            <figcaption className="text-sm text-muted">The path every call takes. A call is placed only if all checks pass.</figcaption>
          </figure>
          <p>
            A booking event arrives on Kafka: a payment failed, a payment is still pending past its threshold, or a stay is two
            days away. The holdout is decided first and is never overridden. Then eleven checks run in a fixed order. If all
            pass, the compliance module issues a single-use clearance that expires in 60 seconds, and the dialler accepts
            nothing else: there is exactly one function that can place a call, and an import rule stops any other module from
            calling it. The agent then speaks. Its first sentence discloses that it is an AI and that the call is recorded, and
            asks for the customer by first name. Nothing about the booking is said until that person confirms who they are.
          </p>
          <p>This is a full call from the engine, recorded in text mode with mock providers and a scripted customer:</p>
          <div className="not-prose my-6 space-y-3 rounded border border-line bg-surface p-4 text-sm">
            {RUN.transcript.map((t, i) => (
              <p key={i}>
                <span className="mr-2 text-xs uppercase tracking-wide text-muted">{t.speaker === "agent" ? "Agent" : "Customer"}</span>
                {t.text}
              </p>
            ))}
          </div>
          <p>
            After the call the customer receives a WhatsApp utility template with the Agoda-hosted link and the grievance
            contact. The outcome, a redacted and encrypted transcript, the tool calls, the cost and a QA score are written once
            and published to Kafka. On this run the QA score was {RUN.qa.score} out of 100 on {RUN.qa.checks.length} checks. You
            can run this and five other scenarios yourself on the private demo, including the kill switch.
          </p>
        </Section>

        <Section n={5} title="The five promises, and how each is enforced">
          <ol>
            <li>
              <strong>The AI never moves money.</strong> The agent can call ten tools: look up the booking, send the payment
              link, confirm details, record a special request, log a case, schedule a callback, transfer to a person, mark do
              not call, send the app link when asked, and end the call. None of them refunds, cancels, re-prices or waives
              anything. Any request about money other than &ldquo;send me the link&rdquo; becomes a case and a warm transfer.
              Tested: an allowlist check on every conversation, plus personas that try refund bait, chargeback threats and
              &ldquo;give me 50% off&rdquo;.
            </li>
            <li>
              <strong>A person is one sentence away.</strong> &ldquo;Insaan se baat karni hai&rdquo;, &ldquo;manager&rdquo;, a
              dispute, fraud, police, consumer court, sustained anger, a VIP flag, two failed attempts at the same step, or any
              medical or safety emergency transfers the call with a five-line summary. If nobody is free, the agent says so and
              books a callback. It never pretends.
            </li>
            <li>
              <strong>Every call is disclosed and compliant.</strong> Disclosure is in the first sentence. The checks in section
              4 run before every dial, and the decision is written whether or not the call is cleared. A property-based test
              varies bookings, consent, DND, caller IDs, clocks, complaints and the kill switch freely and checks that a call is
              placed if and only if every gate passes: <Measured id="proof" />.
            </li>
            <li>
              <strong>Data stays yours.</strong> Card numbers and OTPs are redacted from speech before the language model or
              storage sees them. Transcripts are encrypted at rest. Nothing is used to train or fine-tune a model. Each tenant
              runs in its own runtime with Postgres row-level security as a second wall.
            </li>
            <li>
              <strong>One switch stops everything.</strong> One authenticated call pauses every campaign, drops queued calls and
              ends live calls with a short, polite close, audit-logged with who and why. New dials stop{" "}
              <Measured id="killswitch" />.
            </li>
          </ol>
        </Section>

        <Section n={6} title="Proof so far, measured on test data">
          <p>
            Everything below was measured on synthetic data with mock providers and a scripted caller. It proves that the
            safety and tool layer behaves as designed. It does not prove how a real language model behaves on real Indian phone
            audio; that is what the pilot is for.
          </p>
          <table>
            <thead>
              <tr>
                <th scope="col">What</th>
                <th scope="col">Result</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Guardrails held across 30 personas in up to three languages</td>
                <td>
                  <Measured id="guardrails" />
                </td>
              </tr>
              <tr>
                <td>Refund bait, chargeback, consumer court, child on the line, prompt injection, card number, OTP</td>
                <td>
                  <Measured id="critical" />
                </td>
              </tr>
              <tr>
                <td>Calls resolved without a person, on scripted personas (not a forecast)</td>
                <td>
                  <Measured id="containment" />
                </td>
              </tr>
              <tr>
                <td>End of customer speech to first agent audio, modelled on impaired lines</td>
                <td>
                  <Measured id="latency" />
                </td>
              </tr>
              <tr>
                <td>Holdout on 1,000 seeded bookings</td>
                <td>
                  <Measured id="holdout" />
                </td>
              </tr>
              <tr>
                <td>A clearance used once under concurrent dials on Postgres</td>
                <td>
                  <Measured id="race" />
                </td>
              </tr>
              <tr>
                <td>Automated tests passing</td>
                <td>
                  <Measured id="tests" />
                </td>
              </tr>
            </tbody>
          </table>
          <p>
            Every number links to its method and date. Containment on scripted personas runs higher than it will on real calls,
            because our personas over-represent hard cases that end in a transfer and under-represent the long tail of real
            conversations; we would quote nothing above the 35-55% range for a pilot until we have your audio.
          </p>
        </Section>

        <Section n={7} title="Numbers, caller ID and the WhatsApp loop">
          <p>
            Service calls go out only from caller IDs declared for automated calling in the number series that matches their
            purpose; promotional calls are disabled in the pilot and would need a separate series, recorded promotional
            consent and a dark-pattern audit. Which series applies to Agoda&apos;s sender category, and whether you want verified
            caller name display, are questions for discovery. WhatsApp carries only utility templates, only to numbers with a
            recorded opt-in, and at most one no-answer follow-up per booking event. Meta&apos;s India utility rate is reported at
            Rs 0.115 per message before GST, and in-window utility messages became billable on 1 October 2026{" "}
            <Src id="S-30">(reported; to be confirmed on Meta&apos;s rate card)</Src>. The cost model assumes every template is paid.
          </p>
        </Section>

        <Section n={8} title="Your systems, and honest integration effort">
          <p>
            Your platform runs on your own private cloud, with Fleet on Kubernetes and Spark for data{" "}
            <Src id="S-15">(public engineering writing)</Src>, Kafka at more than three trillion records a day{" "}
            <Src id="S-14">(2025)</Src>, and a partner help centre on Zendesk <Src id="S-15">(public site)</Src>. We designed for
            that, not for a public cloud:
          </p>
          <table>
            <thead>
              <tr>
                <th scope="col">Integration</th>
                <th scope="col">What it takes</th>
                <th scope="col">Effort</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Booking events from Kafka</td>
                <td>A consumer on your topic, mapping your event to our booking-event schema; at-least-once delivery is already handled</td>
                <td>
                  <Est>3 to 5 engineer-days</Est>
                </td>
              </tr>
              <tr>
                <td>Zendesk</td>
                <td>An adapter exists; field mapping and a sandbox token</td>
                <td>
                  <Est>2 to 3 days</Est>
                </td>
              </tr>
              <tr>
                <td>Warm transfer to your contact centre</td>
                <td>Depends on the CCaaS platform and its queue API, which we do not know yet</td>
                <td>
                  <Est>5 to 10 days</Est>
                </td>
              </tr>
              <tr>
                <td>Running on your Kubernetes</td>
                <td>The Helm chart has no cloud-vendor dependencies; secrets, ingress and Postgres are yours</td>
                <td>
                  <Est>about 5 days with your platform team</Est>
                </td>
              </tr>
            </tbody>
          </table>
          <p>
            For the pilot we would run it as a managed service in an India region, so that none of this blocks a start; the
            same chart moves onto your infrastructure afterwards if you want it to.
          </p>
        </Section>

        <Section n={9} title="Security and data">
          <p>
            Least-privilege roles (admin, operations, auditor, read-only), single sign-on through your identity provider,
            scoped and rotatable API keys, and an audit log of every privileged action. Encryption in transit and at rest.
            Personal data redacted at write time; card data never stored. Retention by purpose (audio 30 days, redacted
            transcripts 180 days by default) with a nightly purge that logs its counts. Incident timers built for CERT-In&apos;s
            six-hour report <Src id="S-29">(Directions of April 2022)</Src> and the DPDP breach timelines. We hold no SOC 2 or ISO
            27001 certificate today; we say so plainly and use OWASP ASVS Level 2 as our checklist. The full security pack and
            a questionnaire answer sheet are ready for your review.
          </p>
        </Section>

        <Section n={10} title="The pilot we propose">
          <ul>
            <li>
              <strong>Scope:</strong> <Spec of="pilot.scope">eight weeks, India-originating bookings, payment rescue and
              pre-arrival confirmation, with a 10% no-call holdout</Spec>.
            </li>
            <li>
              <strong>Success measures, agreed before we start:</strong> payment recovery against the holdout with a 95%
              confidence interval; case resolution time and CSAT for the calls that reach a person; complaint rate; cost per
              resolved contact.
            </li>
            <li>
              <strong>Commercials:</strong> <Spec of="offer.pilot">a fixed USD 20,000 for the pilot, half invoiced at the start
              and half at risk against the holdout result</Spec>. After the pilot,{" "}
              <Spec of="offer.run">USD 6,000 a month plus Rs 25 per AI-resolved contact, or USD 0.09 per outbound minute</Spec>,
              with a build-operate-transfer option onto your infrastructure.
            </li>
            <li>
              <strong>Weeks 1-2:</strong> discovery answers, counsel review, caller-ID declaration, WhatsApp templates approved,
              Kafka and CRM connected in a sandbox. <strong>Weeks 3-4:</strong> evaluation on a sample of your own call audio;
              internal test calls. <strong>Weeks 5-8:</strong> live traffic with the holdout; weekly review of every failed or
              low-scoring call; a written result at the end.
            </li>
          </ul>
        </Section>

        <Section n={11} title="What we need from you">
          <p>These are the questions only Agoda can answer. Nothing in this letter assumes the answers.</p>
          <DiscoveryList />
        </Section>

        <Section n={12} title="Who we are">
          <p>
            {PITCH_NAME} is built by {BRAND.legalEntity}, a ProsperOps company in Delhi-NCR, founded by Karn. We are small, and we
            would rather say that here than have you discover it. That is also why the code is written for handover: one
            service, typed throughout, with the safety rules enforced by tests rather than by our discipline. Company details:{" "}
            {BRAND.legalEntity}, GSTIN {BRAND.gstin}, {BRAND.address}. Contact: {BRAND.email}.
          </p>
          <p>Thank you for reading this far.</p>
          <p>Karn</p>
        </Section>
      </article>
    </div>
  );
}
