---
description: Activate Pstack Autonomous Coordinator workflow
---

Read `.agents/pstack/pstack-core.md` (or `~/.config/pstack/home/.agents/pstack/pstack-core.md`) immediately.

Execute the task `$ARGUMENTS` following the Pstack autonomous funnel loop:
1. Output 3-line alignment (`Target`, `Premise & Bottleneck`, `Smallest Leap`) in your own words without pleasantries.
2. Triage clarity (`L0_TRIVIAL` / `L1_CLEAR_DEEP` / `L2_FUZZY`, optionally via `pstack auto "$ARGUMENTS" --json`):
   - `L2_FUZZY`: auto-run `.agents/skills/reframe/SKILL.md` -> `.agents/skills/sharpen/SKILL.md` -> stage `.agents/handoffs/sharpened-prompt.md` and pause at a single Decision Gate.
   - `L1_CLEAR_DEEP`: auto-run `.agents/skills/sharpen/SKILL.md` -> stage `.agents/handoffs/sharpened-prompt.md` and pause at a single Decision Gate.
   - `L0_TRIVIAL` or once Decision Gate is approved: auto-run `pstack route --from-sharpen` (or `pstack route "$ARGUMENTS"` for L0), mount the matching playbook verbatim, and dispatch a fresh subagent via `pstack spawn` / `pstack run --from-sharpen --max-rework 2`.
3. Run `pstack verify all` (or `python3 scripts/pstack-verify.py all`) and require `ALL CHECKS GREEN` before final delivery.
