/* Generated from contracts/schemas. Do not edit; run `make gen`. */

/**
 * A booking state change from Agoda. Every leaf field carries x-purposes: the call purposes allowed to read it (REQ-DPDP-02).
 */
export interface BookingEvent {
  schema_version: "1.0.0";
  tenant_id: string;
  trace_id: string;
  event_id: string;
  occurred_at: string;
  /**
   * Opaque. Never spoken in full; at most the last 4 characters.
   */
  booking_id: string;
  status: "payment_failed" | "payment_pending" | "confirmed" | "cancelled";
  payment_option: "pay_now" | "bnpl" | "zero_pay" | "pay_at_hotel";
  payment_due_at: string | null;
  amount_due: Money;
  property: {
    name: string;
    city: string;
    state: string;
    tier: number;
  };
  stay: {
    check_in: string;
    check_out: string;
    guests: number;
  };
  customer: {
    first_name: string;
    phone_e164: string;
    preferred_language: "hi" | "en" | "hinglish" | "unknown";
    whatsapp_opt_in: null | {
      at: string;
      source: string;
    };
  };
  flags: {
    vip: boolean;
    minor_suspected: boolean;
  };
  /**
   * @minItems 1
   */
  purposes_allowed: ["J1" | "J2", ...("J1" | "J2")[]];
}
export interface Money {
  value: string;
  currency: string;
}
