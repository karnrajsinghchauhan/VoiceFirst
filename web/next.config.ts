import createMDX from "@next/mdx";
import remarkGfm from "remark-gfm";
import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  pageExtensions: ["ts", "tsx", "mdx"],
  // The repo root holds other lockfiles (tools/, server/); pin tracing to this app.
  outputFileTracingRoot: __dirname,
  // `make check` runs eslint with our strict config; the build need not run it twice.
  eslint: { ignoreDuringBuilds: true },
};

const withMDX = createMDX({ options: { remarkPlugins: [remarkGfm] } });

export default withMDX(config);
