// Generates TypeScript types from contracts/schemas. Output dir is argv[2].
import { compileFromFile } from "json-schema-to-typescript";
import { readdirSync, writeFileSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";

const schemaDir = resolve(process.argv[2]);
const outDir = resolve(process.argv[3]);
mkdirSync(outDir, { recursive: true });
const files = readdirSync(schemaDir).filter((f) => f.endsWith(".json")).sort();
const banner = "/* Generated from contracts/schemas. Do not edit; run `make gen`. */";
for (const f of files) {
  const ts = await compileFromFile(join(schemaDir, f), {
    cwd: schemaDir,
    bannerComment: banner,
    additionalProperties: false,
    declareExternallyReferenced: true,
    style: { singleQuote: false, semi: true },
  });
  const name = f.replace(/\.json$/, "");
  writeFileSync(join(outDir, `${name}.ts`), ts);
}
