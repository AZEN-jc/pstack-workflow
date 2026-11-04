---
description: Run Pstack Unslop and Comment Sicko verification gate on prose or code
---

Read `.agents/pstack/principles/unslop-zh-en.md` and `.agents/pstack/principles/no-comments.md` (or from `~/.config/pstack/home/.agents/pstack/principles/`).

Verify and clean target `$ARGUMENTS`:
1. Run `pstack verify all` (or `pstack verify prose $ARGUMENTS` / `pstack verify code $ARGUMENTS`).
2. Rewrite any sentence or comment that triggers a violation until the harness exits 0 with `ALL CHECKS GREEN`.
