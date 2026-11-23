// Mock of POST /concierge/ask: lexical retrieval over the same pages the engine's concierge
// indexes (docs, trust centre, pricing; content/generated/search-index.json). It answers only
// from a retrieved passage, always cites it, and says so when nothing matches well enough.
import index from "@/content/generated/search-index.json";

export interface ConciergeAnswer {
  answer: string;
  citations: { title: string; url: string }[];
  confidence: "high" | "low";
  actions: { type: "book_meeting" }[];
}

interface Entry {
  url: string;
  title: string;
  heading: string;
  text: string;
}

const STOP = new Set(
  "a an and are as at be by can do does for from has have how i if in is it its me my of on or our so that the their this to us we what when where which who why will with you your about there they them".split(" "),
);

function tokens(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9ऀ-ॿ\s-]/g, " ")
    .split(/\s+/)
    .filter((t) => t.length > 2 && !STOP.has(t));
}

const ENTRIES: readonly (Entry & { terms: Map<string, number>; length: number })[] = (index.entries as Entry[]).map((e) => {
  const terms = new Map<string, number>();
  const all = tokens(`${e.title} ${e.heading} ${e.heading} ${e.text}`);
  for (const t of all) terms.set(t, (terms.get(t) ?? 0) + 1);
  return { ...e, terms, length: all.length };
});

const DF = new Map<string, number>();
for (const e of ENTRIES) for (const t of e.terms.keys()) DF.set(t, (DF.get(t) ?? 0) + 1);
const AVG_LEN = ENTRIES.reduce((s, e) => s + e.length, 0) / Math.max(ENTRIES.length, 1);

// BM25 over sections. Score alone cannot tell an off-topic question that shares one common
// word from a real one, so an answer also needs coverage: the matched terms must carry most
// of the question's information (idf-weighted). Words the pages never use count fully against.
const K1 = 1.2;
const B = 0.75;
const MIN_SCORE = 2;
const MIN_COVERAGE = 0.6;

function idf(term: string): number {
  const df = DF.get(term) ?? 0;
  return Math.log(1 + (ENTRIES.length - df + 0.5) / (df + 0.5));
}

function score(query: string[], e: (typeof ENTRIES)[number]): number {
  let s = 0;
  for (const q of new Set(query)) {
    const tf = e.terms.get(q) ?? 0;
    if (!tf) continue;
    s += (idf(q) * tf * (K1 + 1)) / (tf + K1 * (1 - B + (B * e.length) / AVG_LEN));
  }
  return s;
}

function coverage(query: string[], e: (typeof ENTRIES)[number]): number {
  const terms = [...new Set(query)];
  const total = terms.reduce((s, t) => s + idf(t), 0);
  const hit = terms.filter((t) => e.terms.has(t)).reduce((s, t) => s + idf(t), 0);
  return total === 0 ? 0 : hit / total;
}

function firstSentences(text: string, max: number): string {
  const parts = text.match(/[^.!?]+[.!?]+/g) ?? [text];
  let out = "";
  for (const p of parts) {
    if ((out + p).length > max && out) break;
    out += p;
  }
  return out.trim();
}

export function askMock(message: string): ConciergeAnswer {
  const q = tokens(message);
  const ranked = ENTRIES.map((e) => ({ e, s: score(q, e) }))
    .filter((r) => r.s > 0)
    .sort((a, b) => b.s - a.s);
  const best = ranked[0];
  if (!best || best.s < MIN_SCORE || coverage(q, best.e) < MIN_COVERAGE) {
    return {
      answer:
        "I am not sure, and I would rather not guess. I can only answer from the product pages. Would you like to book a call with the founder?",
      citations: [],
      confidence: "low",
      actions: [{ type: "book_meeting" }],
    };
  }
  const cites = [best, ...ranked.slice(1).filter((r) => r.e.url !== best.e.url && r.s >= best.s * 0.8)].slice(0, 2);
  return {
    answer: firstSentences(best.e.text, 420),
    citations: cites.map((r) => ({ title: r.e.heading === r.e.title ? r.e.title : `${r.e.title}: ${r.e.heading}`, url: r.e.url })),
    confidence: "high",
    actions: [],
  };
}
