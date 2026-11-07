---
name: pstack
description: >-
  Autonomous Pstack v2.0 protocol stack dual-engine workflow for Antigravity, Claude Code, Codex, OpenCode, Cursor, WorkBuddy, and Pi.
  Enforces Tier 0/1/2 context planning, desktop dual-tab Builder + Independent Verifier isolation, pointer-only briefs,
  empirical decision.tsv logging, Comment Sicko code hygiene, and 4-gate deterministic verification.
---

# Pstack v2.0 Universal Multi-Agent Skill

Activate this skill whenever the user invokes `/pstack`, `/pstack-build`, `/pstack-verify`, `/pstack-pickup`, mentions `pstack` or protocol stack workflow, or requests rigorous bug root-cause isolation, adversarial code review (`/interrogate`), X tech threads (`tech-thread`), or Build-in-Public engineering postmortems.

## 1. 3-Tier Self-Discovery & 8-Host Mounts

1. **Global Anchor (`PSTACK_HOME`)**: `~/.config/pstack/home` links to the canonical Pstack repository, and `~/.local/bin/{pstack,pstack-verify,ag-spawn}` is mounted on `$PATH`.
2. **Local Skill Mounts (8/8 Hosts)**:
   - **Antigravity (`agy`)**: `~/.gemini/config/skills/pstack`
   - **Claude Code (`claude`)**: `~/.claude/skills/pstack`
   - **Codex CLI (`codex`)**: `~/.codex/skills/pstack`
   - **OpenCode (`opencode`)**: `~/.config/opencode/skills/pstack` + `~/.config/opencode/command/*.md`
   - **Cursor (`cursor`)**: `~/.cursor/skills-cursor/pstack`
   - **WorkBuddy AI (`workbuddy`)**: `~/.workbuddy-ai/skills/pstack`
   - **Pi (`pi`)**: `~/.pi/agent/skills/pstack`
   - **Universal Agent Pool**: `~/.agents/skills/pstack`
3. **Overlay Asset Lookup (`scripts/pstack_resolver.py`)**:
   Dynamic state (`.agents/decision.tsv`, `.agents/handoffs/*`) lives in `WORKSPACE_ROOT`, while static playbooks, principles, and schemas transparently fall back to `PSTACK_HOME`. Run `pstack init` (`--light` or `--full`) in any external repository.

## 2. Desktop Dual-Tab Loop & Slash Triggers

1. **Read Coordinator Core First**:
   Read `.agents/pstack/pstack-core.md` (strictly `<= 48 lines`, or `~/.config/pstack/home/.agents/pstack/pstack-core.md`).
2. **Tab 1 — Builder (`/pstack-build`)**:
   - Output 3-line alignment (`Target`, `Premise & Bottleneck`, `Smallest Leap`) in your own words.
   - Copy the selected playbook from `.agents/pstack/playbooks/` verbatim as your checklist.
   - Write `> [Builder Restate]` (<= 3 lines) at the top of `.agents/handoffs/output-draft.md`.
   - Run `pstack verify all` (Gate 1 Handoff + Gate 2 Prose + Gate 3 Code Slop + Gate 4 Runtime `verify_cmd` digest into `evidence-pack.md`).
3. **Tab 2 — Independent Verifier (`/pstack-verify` in a fresh Tab or subagent)**:
   - Run `pstack verify prep-verifier` to inspect the <= 20 line read-only digest (`active-brief.md`, `[Builder Restate]`, `Runtime Verification Digest`, and `git diff --stat`).
   - Write a 4-tier adversarial verdict (`ACT_ON`, `CONSIDER`, `NOTED`, `DISMISSED` + `VERDICT: PASS | REJECT`) to `.agents/handoffs/verifier-verdict.md`.
   - Run `pstack verify verdict` to validate the verdict and automatically export `.agents/handoffs/output-final.md` (with `> [Builder Restate]` stripped).
4. **Zero-Token Offline Tooling (`/pstack-pickup`, `correct`, `onboard`, `update`)**:
   - `pstack pause "<note>"` / `pstack pickup`: Generate and read `.agents/handoffs/session-snapshot.md` (<= 20 lines) for instant cross-session recovery.
   - `pstack correct --scan | --code-rule "<regex>" "<reason>" | --prose-ban "<phrase>"`: Promote lessons from `.agents/decision.tsv` into mechanical regex/prose rules.
   - `pstack onboard --detect | --to-thread`: Auto-detect project `verify_cmd` or synthesize `active-brief.md` from recent Git commits and `decision.tsv`.
   - `pstack update [--check|--apply]` / `/pstack-update`: Check remote commit updates and fast-forward all 8 local agent mounts.
