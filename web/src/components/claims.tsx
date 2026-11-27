// Every number on a public page is wrapped in one of these (enforced by tests/claims.test.ts):
//   <Src id="S-23">  a dated external fact in docs/sources.md
//   <Measured id>    a dated measured result in content/measured.json (test data, with method)
//   <Spec of>        a fact about our own product's configuration or offer
//   <Est>            an estimate, labelled as such
// Content strings use the same four through the markup [[S-23|text]], [[m:id|text]],
// [[spec:ref|text]] and [[est|text]], rendered by <Rich>.
import Link from "next/link";
import type { ReactNode } from "react";
import sources from "@/content/generated/sources.json";
import measured from "@/content/measured.json";

export interface SourceRow {
  id: string;
  fact: string;
  source: string;
  links: { label: string; url: string }[];
  date: string;
}

export interface MeasuredItem {
  id: string;
  value: string;
  label: string;
  date: string;
  method: string;
  result: string;
}

export const SOURCES: readonly SourceRow[] = sources.rows;
export const MEASURED: readonly MeasuredItem[] = measured.items;
export const MEASURED_NOTE: string = measured.note;

export function source(id: string): SourceRow {
  const row = SOURCES.find((s) => s.id === id);
  if (!row) throw new Error(`unknown source ${id}: add it to docs/sources.md`);
  return row;
}

export function measuredItem(id: string): MeasuredItem {
  const item = MEASURED.find((m) => m.id === id);
  if (!item) throw new Error(`unknown measured result ${id}: add it to content/measured.json`);
  return item;
}

export function Src({ id, children }: { id: string; children: ReactNode }) {
  const row = source(id);
  return (
    <span className="whitespace-nowrap">
      {children}
      <Link
        href={`/docs/sources#${id}`}
        className="ml-0.5 align-super text-[0.65em] text-accent no-underline hover:underline"
        title={`${row.source}, ${row.date}`}
        aria-label={`Source ${id}: ${row.source}, ${row.date}`}
      >
        {id}
      </Link>
    </span>
  );
}

export function Measured({ id, children }: { id: string; children?: ReactNode }) {
  const item = measuredItem(id);
  return (
    <span className="whitespace-nowrap">
      {children ?? item.value}
      <Link
        href={`/product#proof-${id}`}
        className="ml-0.5 align-super text-[0.65em] text-accent no-underline hover:underline"
        title={`Measured on test data, ${item.date}: ${item.method}`}
        aria-label={`Measured on test data, ${item.date}`}
      >
        measured
      </Link>
    </span>
  );
}

export function Spec({ of: specRef, children }: { of: string; children: ReactNode }) {
  return (
    <span title={`Product specification: ${specRef}`} data-spec={specRef}>
      {children}
    </span>
  );
}

export function Est({ children }: { children: ReactNode }) {
  return (
    <span>
      {children} <span className="text-muted">(estimate)</span>
    </span>
  );
}

const MARK = /\[\[([^|\]]+)\|([^\]]+)\]\]/g;

export function Rich({ text }: { text: string }) {
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(MARK)) {
    const [whole, tag = "", body = ""] = m;
    const at = m.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    if (tag.startsWith("S-")) out.push(<Src key={key++} id={tag}>{body}</Src>);
    else if (tag.startsWith("m:")) out.push(<Measured key={key++} id={tag.slice(2)}>{body}</Measured>);
    else if (tag.startsWith("spec:")) out.push(<Spec key={key++} of={tag.slice(5)}>{body}</Spec>);
    else if (tag === "est") out.push(<Est key={key++}>{body}</Est>);
    else throw new Error(`unknown claim tag ${tag}`);
    last = at + whole.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return <>{out}</>;
}
