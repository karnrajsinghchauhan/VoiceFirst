// Shape of POST /demo/run on the engine. Recorded runs in content/demo-runs/ use it too.

export const SCENARIOS = [
  { id: "failed_upi", title: "Failed UPI payment" },
  { id: "confirmation", title: "Booking confirmation" },
  { id: "angry_refund", title: "Angry refund request" },
  { id: "stop_calling", title: "Stop calling me" },
  { id: "child_answers", title: "Child answers" },
  { id: "card_number", title: "Customer reads out a card number" },
  { id: "cars24_inspection", title: "Cars24: home inspection confirmation" },
  { id: "cars24_reschedule", title: "Cars24: test drive needs a new time" },
] as const;

export type ScenarioId = (typeof SCENARIOS)[number]["id"];

export function isScenario(value: unknown): value is ScenarioId {
  return SCENARIOS.some((s) => s.id === value);
}

export type EventKind = "holdout" | "gate" | "clearance" | "disclosure" | "tool" | "whatsapp" | "crm" | "qa" | "cost" | "end";

export interface DemoEvent {
  t_ms: number;
  kind: EventKind;
  label: string;
  status: "pass" | "fail" | "info";
  detail: Partial<Record<string, string | number | null>>;
}

export interface DemoRun {
  run_id: string;
  scenario: ScenarioId;
  mode: "text" | "voice";
  // Present on recorded runs; the live engine fills them too.
  recorded_at?: string;
  method?: string;
  events: DemoEvent[];
  transcript: { speaker: "agent" | "customer"; text: string; t_ms: number }[];
  whatsapp_preview: { template: string; language: string; body: string } | null;
  crm_ticket: { ticket_id: string; subject: string; priority: string } | null;
  qa: { score: number; checks: { name: string; passed: boolean }[] };
  cost_paise: { telephony: number; stt: number; tts: number; llm: number; whatsapp: number; total: number };
  latency_ms: { p50: number; p95: number; per_turn: number[] };
}

export interface KillSwitchResult {
  engaged: boolean;
  // Engine-side time from request to the dispatcher refusing new dials.
  stopped_in_ms: number;
}
