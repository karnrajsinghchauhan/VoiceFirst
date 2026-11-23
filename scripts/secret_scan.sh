#!/usr/bin/env bash
# Fails if a tracked file looks like it holds a credential. Patterns cover the providers we use.
set -euo pipefail
cd "$(dirname "$0")/.."
patterns='(sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|EAA[A-Za-z0-9]{40,}|xox[bp]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[0-9]{8,10}:[A-Za-z0-9_-]{35})'
if git ls-files -z | xargs -0 grep -IEn "$patterns" -- 2>/dev/null; then
  echo "secret scan: possible credential found" >&2
  exit 1
fi
echo "secret scan: clean"
