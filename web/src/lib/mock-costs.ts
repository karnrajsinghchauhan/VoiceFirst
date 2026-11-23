// Mock of GET /costs. The engine computes this from its unit-price config; the mock uses the
// same defaults so the console renders realistically. Anything not in docs/sources.md is an
// estimate and says so.
import type { CostBreakdown, CostComponent } from "./console-types";

const SOURCES = "docs/sources.md";
const CHECKED = "2026-11 (per brief; not re-fetched)";

// Assumptions behind per-minute figures for items priced per message or per character.
const ASSUMPTIONS = {
  avg_call_minutes: 1.5,
  agent_chars_per_minute: 360,
  resolution_rate: 0.5,
  whatsapp_templates_per_call: 1,
};

const COMPONENTS: CostComponent[] = [
  { name: "Telephony (Plivo India, 30-s pulse)", unit: "per minute", unit_price: "Rs 0.38", source_url: `${SOURCES} (carried from earlier research)`, checked_at: CHECKED, per_minute_paise: 38, estimate: true },
  { name: "A2P termination charge", unit: "per call", unit_price: "unknown", source_url: "discovery question", checked_at: "not known", per_minute_paise: 0, estimate: true },
  { name: "Speech-to-text (Sarvam)", unit: "per minute", unit_price: "Rs 0.49", source_url: `${SOURCES}#S-31`, checked_at: "2026-11", per_minute_paise: 49, estimate: false },
  { name: "Language model", unit: "per minute of call", unit_price: "Rs 0.10", source_url: "estimate", checked_at: "2026-11-23", per_minute_paise: 10, estimate: true },
  { name: "Text-to-speech (Sarvam Bulbul v3)", unit: "per 1,000 characters", unit_price: "Rs 3.00", source_url: `${SOURCES}#S-31`, checked_at: "2026-11", per_minute_paise: 108, estimate: false },
  { name: "Orchestration and infrastructure", unit: "per minute", unit_price: "Rs 0.05", source_url: "estimate", checked_at: "2026-11-23", per_minute_paise: 5, estimate: true },
  { name: "WhatsApp utility template (+18% GST)", unit: "per message", unit_price: "Rs 0.1357", source_url: `${SOURCES}#S-30`, checked_at: "2026", per_minute_paise: 9, estimate: false },
  { name: "Storage and QA", unit: "per minute", unit_price: "Rs 0.02", source_url: "estimate", checked_at: "2026-11-23", per_minute_paise: 2, estimate: true },
];

const PER_MINUTE = COMPONENTS.reduce((sum, c) => sum + c.per_minute_paise, 0);

export const MOCK_COSTS: CostBreakdown = {
  as_of: "2026-11-23",
  currency: "INR",
  components: COMPONENTS,
  per_minute_paise: PER_MINUTE,
  per_resolved_contact_paise: Math.round((PER_MINUTE * ASSUMPTIONS.avg_call_minutes) / ASSUMPTIONS.resolution_rate),
  assumptions: ASSUMPTIONS,
  comparison: [
    { vendor: "Vapi (hosting only)", price: "USD 0.05", unit: "per minute", source_url: "carried from earlier research; unverified", checked_at: "re-check before quoting" },
    { vendor: "Retell", price: "USD 0.07-0.31", unit: "per minute", source_url: "carried from earlier research; unverified", checked_at: "re-check before quoting" },
    { vendor: "ElevenLabs Agents (overage)", price: "USD 0.08", unit: "per minute", source_url: "carried from earlier research; unverified", checked_at: "re-check before quoting" },
  ],
};
