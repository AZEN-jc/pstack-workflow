---
description: Run adversarial multi-model code and architecture interrogation (/interrogate)
---

Read `.agents/pstack/poteto-core.md` and `.agents/pstack/playbooks/interrogate.md` (or from `~/.config/opencode/skills/pstack/pstack/`).

Interrogate target `$ARGUMENTS` for hidden invariants, race conditions, blast radius, and swallowed errors:
1. Output 3-line alignment (`Target`, `Premise & Bottleneck`, `Smallest Leap`).
2. Cite exact `file:line` pointers for every flaw discovered.
3. Run `python3 scripts/verify-code-slop.py` on target code files and record findings via `python3 scripts/log-decision.py`.
