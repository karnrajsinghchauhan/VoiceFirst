#!/usr/bin/env bash
# Generates pydantic and TypeScript types from contracts/schemas.
# Usage: gen_contracts.sh <python_out_dir> <ts_out_dir>
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
py_out="$1"
ts_out="$2"
rm -rf "$py_out" "$ts_out"
(cd "$root/server" && uv run --quiet datamodel-codegen \
  --input "$root/contracts/schemas" --input-file-type jsonschema --output "$py_out" \
  --output-model-type pydantic_v2.BaseModel --use-annotated --field-constraints \
  --use-standard-collections --use-union-operator --target-python-version 3.12 \
  --enum-field-as-literal all --use-schema-description --disable-timestamp \
  --use-double-quotes --strict-nullable --collapse-root-models)
node "$root/tools/contracts-ts/gen.mjs" "$root/contracts/schemas" "$ts_out"
