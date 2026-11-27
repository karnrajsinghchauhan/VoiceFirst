// Self-hosted fonts (OFL, licences in src/fonts/). next/font emits font-display: swap and
// preloads the Latin files; Devanagari loads when Hindi text is on the page.
import localFont from "next/font/local";

export const inter = localFont({
  src: "../fonts/inter-latin-wght-normal.woff2",
  variable: "--font-inter",
  weight: "100 900",
  display: "swap",
});

export const fraunces = localFont({
  src: "../fonts/fraunces-latin-wght-normal.woff2",
  variable: "--font-fraunces",
  weight: "100 900",
  display: "swap",
});

export const mukta = localFont({
  src: [
    { path: "../fonts/mukta-devanagari-400-normal.woff2", weight: "400" },
    { path: "../fonts/mukta-devanagari-600-normal.woff2", weight: "600" },
  ],
  variable: "--font-mukta",
  display: "swap",
  preload: false,
});
