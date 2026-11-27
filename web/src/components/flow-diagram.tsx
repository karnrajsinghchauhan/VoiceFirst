// How one call works. Inline SVG: ships with the page, scales, prints, and reads in a screen reader.
const STEPS: readonly { label: string; sub: string }[] = [
  { label: "Booking event", sub: "payment failed or pending, or a stay coming up" },
  { label: "Holdout", sub: "a fixed share of bookings is never called" },
  { label: "Compliance gates", sub: "consent, DND, declared caller ID, call window, caps" },
  { label: "Single-use clearance", sub: "the only thing the dialler accepts" },
  { label: "AI call", sub: "discloses AI and recording, then confirms identity" },
  { label: "WhatsApp pay link", sub: "Agoda-hosted page; no card details by voice" },
  { label: "Outcome logged", sub: "CRM, Kafka, QA score; lift against the holdout" },
];

const INK = "#141414";
const MUTED = "#57544e";
const LINE = "#dedad1";
const ACCENT = "#1f4e5f";

export function FlowDiagram() {
  const w = 640;
  const boxW = 380;
  const boxH = 58;
  const gap = 22;
  const x = 20;
  const branchX = x + boxW + 40;
  const height = STEPS.length * (boxH + gap) + 10;
  const callY = 4 * (boxH + gap) + 10;
  return (
    <svg viewBox={`0 0 ${w} ${height}`} role="img" aria-labelledby="flow-title flow-desc" className="h-auto w-full max-w-2xl">
      <title id="flow-title">How one call works</title>
      <desc id="flow-desc">
        A booking event passes the holdout and the compliance gates, receives a single-use clearance, and only then is
        dialled. The AI call discloses itself, confirms identity and sends a WhatsApp payment link. Any judgement call goes
        to a human with a case summary. Every call ends in a logged outcome.
      </desc>
      <defs>
        <marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill={MUTED} />
        </marker>
      </defs>
      {STEPS.map((step, i) => {
        const y = 10 + i * (boxH + gap);
        return (
          <g key={step.label}>
            <rect x={x} y={y} width={boxW} height={boxH} rx={4} fill="#ffffff" stroke={i === 3 ? ACCENT : LINE} strokeWidth={i === 3 ? 1.5 : 1} />
            <text x={x + 16} y={y + 24} fontSize={14} fontWeight={600} fill={INK} fontFamily="var(--font-sans)">
              {step.label}
            </text>
            <text x={x + 16} y={y + 44} fontSize={12} fill={MUTED} fontFamily="var(--font-sans)">
              {step.sub}
            </text>
            {i < STEPS.length - 1 && (
              <line x1={x + 40} y1={y + boxH} x2={x + 40} y2={y + boxH + gap - 2} stroke={MUTED} markerEnd="url(#flow-arrow)" />
            )}
          </g>
        );
      })}
      <line x1={x + boxW} y1={callY + boxH / 2} x2={branchX - 2} y2={callY + boxH / 2} stroke={MUTED} markerEnd="url(#flow-arrow)" />
      <rect x={branchX} y={callY - 6} width={w - branchX - 10} height={boxH + 12} rx={4} fill="#ffffff" stroke={ACCENT} />
      <text x={branchX + 12} y={callY + 20} fontSize={14} fontWeight={600} fill={INK} fontFamily="var(--font-sans)">
        Human
      </text>
      <text x={branchX + 12} y={callY + 40} fontSize={12} fill={MUTED} fontFamily="var(--font-sans)">
        money, disputes,
      </text>
      <text x={branchX + 12} y={callY + 56} fontSize={12} fill={MUTED} fontFamily="var(--font-sans)">
        anger, safety
      </text>
    </svg>
  );
}
