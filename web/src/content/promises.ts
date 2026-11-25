// The five promises (brief section 4). Shared by the site and the docs so the wording has one owner.
export interface Promise5 {
  id: "P1" | "P2" | "P3" | "P4" | "P5";
  title: string;
  body: string;
}

export const PROMISES: readonly Promise5[] = [
  {
    id: "P1",
    title: "The AI never moves money.",
    body: "A short tool allowlist. No tool can refund, cancel, re-price, issue credit or waive a fee. Any money request other than sending the pay link goes to a human.",
  },
  {
    id: "P2",
    title: "A human is always one sentence away.",
    body: "\"Insaan se baat karni hai\", a dispute, a chargeback threat, sustained anger, a VIP flag or a safety issue triggers a warm transfer with a case summary. If no one is free, the agent says so and books a callback.",
  },
  {
    id: "P3",
    title: "Every call is disclosed and compliant.",
    body: "The first sentence says it is an AI assistant and that the call is recorded. The dialer accepts only a single-use clearance that exists after eleven compliance gates pass.",
  },
  {
    id: "P4",
    title: "Data stays the client's.",
    body: "PII is redacted at write time and encrypted at rest. No training on client data. Retention by purpose, erasure on request, India residency by default.",
  },
  {
    id: "P5",
    title: "One switch stops everything.",
    body: "One authenticated call pauses every campaign and drops queued dials within five seconds. Live calls close politely. The action is audit-logged with actor and reason.",
  },
];
