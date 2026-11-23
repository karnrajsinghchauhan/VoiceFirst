// Home-page FAQ. Answers use the claims markup (components/claims.tsx) for any number.
export const FAQ: readonly { q: string; a: string }[] = [
  {
    q: "Is this an Agoda product?",
    a: "No. It is an independent product built for Agoda's India customers and offered to Agoda. It is not affiliated with or endorsed by Agoda.",
  },
  {
    q: "Does the AI ever take card details or an OTP?",
    a: "No. Speech is redacted before the model sees it, the agent stops the customer politely if they start reading a card number, and payment happens on an Agoda-hosted page linked over WhatsApp.",
  },
  {
    q: "Can it refund, cancel or change a price?",
    a: "No tool exists that can. Any money request other than sending the payment link becomes a case and a warm transfer to a person.",
  },
  {
    q: "What happens when someone says stop calling?",
    a: "The number is opted out on the spot, the agent confirms once and ends the call, and the system will not ask that number for consent again for [[spec:compliance.opt_out_lock_days|90 days]].",
  },
  {
    q: "How do you know it works?",
    a: "A share of bookings is never called. Comparing recovery between called and not-called bookings gives the lift, with a confidence interval, instead of a before-and-after guess.",
  },
  {
    q: "Is it live?",
    a: "Not yet. The engine, the compliance proofs and the tester run on test data. No real customer has been called. Real providers switch on only after keys and counsel sign-off.",
  },
  {
    q: "Can it run on our own infrastructure?",
    a: "Yes. The same Helm chart we run installs on your Kubernetes, with Postgres and a Kafka-API event bus. We hand it over when you are ready.",
  },
];
