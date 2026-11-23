#!/usr/bin/env bash
# Claude Code PreToolUse hook: blocks `git commit` unless `make check` passes (rule 6.10).
set -euo pipefail
cmd="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')"
case "$cmd" in
  *"git commit"*)
    root="$(git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse --show-toplevel)"
    if ! make -C "$root" check >/tmp/av-make-check.log 2>&1; then
      echo "make check failed; commit blocked. Tail of log:" >&2
      tail -40 /tmp/av-make-check.log >&2
      exit 2
    fi
    ;;
esac
exit 0
