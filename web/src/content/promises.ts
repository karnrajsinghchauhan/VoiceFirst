// The five promises (brief v2 section 4). One owner for the wording: the site, docs and letter use it.
export interface Promise5 {
  id: "P1" | "P2" | "P3" | "P4" | "P5";
  title: string;
  body: string;
  enforced: string;
}

export const PROMISES: readonly Promise5[] = [
  {
    id: "P1",
    title: "The AI never moves money.",
    body: "A short tool allowlist. No tool can refund, cancel, re-price, issue credit or waive a fee. Any money request other than sending the pay link goes to a person.",
    enforced: "The allowlist lives outside the model; a call to any other tool raises an error. Tested on every persona, including prompt injection.",
  },
  {
    id: "P2",
    title: "A person is always one sentence away.",
    body: "Asking for a human, a dispute, a chargeback threat, sustained anger, a VIP flag or a safety issue triggers a warm transfer with a case summary. If no one is free, the agent says so and books a callback.",
    enforced: "Handoff triggers are deterministic guardrails, not model choices. The tester asserts a handoff on every trigger.",
  },
  {
    id: "P3",
    title: "Every call is disclosed and compliant.",
    body: "The first sentence says it is an AI assistant and that the call is recorded. The dialler accepts only a single-use clearance that exists after every compliance gate passes.",
    enforced: "A stateful property test checks that a call is placed if and only if every gate passes.",
  },
  {
    id: "P4",
    title: "Data stays the client's.",
    body: "PII is redacted at write time and encrypted at rest. No training on client data. Retention by purpose, erasure on request, India residency by default.",
    enforced: "Static tests prove no card fields exist; the production config refuses out-of-region providers.",
  },
  {
    id: "P5",
    title: "One switch stops everything.",
    body: "One authenticated call pauses every campaign and drops queued dials. Live calls close politely. The action is audit-logged with actor and reason.",
    enforced: "A test engages the switch on a real clock and checks that no new dial succeeds within five seconds.",
  },
];
