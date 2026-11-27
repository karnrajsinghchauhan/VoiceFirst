// Server-side security helpers for the route handlers: console session cookies, CSRF
// (double-submit), the private-page passcode gate, and per-client rate limits.
import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { cookies, headers } from "next/headers";

export const SESSION_COOKIE = "av_session";
export const CSRF_COOKIE = "av_csrf";
export const CSRF_HEADER = "x-csrf-token";
export const GATE_COOKIE = "av_gate";

// Secure cookies are accepted on http://localhost by browsers, so tests use the same flags.
const BASE = { secure: true, sameSite: "strict" as const, path: "/" };
const EIGHT_HOURS = 8 * 60 * 60;

export async function setSession(token: string): Promise<void> {
  const jar = await cookies();
  jar.set(SESSION_COOKIE, token, { ...BASE, httpOnly: true, maxAge: EIGHT_HOURS });
  jar.set(CSRF_COOKIE, randomBytes(24).toString("hex"), { ...BASE, httpOnly: false, maxAge: EIGHT_HOURS });
}

export async function clearSession(): Promise<void> {
  const jar = await cookies();
  jar.delete(SESSION_COOKIE);
  jar.delete(CSRF_COOKIE);
}

export async function sessionToken(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
}

function sameText(a: string, b: string): boolean {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

/** Double-submit: the header must equal the CSRF cookie. Cross-site pages can read neither. */
export async function csrfValid(): Promise<boolean> {
  const cookie = (await cookies()).get(CSRF_COOKIE)?.value;
  const header = (await headers()).get(CSRF_HEADER);
  return Boolean(cookie && header && sameText(cookie, header));
}

/** The passcode for /demo and /agoda. Unset means the pages stay closed. */
export function demoPasscode(): string | null {
  const p = process.env.AV_DEMO_PASSCODE;
  return p && p.length >= 8 ? p : null;
}

/** Cookie value proving the visitor entered the passcode; middleware checks the same digest. */
export function gateDigest(passcode: string): string {
  return createHmac("sha256", passcode).update("av-gate-v1").digest("hex");
}

export function passcodeMatches(candidate: string): boolean {
  const expected = demoPasscode();
  if (expected === null) return false;
  const a = createHash("sha256").update(candidate).digest();
  const b = createHash("sha256").update(expected).digest();
  return timingSafeEqual(a, b);
}

export async function setGate(passcode: string): Promise<void> {
  (await cookies()).set(GATE_COOKIE, gateDigest(passcode), { ...BASE, httpOnly: true, maxAge: EIGHT_HOURS });
}

export async function gateValid(): Promise<boolean> {
  const passcode = demoPasscode();
  const value = (await cookies()).get(GATE_COOKIE)?.value;
  return Boolean(passcode && value && sameText(value, gateDigest(passcode)));
}

// Fixed-window limits per client and bucket. In-process: enough for one web instance; the
// engine applies its own limits to the API behind it.
const WINDOW_MS = 60_000;
// Requests per client per minute. AV_RATE_LIMIT_<BUCKET> overrides one bucket, so the
// Playwright suite (every scenario and sign-in within a minute) can lift it; production
// keeps these defaults.
const DEFAULT_LIMITS = { ask: 20, book: 5, gate: 10, demo: 30, session: 10 } as const;

function limit(bucket: keyof typeof DEFAULT_LIMITS): number {
  const raw = Number(process.env[`AV_RATE_LIMIT_${bucket.toUpperCase()}`]);
  return Number.isInteger(raw) && raw > 0 ? raw : DEFAULT_LIMITS[bucket];
}

const LIMITS: Record<keyof typeof DEFAULT_LIMITS, number> = {
  ask: limit("ask"),
  book: limit("book"),
  gate: limit("gate"),
  demo: limit("demo"),
  session: limit("session"),
};
const hits = new Map<string, { start: number; count: number }>();

export type Bucket = keyof typeof DEFAULT_LIMITS;

export async function clientKey(): Promise<string> {
  const h = await headers();
  return h.get("x-forwarded-for")?.split(",")[0]?.trim() || h.get("x-real-ip") || "local";
}

export async function rateLimited(bucket: Bucket): Promise<boolean> {
  const key = `${bucket}:${await clientKey()}`;
  const now = Date.now();
  const entry = hits.get(key);
  if (!entry || now - entry.start >= WINDOW_MS) {
    hits.set(key, { start: now, count: 1 });
    return false;
  }
  entry.count += 1;
  return entry.count > LIMITS[bucket];
}

export function jsonError(status: number, error: string, detail: string): Response {
  return Response.json({ error, detail }, { status });
}
