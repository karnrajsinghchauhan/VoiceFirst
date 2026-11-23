// One owner for the changelog; /changelog and /docs/changelog both render it.
export const CHANGELOG: readonly { date: string; title: string; body: string }[] = [
  {
    date: "2026-11-23",
    title: "Identity-first openings",
    body: "The call discloses the AI and the recording, then asks for the booker by name. Nothing about the booking is said until they confirm.",
  },
  {
    date: "2026-11-23",
    title: "Commit gate",
    body: "A git hook blocks any commit unless the full check suite passes.",
  },
  {
    date: "2026-11-23",
    title: "End-to-end pilot path",
    body: "Booking event to gates, dial, agent, WhatsApp link, CRM case and encrypted transcript, on mock providers.",
  },
  {
    date: "2026-11-23",
    title: "Failure drills",
    body: "Speech, model, telephony, WhatsApp, event bus and database failures raise typed errors; none switches provider.",
  },
  {
    date: "2026-11-23",
    title: "Compliance proof",
    body: "A stateful property test checks that a call is placed if and only if every gate passes, against an independently written oracle.",
  },
];
