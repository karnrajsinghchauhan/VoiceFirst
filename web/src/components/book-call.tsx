"use client";

// Book a call. Consent to be contacted is explicit and unticked by default; the hidden
// "website" field is a honeypot that people never see and bots tend to fill.
import { useEffect, useState } from "react";

function label(slot: string): string {
  return new Date(slot).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

type State = { kind: "idle" } | { kind: "sending" } | { kind: "booked"; slot: string } | { kind: "error"; message: string };

export function BookCall() {
  const [slots, setSlots] = useState<string[] | null>(null);
  const [state, setState] = useState<State>({ kind: "idle" });

  useEffect(() => {
    fetch("/api/concierge/slots")
      .then((r) => r.json() as Promise<{ slots: string[] }>)
      .then((d) => setSlots(d.slots), () => setState({ kind: "error", message: "Could not load times. Email us instead." }));
  }, []);

  if (state.kind === "booked")
    return (
      <p role="status" className="rounded border border-line bg-surface p-6" data-testid="booked">
        Booked for {label(state.slot)} India time. You will get a calendar invite by email.
      </p>
    );

  return (
    <form
      className="grid gap-4 rounded border border-line bg-surface p-6 md:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        setState({ kind: "sending" });
        void fetch("/api/concierge/book", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            session_id: crypto.randomUUID(),
            name: f.get("name"),
            email: f.get("email"),
            company: f.get("company"),
            slot: f.get("slot"),
            consent: f.get("consent") === "on",
            website: f.get("website"),
          }),
        }).then(async (r) => {
          if (r.ok) {
            const b = (await r.json()) as { slot: string };
            setState({ kind: "booked", slot: b.slot });
          } else {
            const b = (await r.json().catch(() => null)) as { detail?: string } | null;
            setState({ kind: "error", message: b?.detail ?? "Booking failed." });
          }
        });
      }}
    >
      <label className="grid gap-1 text-sm">
        Name
        <input name="name" required maxLength={120} autoComplete="name" className="rounded border border-line px-3 py-2" />
      </label>
      <label className="grid gap-1 text-sm">
        Work email
        <input name="email" type="email" required maxLength={200} autoComplete="email" className="rounded border border-line px-3 py-2" />
      </label>
      <label className="grid gap-1 text-sm">
        Company
        <input name="company" required maxLength={160} autoComplete="organization" className="rounded border border-line px-3 py-2" />
      </label>
      <label className="grid gap-1 text-sm">
        Time (India)
        <select name="slot" required className="rounded border border-line px-3 py-2" disabled={slots === null} defaultValue="">
          <option value="" disabled>
            {slots === null ? "Loading times" : "Choose a time"}
          </option>
          {slots?.map((s) => (
            <option key={s} value={s}>
              {label(s)}
            </option>
          ))}
        </select>
      </label>
      <div className="hidden" aria-hidden="true">
        <label>
          Website
          <input name="website" tabIndex={-1} autoComplete="off" />
        </label>
      </div>
      <label className="flex items-start gap-2 text-sm md:col-span-2">
        <input type="checkbox" name="consent" required className="mt-1" />
        <span>I agree to be contacted by email about this meeting. We use your details only for that, as described in the privacy notice.</span>
      </label>
      <div className="flex items-center gap-4 md:col-span-2">
        <button type="submit" disabled={state.kind === "sending"} className="motion rounded bg-ink px-4 py-2.5 text-sm text-paper hover:bg-accent disabled:opacity-50">
          Book a call
        </button>
        {state.kind === "error" && (
          <p role="alert" className="text-sm text-fail">
            {state.message}
          </p>
        )}
      </div>
    </form>
  );
}
