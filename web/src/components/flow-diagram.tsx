// Inline SVG so the diagram ships with the page and needs no image assets.
const STEPS: readonly { label: string; sub: string }[] = [
  { label: "booking_event", sub: "payment_failed / pending, confirmed" },
  { label: "Holdout", sub: "10% never called" },
  { label: "11 compliance gates", sub: "consent, DND, CLI, window, caps" },
  { label: "AI call", sub: "discloses AI and recording first" },
  { label: "Consent", sub: "explicit \"haan, bhej do\"" },
  { label: "WhatsApp pay link", sub: "Agoda-hosted, utility template" },
];

export function FlowDiagram() {
  const boxW = 150;
  const gap = 22;
  const y = 20;
  const h = 74;
  const width = STEPS.length * boxW + (STEPS.length - 1) * gap + 20;
  const outcomeY = y + h + 60;
  return (
    <svg
      viewBox={`0 0 ${width} ${outcomeY + h + 20}`}
      role="img"
      aria-labelledby="flow-title"
      className="w-full"
    >
      <title id="flow-title">
        Flow: booking event, holdout, eleven compliance gates, AI call with disclosure, consent,
        WhatsApp payment link, then a logged outcome or a warm handoff to a human.
      </title>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="#5f5b53" />
        </marker>
      </defs>
      {STEPS.map((step, i) => {
        const x = 10 + i * (boxW + gap);
        return (
          <g key={step.label}>
            <rect x={x} y={y} width={boxW} height={h} rx={6} fill="#ffffff" stroke="#2f5d50" />
            <text x={x + boxW / 2} y={y + 30} textAnchor="middle" fontSize={13} fontWeight={600} fill="#1c1b19">
              {step.label}
            </text>
            <text x={x + boxW / 2} y={y + 52} textAnchor="middle" fontSize={10} fill="#5f5b53">
              {step.sub}
            </text>
            {i < STEPS.length - 1 && (
              <line
                x1={x + boxW}
                y1={y + h / 2}
                x2={x + boxW + gap - 2}
                y2={y + h / 2}
                stroke="#5f5b53"
                markerEnd="url(#arrow)"
              />
            )}
          </g>
        );
      })}
      {/* Every stage can end in a logged outcome; judgement calls go to a human. */}
      <rect x={10} y={outcomeY} width={width / 2 - 20} height={h} rx={6} fill="#e6efeb" stroke="#2f5d50" />
      <text x={10 + (width / 2 - 20) / 2} y={outcomeY + 32} textAnchor="middle" fontSize={13} fontWeight={600} fill="#1c1b19">
        Outcome logged
      </text>
      <text x={10 + (width / 2 - 20) / 2} y={outcomeY + 52} textAnchor="middle" fontSize={10} fill="#5f5b53">
        call_outcome on Kafka; lift measured vs holdout
      </text>
      <rect x={width / 2 + 10} y={outcomeY} width={width / 2 - 20} height={h} rx={6} fill="#f7e9e0" stroke="#8a3b12" />
      <text x={width / 2 + 10 + (width / 2 - 20) / 2} y={outcomeY + 32} textAnchor="middle" fontSize={13} fontWeight={600} fill="#1c1b19">
        Warm handoff to a human
      </text>
      <text x={width / 2 + 10 + (width / 2 - 20) / 2} y={outcomeY + 52} textAnchor="middle" fontSize={10} fill="#5f5b53">
        disputes, refunds, anger, VIP, safety; with a 5-line summary
      </text>
      <line x1={width / 2} y1={y + h} x2={width / 4} y2={outcomeY - 2} stroke="#5f5b53" markerEnd="url(#arrow)" />
      <line x1={width / 2} y1={y + h} x2={(3 * width) / 4} y2={outcomeY - 2} stroke="#5f5b53" markerEnd="url(#arrow)" />
    </svg>
  );
}
