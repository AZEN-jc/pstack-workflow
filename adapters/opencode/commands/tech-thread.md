---
description: Draft a zero-slop hardcore X tech thread or architecture critique using Pstack
---

Read `.agents/pstack/pstack-core.md` and `.agents/pstack/playbooks/tech-thread.md` (or from `~/.config/pstack/home/.agents/pstack/`).

Draft an 8-12 post technical thread or deep postmortem for `$ARGUMENTS`:
1. Output 3-line alignment (`Target`, `Premise & Bottleneck`, `Smallest Leap`).
2. Follow `.agents/pstack/principles/unslop-zh-en.md`: zero em-dashes (`—`/`——`/` -- `), zero mid-sentence colons, <= 45 Chinese chars or <= 28 English words per sentence, and mandatory `[实测 Measured]` / `[推导 Inferred]` epistemic tags.
3. Save draft to `.agents/handoffs/output-draft.md` and run `pstack verify prose .agents/handoffs/output-draft.md` until `ALL CHECKS GREEN`.
