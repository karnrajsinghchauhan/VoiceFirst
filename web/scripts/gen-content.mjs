// Generates the site's derived content from the repo's single sources of truth:
//   docs/sources.md            -> src/content/generated/sources.json
//   contracts/openapi.yaml     -> src/content/generated/api-reference.json
//   src/app/docs/**/page.mdx,
//   src/content/{trust,pricing}.json -> src/content/generated/search-index.json (concierge retrieval)
// `--check` fails if the committed output is stale, so `npm run lint` catches drift.
import { readFileSync, writeFileSync, mkdirSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, dirname, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const repo = join(web, "..");
const out = join(web, "src/content/generated");
const check = process.argv.includes("--check");

function sources() {
  const md = readFileSync(join(repo, "docs/sources.md"), "utf8");
  const rows = [];
  for (const line of md.split("\n")) {
    const m = line.match(/^\|\s*(S-\d{2})\s*\|(.*)\|(.*)\|(.*)\|\s*$/);
    if (!m) continue;
    rows.push({ id: m[1], fact: m[2].trim(), source: m[3].trim(), date: m[4].trim() });
  }
  if (rows.length === 0) throw new Error("no rows parsed from docs/sources.md");
  const note = md.split("\n").filter((l) => l && !l.startsWith("|") && !l.startsWith("#")).join(" ").trim();
  return { note, rows };
}

function apiReference() {
  const spec = yaml.load(readFileSync(join(repo, "contracts/openapi.yaml"), "utf8"));
  const ops = [];
  for (const [path, item] of Object.entries(spec.paths ?? {})) {
    for (const [method, op] of Object.entries(item)) {
      if (!["get", "post", "put", "patch", "delete"].includes(method)) continue;
      const body = op.requestBody?.content?.["application/json"]?.schema?.$ref;
      const ok = op.responses?.["200"]?.content?.["application/json"]?.schema;
      ops.push({
        method: method.toUpperCase(),
        path,
        summary: op.summary ?? "",
        tag: (op.tags ?? ["other"])[0],
        auth: Boolean(op.security) || path !== "/healthz",
        request: body ? body.split("/").pop() : null,
        response: ok?.$ref ? ok.$ref.split("/").pop() : ok?.type === "array" && ok.items?.$ref ? `${ok.items.$ref.split("/").pop()}[]` : null,
      });
    }
  }
  ops.sort((a, b) => a.tag.localeCompare(b.tag) || a.path.localeCompare(b.path) || a.method.localeCompare(b.method));
  return { title: spec.info?.title ?? "", version: spec.info?.version ?? "", operations: ops };
}

function walk(dir) {
  const files = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) files.push(...walk(p));
    else if (name === "page.mdx") files.push(p);
  }
  return files;
}

function plain(mdx) {
  return mdx
    .replace(/^import .*$/gm, "")
    .replace(/^export .*$/gm, "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[#*_`|>]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function searchIndex() {
  const docsRoot = join(web, "src/app/docs");
  const entries = [];
  for (const file of walk(docsRoot).sort()) {
    const rel = relative(docsRoot, dirname(file)).split(sep).join("/");
    const url = rel ? `/docs/${rel}` : "/docs";
    const mdx = readFileSync(file, "utf8");
    const title = (mdx.match(/^#\s+(.+)$/m) ?? [null, url])[1].trim();
    // Split on H2 so a citation points at the section that answers the question.
    const parts = mdx.split(/^##\s+/m);
    parts.forEach((part, i) => {
      const heading = i === 0 ? title : part.split("\n")[0].trim();
      const text = plain(i === 0 ? part : part.split("\n").slice(1).join("\n"));
      if (text.length > 40) entries.push({ url, title, heading, text });
    });
  }
  for (const [name, url] of [["trust", "/security"], ["pricing", "/pricing"]]) {
    const data = JSON.parse(readFileSync(join(web, `src/content/${name}.json`), "utf8"));
    for (const s of data.sections) {
      entries.push({ url: `${url}#${s.id}`, title: data.title, heading: s.heading, text: [s.body, ...(s.points ?? [])].join(" ") });
    }
  }
  return { entries };
}

const files = {
  "sources.json": sources(),
  "api-reference.json": apiReference(),
  "search-index.json": searchIndex(),
};

mkdirSync(out, { recursive: true });
let stale = [];
for (const [name, data] of Object.entries(files)) {
  const text = JSON.stringify(data, null, 1) + "\n";
  const path = join(out, name);
  if (check) {
    if (!existsSync(path) || readFileSync(path, "utf8") !== text) stale.push(name);
  } else {
    writeFileSync(path, text);
  }
}
if (stale.length) {
  console.error(`generated content is stale: ${stale.join(", ")}; run npm run gen:content`);
  process.exit(1);
}
console.log(check ? "generated content: up to date" : "generated content: written");
