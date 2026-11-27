// Every request: a per-request CSP nonce (no 'unsafe-inline' scripts), noindex on private
// routes, and the passcode gate in front of /demo and /agoda.
import { NextResponse, type NextRequest } from "next/server";

const PRIVATE = ["/demo", "/agoda", "/console", "/gate"];
const GATED = ["/demo", "/agoda", "/api/demo"];

function startsWithAny(path: string, prefixes: readonly string[]): boolean {
  return prefixes.some((p) => path === p || path.startsWith(`${p}/`));
}

function hex(buf: ArrayBuffer): string {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Same digest as lib/server/security.ts gateDigest, computed with Web Crypto (edge runtime).
async function gateDigest(passcode: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(passcode), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode("av-gate-v1")));
}

async function gateOpen(req: NextRequest): Promise<boolean> {
  const passcode = process.env.AV_DEMO_PASSCODE;
  if (!passcode || passcode.length < 8) return false;
  const value = req.cookies.get("av_gate")?.value;
  return value !== undefined && value === (await gateDigest(passcode));
}

function csp(nonce: string, host: string): string {
  const dev = process.env.NODE_ENV !== "production";
  const local = host.startsWith("localhost") || host.startsWith("127.0.0.1");
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    // next/font and React inject style attributes; styles cannot execute code.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "frame-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    ...(local ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}

export async function middleware(req: NextRequest): Promise<NextResponse> {
  const path = req.nextUrl.pathname;

  if (startsWithAny(path, GATED) && !(await gateOpen(req))) {
    if (path.startsWith("/api/")) return NextResponse.json({ error: "gate", detail: "passcode required" }, { status: 401 });
    const url = req.nextUrl.clone();
    url.pathname = "/gate";
    url.search = `?next=${encodeURIComponent(path)}`;
    return NextResponse.redirect(url);
  }

  const nonce = btoa(crypto.randomUUID());
  const policy = csp(nonce, req.headers.get("host") ?? "");
  const requestHeaders = new Headers(req.headers);
  // Next reads the nonce from the request's CSP header and applies it to its own scripts.
  requestHeaders.set("content-security-policy", policy);
  requestHeaders.set("x-nonce", nonce);
  const res = NextResponse.next({ request: { headers: requestHeaders } });
  res.headers.set("content-security-policy", policy);
  if (startsWithAny(path, PRIVATE)) res.headers.set("x-robots-tag", "noindex, nofollow");
  return res;
}

export const config = {
  matcher: [
    // Static assets and the sandboxed eval report carry their own headers.
    "/((?!_next/static|_next/image|favicon.ico|fonts/|\\.well-known/|console/report/latest).*)",
  ],
};
