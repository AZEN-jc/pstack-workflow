---
description: Activate Lauren Tan (@poteto) Pstack Coordinator workflow
---

Read `.agents/pstack/poteto-core.md` (or `~/.config/opencode/skills/pstack/pstack/poteto-core.md`) immediately.

Execute the task `$ARGUMENTS` following the Pstack mandatory loop:
1. Output 3-line alignment (`Target`, `Premise & Bottleneck`, `Smallest Leap`) in your own words without pleasantries.
2. Mount the matching playbook from `.agents/pstack/playbooks/` into your checklist verbatim.
3. Write pointer-only handoff brief to `.agents/handoffs/active-brief.md` and spawn a fresh subagent or run `./scripts/ag-spawn.sh`.
4. Run `python3 scripts/pstack-verify.py all` and require `ALL CHECKS GREEN` before final delivery.
