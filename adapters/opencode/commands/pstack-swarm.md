---
description: Run parallel Git Worktree DAG swarm or multi-agent arena (/pstack-swarm)
---

Execute Pstack v3.1 parallel Worktree DAG orchestration for `$ARGUMENTS`:
1. Run `pstack swarm "$ARGUMENTS"` (or `pstack arena --runners codex,opencode` for multi-agent competition).
2. Inspect wave execution, 3-way Git patch merges, and conflict status via `pstack tree`.
3. If interrupted, resume remaining DAG nodes with `pstack resume` and verify via `pstack verify all`.
