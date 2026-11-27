import createMDX from "@next/mdx";
import remarkGfm from "remark-gfm";
import type { NextConfig } from "next";

// Static security headers. The CSP is per request (nonce) and set in src/middleware.ts.
const SECURITY_HEADERS = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  pageExtensions: ["ts", "tsx", "mdx"],
  // The repo root holds other lockfiles (tools/, server/); pin tracing to this app.
  outputFileTracingRoot: __dirname,
  // `make check` runs eslint with our strict config; the build need not run it twice.
  eslint: { ignoreDuringBuilds: true },
  async headers() {
    return [
      // Two rules must not both match a path: duplicate X-Frame-Options values are invalid.
      { source: "/:path((?!console/report/latest).*)", headers: [...SECURITY_HEADERS, { key: "X-Frame-Options", value: "DENY" }] },
      // The eval report is framed by the console on the same origin, sandboxed.
      { source: "/console/report/latest", headers: [...SECURITY_HEADERS, { key: "X-Frame-Options", value: "SAMEORIGIN" }] },
    ];
  },
};

const withMDX = createMDX({ options: { remarkPlugins: [remarkGfm] } });

export default withMDX(config);
