---
description: Run Pstack Unslop and Comment Sicko verification gate on prose or code
---

Read `.agents/pstack/principles/unslop-zh-en.md` and `.agents/pstack/principles/no-comments.md`.

Verify and clean target `$ARGUMENTS`:
1. Run `python3 scripts/pstack-verify.py all` (or `python3 scripts/verify-prose.py $ARGUMENTS` / `python3 scripts/verify-code-slop.py $ARGUMENTS`).
2. Rewrite any sentence or comment that triggers a violation until the harness exits 0 with `ALL CHECKS GREEN`.
