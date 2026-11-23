# S2: commit safety

Every commit runs `make check` through `.githooks/pre-commit` (installed with `make hooks`).

## Proof (scratch branch `scratch/s2-hook-proof`, 2026-11-23)
A file with an unused import and bad formatting (`server/app/lint_bait.py`) was staged and committed:

```
app/lint_bait.py:1:12: F401 [*] `sys` imported but unused
  |
1 | import os, sys
  |            ^^^ F401
2 | x=1
  |
  = help: Remove unused import

Found 4 errors.
[*] 4 fixable with the `--fix` option.
make: *** [Makefile:21: lint] Error 1
make: Leaving directory '/home/user/agoda-voice'
commit_exit=1
HEAD before=dbfeabde04dc95dcf78fa022500c5779286cdf24 after=dbfeabde04dc95dcf78fa022500c5779286cdf24
```

The commit exited 1 and HEAD did not move. The scratch branch was deleted afterwards.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01CCBpPgw3Y5S81RNo8Axnrb
