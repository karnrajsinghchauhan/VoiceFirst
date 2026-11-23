#!/usr/bin/env bash
# Fails if the committed generated types differ from what the schemas produce.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"$root/scripts/gen_contracts.sh" "$tmp/py" "$tmp/ts" 2>/dev/null
diff -r -x __pycache__ "$tmp/py" "$root/server/app/contracts/generated" >/dev/null || { echo "contract drift: python types out of date; run make gen" >&2; exit 1; }
diff -r "$tmp/ts" "$root/web/src/contracts" >/dev/null || { echo "contract drift: TypeScript types out of date; run make gen" >&2; exit 1; }
(cd "$root/server" && uv run --quiet python "$root/scripts/export_openapi.py" "$tmp/openapi.yaml")
diff "$tmp/openapi.yaml" "$root/contracts/openapi.yaml" >/dev/null || { echo "contract drift: contracts/openapi.yaml out of date; run make gen" >&2; exit 1; }
echo "contracts: no drift"
