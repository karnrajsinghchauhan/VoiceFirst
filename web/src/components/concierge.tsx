"use client";

// Text concierge. Answers come only from the product pages, each with a citation; when it is
// unsure it says so and offers a call. Voice is added once real-time speech is switched on.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

interface Answer {
  answer: string;
  citations: { title: string; url: string }[];
  confidence: "high" | "low";
  actions: { type: "book_meeting" }[];
}

type Turn = { who: "you"; text: string } | { who: "concierge"; reply: Answer } | { who: "error"; text: string };

const HIDDEN_ON = ["/console", "/demo", "/agoda", "/gate"];

export function Concierge() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const session = useRef<string>("");
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    session.current = crypto.randomUUID();
    const fromHash = () => {
      if (window.location.hash === "#concierge") setOpen(true);
    };
    fromHash();
    window.addEventListener("hashchange", fromHash);
    return () => window.removeEventListener("hashchange", fromHash);
  }, []);

  useEffect(() => {
    if (open) input.current?.focus();
  }, [open]);

  if (HIDDEN_ON.some((p) => path === p || path.startsWith(`${p}/`))) return null;

  async function ask(message: string): Promise<void> {
    setTurns((t) => [...t, { who: "you", text: message }]);
    setBusy(true);
    try {
      const res = await fetch("/api/concierge/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ session_id: session.current, message }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { detail?: string } | null;
        setTurns((t) => [...t, { who: "error", text: body?.detail ?? "Something went wrong. Please try again." }]);
        return;
      }
      const reply = (await res.json()) as Answer;
      setTurns((t) => [...t, { who: "concierge", reply }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div data-concierge className="fixed bottom-4 right-4 z-30 flex flex-col items-end">
      {open && (
        <section
          id="concierge"
          aria-label="Concierge"
          className="mb-3 flex max-h-[70vh] w-[min(24rem,calc(100vw-2rem))] flex-col rounded border border-line bg-surface"
        >
          <header className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="font-display text-base">Ask about the product</h2>
            <button className="text-sm text-muted underline" onClick={() => setOpen(false)}>
              Close
            </button>
          </header>
          <ol className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm" aria-live="polite" data-testid="concierge-log">
            {turns.length === 0 && (
              <li className="text-muted">
                I answer from this site&apos;s product, security and pricing pages, and I link the page I used. I do not know
                anything else, and I will say so.
              </li>
            )}
            {turns.map((t, i) =>
              t.who === "you" ? (
                <li key={i} className="text-right">
                  <span className="inline-block rounded bg-accent-soft px-3 py-2">{t.text}</span>
                </li>
              ) : t.who === "error" ? (
                <li key={i} role="alert" className="text-fail">
                  {t.text}
                </li>
              ) : (
                <li key={i} data-confidence={t.reply.confidence}>
                  <p>{t.reply.answer}</p>
                  {t.reply.citations.length > 0 && (
                    <p className="mt-1 text-xs text-muted">
                      Source:{" "}
                      {t.reply.citations.map((c, j) => (
                        <span key={c.url}>
                          {j > 0 && ", "}
                          <Link href={c.url} className="underline" data-testid="citation">
                            {c.title}
                          </Link>
                        </span>
                      ))}
                    </p>
                  )}
                  {t.reply.actions.some((a) => a.type === "book_meeting") && (
                    <p className="mt-1">
                      <Link href="/voice#book" className="underline" onClick={() => setOpen(false)}>
                        Book a call
                      </Link>
                    </p>
                  )}
                </li>
              ),
            )}
          </ol>
          <form
            className="flex gap-2 border-t border-line p-3"
            onSubmit={(e) => {
              e.preventDefault();
              const m = draft.trim();
              if (!m || busy) return;
              setDraft("");
              void ask(m);
            }}
          >
            <label htmlFor="concierge-input" className="sr-only">
              Your question
            </label>
            <input
              id="concierge-input"
              ref={input}
              value={draft}
              maxLength={600}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="How does the holdout work?"
              className="flex-1 rounded border border-line px-3 py-2 text-sm"
              autoComplete="off"
            />
            <button type="submit" disabled={busy} className="motion rounded bg-ink px-3 py-2 text-sm text-paper disabled:opacity-50">
              Ask
            </button>
          </form>
        </section>
      )}
      <button
        type="button"
        aria-expanded={open}
        aria-controls="concierge"
        onClick={() => setOpen((o) => !o)}
        className="motion rounded-full border border-ink bg-surface px-4 py-2 text-sm hover:bg-ink hover:text-paper"
      >
        {open ? "Hide concierge" : "Ask the concierge"}
      </button>
    </div>
  );
}
