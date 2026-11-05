---
name: pstack
description: >-
  Autonomous Pstack protocol stack dual-engine workflow for Antigravity, Claude Code, Codex, OpenCode, and Cursor.
  Enforces coordinator-only main thread, stateless subagent handoffs via pointer briefs,
  empirical decision.tsv logging, Comment Sicko code hygiene, and zero-slop prose verification.
---

# Pstack Universal Multi-Agent Skill

Activate this skill whenever the user invokes `/pstack`, mentions `pstack` or protocol stack workflow, or requests rigorous bug root-cause isolation, adversarial code review (`/interrogate`), X tech threads (`tech-thread`), or Build-in-Public engineering postmortems.

## 3-Tier Self-Discovery & Path Resolution

1. **Global Anchor (`PSTACK_HOME`)**: `~/.config/pstack/home` links to the canonical Pstack repository, and `~/.local/bin/pstack` (`pstack`, `pstack-verify`, `ag-spawn`) is mounted on `$PATH`.
2. **Local Skill Mounts (6/6 Agents)**:
   - **Antigravity (`agy`)**: `~/.gemini/config/skills/pstack`
   - **Claude Code (`claude`)**: `~/.claude/skills/pstack`
   - **Codex CLI (`codex`)**: `~/.codex/skills/pstack`
   - **OpenCode (`opencode`)**: `~/.config/opencode/skills/pstack`
   - **Cursor (`cursor`)**: `~/.cursor/skills-cursor/pstack`
   - **WorkBuddy AI (`workbuddy`)**: `~/.workbuddy-ai/skills/pstack`
3. **Overlay Asset Lookup (`scripts/pstack_resolver.py`)**:
   Dynamic state (`.agents/decision.tsv`, `.agents/handoffs/*`) lives in the current `WORKSPACE_ROOT`, while static playbooks, principles, and schemas transparently fall back to `PSTACK_HOME`. Run `pstack init` in any external repository to initialize a zero-copy light workspace.

## Mandatory Execution Loop

1. **Read Coordinator Core First**:
   Read `.agents/pstack/pstack-core.md` (or `~/.config/pstack/home/.agents/pstack/pstack-core.md` in a light workspace).
2. **Three-Line Alignment (In-Your-Own-Words)**:
   Start your very first response with three concise lines (`Target`, `Premise & Bottleneck`, `Smallest Leap`). Do not wait for confirmation. If existing empirical evidence contradicts the user's premise, cite `file:line` and stop immediately.
3. **Literal Playbook Mounting**:
   Select the matching playbook from `.agents/pstack/playbooks/` (or `~/.config/pstack/home/.agents/pstack/playbooks/`) and copy its exact steps as your checklist.
4. **Pointer-Only Fresh Subagent Handoff**:
   Write the task contract and `file:start-end` pointers to `.agents/handoffs/active-brief.md`. Dispatch a fresh subagent using your runtime's subagent tool (`invoke_subagent` / `Task`) or `pstack spawn <opencode|codex|claude|agy>`.
5. **Deterministic Verification Gate**:
   Run `pstack verify all` (or `python3 scripts/pstack-verify.py all`). Never deliver output unless the script prints `ALL CHECKS GREEN`.
