---
name: pstack
description: >-
  Lauren Tan (@poteto) Pstack dual-engine workflow for Antigravity, Claude Code, Codex, OpenCode, and Cursor.
  Enforces coordinator-only main thread, stateless subagent handoffs via pointer briefs,
  empirical decision.tsv logging, Comment Sicko code hygiene, and zero-slop prose verification.
---

# Pstack Universal Multi-Agent Skill

Activate this skill whenever the user invokes `/poteto-mode`, `/pstack`, mentions `pstack` / 土豆姐工作流, or requests rigorous bug root-cause isolation, adversarial code review (`/interrogate`), X tech threads (`tech-thread`), or Build-in-Public engineering postmortems.

## Path Resolution Across Local Agents

This skill is mounted across all 5 local agents:
- **Antigravity (`agy`)**: `~/.gemini/config/skills/pstack`
- **Claude Code (`claude`)**: `~/.claude/skills/pstack`
- **Codex CLI (`codex`)**: `~/.codex/skills/pstack`
- **OpenCode (`opencode`)**: `~/.config/opencode/skills/pstack`
- **Cursor (`cursor`)**: `~/.cursor/skills-cursor/pstack`

Inside this skill directory, `pstack/` links directly to `.agents/pstack/` and `scripts/` links directly to `scripts/`. If the current workspace does not yet have `.agents/pstack/`, read `pstack/poteto-core.md` and run `scripts/pstack-verify.py` directly from this skill directory, or run `<skill_dir>/scripts/bootstrap-repo.sh <target_repo> symlink` to inject the topology into the current workspace.

## Mandatory Execution Loop

1. **Read Coordinator Core First**:
   Read `.agents/pstack/poteto-core.md` (or `<skill_dir>/pstack/poteto-core.md` when running outside a bootstrapped repo).
2. **Three-Line Alignment (In-Your-Own-Words)**:
   Start your very first response with three concise lines (`Target`, `Premise & Bottleneck`, `Smallest Leap`). Do not wait for confirmation. If existing empirical evidence contradicts the user's premise, cite `file:line` and stop immediately.
3. **Literal Playbook Mounting**:
   Select the matching playbook from `.agents/pstack/playbooks/` (`tech-thread.md`, `build-in-public.md`, `bug-fix.md`, `architecture-feature.md`, `interrogate.md`, `figure-it-out.md`) and copy its exact steps as your checklist.
4. **Pointer-Only Fresh Subagent Handoff**:
   Write the task contract and `file:start-end` pointers to `.agents/handoffs/active-brief.md`. Dispatch a fresh subagent using your runtime's subagent tool (`invoke_subagent` / `Task`) or `./scripts/ag-spawn.sh .agents/handoffs/active-brief.md <opencode|codex|claude|agy>`.
5. **Deterministic Verification Gate**:
   Run `python3 scripts/pstack-verify.py all` (or `verify-prose.py` / `verify-code-slop.py` / `verify-handoff.py`). Never deliver output unless the script prints `ALL CHECKS GREEN`.
