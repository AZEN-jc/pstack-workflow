---
description: Run adversarial multi-model code and architecture interrogation (/interrogate)
---

Read `.agents/pstack/pstack-core.md` and `.agents/pstack/playbooks/interrogate.md` (or from `~/.config/pstack/home/.agents/pstack/`).

Interrogate target `$ARGUMENTS` for hidden invariants, race conditions, blast radius, and swallowed errors:
1. Output 3-line alignment (`Target`, `Premise & Bottleneck`, `Smallest Leap`).
2. Cite exact `file:line` pointers for every flaw discovered.
3. Run `pstack verify code $ARGUMENTS` and record findings via `pstack log add`.
