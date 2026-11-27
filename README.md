# Pstack: Deterministic Worktree Swarm & 4-Gate Verification Engine for Coding Agents

<p align="center"><b>English</b> | <b><a href="./README_ZH.md">简体中文</a></b></p>

<p align="center">
  <a href="https://github.com/AZEN-jc/pstack-workflow/actions/workflows/pstack-ci.yml"><img src="https://github.com/AZEN-jc/pstack-workflow/actions/workflows/pstack-ci.yml/badge.svg" alt="Pstack CI" /></a>
  <img src="https://img.shields.io/badge/Engine-v3.1_Worktree_Swarm_%26_Arena-2563EB?style=flat-square" alt="Architecture" />
  <img src="https://img.shields.io/badge/Router-Bilingual_Repo--Map_(7_Langs)-7C3AED?style=flat-square" alt="Router" />
  <img src="https://img.shields.io/badge/Verification-4_Gates_%2B_Auto--Rework-10B981?style=flat-square" alt="Verification" />
</p>

<p align="center">
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Ecosystem-8_Hosts_%2B_Stdio_MCP_Server-06B6D4?style=flat-square" alt="Ecosystem" /></a>
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Isolation-3--Way_Git_Merge_%2B_Scope_Lock-F97316?style=flat-square" alt="Isolation" /></a>
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Tests-25_Unit_Tests_%2B_ABCD_Bench-E11D48?style=flat-square" alt="Benchmark" /></a>
</p>

> Client-agnostic task router, parallel Git worktree scheduler, and 4-gate verification engine for coding agents [Offline-Measured].
> Left unconstrained, coding agents hallucinate imports and overwrite concurrent work across shared branches.
> They paste unvetted diffs across broken paths before exhausting context windows.
> Pstack v3.1 replaces conversational trust with bilingual Repo-Map routing, isolated worktree execution, bounded auto-rework loops, and physical pre-commit gates.
> Static playbooks and volatile projects stay physically decoupled across 8 local hosts and native MCP clients.

---

## 1. ELI5: What is Pstack v3.1?

> **TL;DR for Humans**  
> Conventional multi-agent setups act like newcomers chatting in a shared folder. They paste hundreds of code lines, collide on files, and declare broken builds tested.  
> Pstack v3.1 turns agent workflows into an execution and verification engine. Give a one-line goal and the router extracts ranked AST pointers across 7 languages. Workers run in parallel Git worktrees under strict path locks, auto-rework gate failures, and merge via 3-way Git patches.

AI coding failures stem from poor discipline, not weak models.
Initial handoff payload compresses by 93.5% [Offline-Measured].
Multi-turn session token delta depends on conversation depth [Sim-Verified].

| Failure Mode | Conventional Agent Setup | Pstack v3.1 Deterministic Engine | Measured Payoff [Offline-Measured] |
| :--- | :--- | :--- | :--- |
| **Manual Prompt & File Hunting** | Users memorize commands and manually hunt file paths for prompts. | **Bilingual Repo-Map Router (`pstack route/run`)**. Extracts CJK/English terms and ranks symbols across `.py/.ts/.js/.go/.rs/.sh` + `models.json` role routing. | 0-token routing in <50ms |
| **Parallel File Collisions** | Multiple agents edit the same directory and overwrite each other. | **True Parallel Worktree Swarm & Arena (`pstack swarm/arena`)**. Concurrent wave execution in isolated Git worktrees, `allowed_paths` lock, and `git apply --3way` merge. | Zero cross-agent file corruption |
| **Single-Shot Gate Failure** | Agent fails a lint or test check and stops for human cleanup. | **Bounded Auto-Rework Loop (`--max-rework 2`) & Crash Quarantine**. Injects gate failure digest into brief and spawns a fresh stateless retry; isolates crash diffs as `.patch`. | Autonomous self-healing retries |
| **Conversational & Code Bloat** | Excessive filler and massive diffs with drifted line ranges. | **Tier 0 Core (≤48 lines) + AST Symbol Auto-Heal (`file:start-end#symbol`)**. Auto-relocates drifted line ranges via `--fix` and caps inline blocks at 15 lines. | Handoff payload cut by 93.5% |
| **Conflicted Self-Review** | Agents declare their own code tested without running real checks. | **Gate 4 Composite Toolchain + Blind Verifier (`--blind`)**. Runs `Test + Lint + Typecheck`, records SHA256, and strips Builder narrative for Tab 2 blind review. | 12/12 adversarial mutations caught |
| **Bypassed Verification** | Agents commit directly to Git without running verification commands. | **Physical Pre-Commit Hook (`pstack hook`) & Native MCP Server (`pstack mcp`)**. Enforces scope and code gates at `git commit` time; exposes 5 JSON-RPC 2.0 Stdio MCP tools. | 100% commit-time gate enforcement |

---

## 2. Core Architecture: Repo-Map Router, Parallel Worktrees & 4-Gate Auto-Rework

Running pstack needs no manual playbook copying. Decoupled templates ensure zero-break execution [Offline-Measured].

```text
                 User Goal: pstack run "修复状态机超时恢复异常" --max-rework 2
                                            |
                                            v
           +-----------------------------------------------------------------+
           | 1. Bilingual Repo-Map Router (pstack_router.py + models.json)   |
           |    - Intent & Complexity -> fast_tier (Flash) / deep_tier (Pro) |
           |    - Multi-lang AST/Regex symbol ranking (.py/.ts/.go/.rs/.sh)  |
           +-----------------------------------------------------------------+
                                            |
                                            v
           +-----------------------------------------------------------------+
           | 2. Parallel Worktree Scheduler (pstack_scheduler.py)            |
           |    - Swarm Wave ThreadPool / Arena Competing Candidates         |
           |    - Ephemeral Git Worktrees (.agents/worktrees/<node_id>)      |
           |    - allowed_paths Scope Lock + Dirty-Tree Crash Patch Rollback |
           +-----------------------------------------------------------------+
                                            |
                         +------------------+------------------+
                         |   4 Deterministic Gates (Gate 1-4)  |
                         |   Pass? ----No (r <= max_rework)----+--> Inject Failure Digest
                         +------------------+------------------+    & Spawn Fresh Retry
                                            | Yes
                                            v
           +-----------------------------------------------------------------+
           | 3. git apply --3way Merge + Blind Verifier (--blind) + Verdict  |
           |    - Pre-Commit Hook (.git/hooks/pre-commit) & Stdio MCP Server |
           |    - DAG Checkpoints (dag-state.json) & ASCII Tree (pstack tree)|
           +-----------------------------------------------------------------+
```

- **Tier 0 Resident Routing (`pstack-core.md` ≤ 48 lines)**: Minimal 3-line entry mandates every agent to read `.agents/pstack/pstack-core.md` first [Offline-Measured].
- **Bilingual Repo-Map & 5-Role Model Matrix (`models.json`)**: Maps `coordinator`, `architect`, `builder`, `reviewer`, and `verifier` across vendor-agnostic `fast_tier` and `deep_tier` models [Offline-Measured].
- **Parallel Worktree Pool & 3-Way Git Merge**: Executes independent DAG waves concurrently, enforces `allowed_paths` boundaries, and merges non-overlapping edits and file deletions via `git apply --3way` [Sim-Verified].
- **Bounded Auto-Rework & Blind Dual-Tab Verification**: Automatically retries failed gates up to `--max-rework` times with fresh subagents, then generates a ≤25-line `--blind` review pack for independent Tab 2 verdict [Sim-Verified].
- **Physical Pre-Commit Hook & Zero-Dependency MCP Server**: Locks verification into `.git/hooks/pre-commit` and exposes `pstack_route`, `pstack_verify`, `pstack_swarm`, `pstack_arena`, and `pstack_tree` over JSON-RPC 2.0 Stdio [Offline-Measured].

---

## 3. 8-Host Matrix, Global CLI & Native MCP Mounts

One bootstrap run mounts pstack across 8 hosts. Global CLI executables activate simultaneously in ~/.local/bin [Offline-Measured].

| Target Host | Global Mount Path | Project Auto Entry | Core Role |
| :--- | :--- | :--- | :--- |
| **Global Anchor (`PSTACK_HOME`)** | `~/.config/pstack/home` | Fallback root for `pstack_resolver.py` | Static playbook templates |
| **Global CLI (`$PATH`)** | `~/.local/bin/pstack*` (13 CLIs) | Run `pstack` directly anywhere | Unified command-line interface |
| **Native MCP Server (`stdio`)** | `~/.local/bin/pstack-mcp` (`pstack mcp`) | JSON-RPC 2.0 Stdio (5 MCP tools) | Native tool calling for MCP hosts |
| **Git Pre-Commit Hook** | `.git/hooks/pre-commit` (`pstack hook install`) | Automatic commit-time gate check | Physical anti-bypass enforcement |
| **Antigravity (`agy`)** | `~/.gemini/config/skills/pstack` | `AGENTS.md` + `SKILL.md` | Native subagent orchestration |
| **Claude Code (`claude`)** | `~/.claude/skills/pstack` | `CLAUDE.md` | Automated terminal workflow |
| **Codex CLI & App (`codex`)** | `~/.codex/skills/pstack` | `AGENTS.md` | Worktree drills and blind verification |
| **OpenCode (`opencode`)** | `~/.config/opencode/skills/pstack` + `command/*.md` | `AGENTS.md` + 9 slash commands | Slash command workspace |
| **Cursor IDE (`cursor`)** | `~/.cursor/skills-cursor/pstack` | `.cursor/rules/pstack.mdc` + `AGENTS.md` | In-editor rule enforcement |
| **WorkBuddy AI (`workbuddy`)** | `~/.workbuddy-ai/skills/pstack` | `AGENTS.md` + `SKILL.md` | Desktop dual-tab workspace host |
| **Pi Agent (`pi`)** | `~/.pi/agent/skills/pstack` | `AGENTS.md` + `SKILL.md` | Minimal desktop and terminal host |
| **Universal Agent Pool** | `~/.agents/skills/pstack` | Cross-host universal skill pool | Standardized mount point |

---

## 4. Quick Start: 30-Second Bootstrap & Lightweight Init

Execute the following commands in terminal for global setup:

```bash
# 1. Mount 8 agent skills, OpenCode slash commands, and ~/.local/bin/pstack
./scripts/bootstrap-repo.sh --global

# 2. Inspect status across all 8 hosts and global CLI
pstack status

# 3. Initialize lightweight workspace in any external repository (--light | --full | --symlink)
cd /path/to/your/repo && pstack init --light

# 4. Auto-detect project verify command, or generate tech-thread brief from last 3 commits
pstack onboard --detect
pstack onboard --to-thread --commits 3 --playbook tech-thread
```

---

## 5. Unified CLI, 4-Gate Verification & Zero-Token Toolchain

All deliverables must pass 4 harness gates. Verdicts require review via pstack verify verdict [Sim-Verified].

```bash
# Run all 4 deterministic gates (Gate 1 Handoff + Gate 2 Prose + Gate 3 Code Slop + Gate 4 Runtime cmd)
pstack verify all

# Generate a ≤25-line blind review pack for fresh Independent Verifier tab
pstack verify prep-verifier --blind

# Validate .agents/handoffs/verifier-verdict.md and export clean output-final.md
pstack verify verdict

# 5-tier correction: scan decision.tsv for repeated rollbacks, inject code regex or prose bans
pstack correct --scan
pstack correct --code-rule "^\s*print\([\"']DEBUG" "Prohibit lingering debug prints"
pstack correct --prose-ban "cognitive load"

# Cross-session resumption: generate and read strictly ≤20-line session-snapshot.md
pstack pause "Completed core module refactor and 4-gate verification"
pstack pickup

# Automated remote update check and self-update
pstack update --check
pstack update

# Run unit tests, 0-token benchmark, and MCP self-test
pstack test
pstack bench
pstack mcp --self-test
pstack verify handoff --fix

# Bilingual Repo-Map routing, pre-flight /reframe -> /sharpen staging, bounded auto-rework, parallel Swarm, and Git pre-commit hook
pstack route "修复状态机超时恢复异常" --json
pstack route --from-sharpen
pstack run --from-sharpen --max-rework 2
pstack run "修复路由 Bug" --runner codex --max-rework 2
pstack swarm --dry-run && pstack arena --dry-run && pstack tree
pstack hook install && pstack hook status
```

See [benchmarks/latest-report.md](./benchmarks/latest-report.md) for full benchmark metrics [Offline-Measured].

### Terminal 4-Gate Output Sample

```text
====================================================================
PSTACK v3.1 FOUR-GATE VERIFICATION SUITE
====================================================================
[1/4] Handoff Brief Check   : .agents/handoffs/active-brief.md -> PASS (Schema V3 + Symbol Auto-Heal)
[2/4] Prose & Restate Check : .agents/handoffs/output-draft.md -> PASS (Builder Restate + 0 slop)
[3/4] Comment Sicko & Rules : scripts/ (1 custom rule)         -> PASS (0 violations)
[4/4] Runtime verify_cmd    : exit=0, sha256=1aefa2e6acf7      -> PASS (evidence-pack.md updated)
====================================================================
STATUS : ALL 4 HARNESS GATES GREEN (Return Code: 0)
====================================================================
```

---

## 6. Repository Topology

See [UPGRADE_V2.md](./UPGRADE_V2.md) for full v3.0 and v3.1 kernel hardening specifications.

```text
.
├── AGENTS.md                        # Antigravity / Codex / OpenCode / Cursor / Pi entry
├── CLAUDE.md                        # Claude Code entry
├── UPGRADE_V2.md                    # Pstack v3.0 and v3.1 kernel hardening specifications
├── benchmarks/                      # Reproducible benchmark reports (latest-report.md, latest-metrics.json)
├── tests/                           # Standard library unit test suite (test_pstack_harness.py)
├── .cursor/rules/pstack.mdc         # Cursor IDE rules
├── adapters/opencode/commands/      # OpenCode slash commands (/pstack-build, /pstack-verify, /pstack-bench)
├── .agents/
│   ├── decision.tsv                 # Empirical decision and rollback ledger (runtime state)
│   ├── handoffs/                    # Handoff zone (active-brief, evidence-pack, drafts, verdict, logs/)
│   ├── pstack/                      # Static template repository (fallback via ~/.config/pstack/home)
│   │   ├── pstack-core.md           # Tier 0 coordinator kernel (strictly <= 48 lines)
│   │   ├── custom-banned-phrases.txt# Dynamic prose ban list managed via /correct
│   │   ├── custom-code-rules.tsv    # Dynamic code regex ban list managed via /correct
│   │   ├── playbooks/               # 6 specialized execution playbooks
│   │   └── principles/              # 5 core principles (Unslop, No-Comments, Prove-It-Works)
│   └── skills/pstack/SKILL.md       # Universal skill definition across 8 hosts
└── scripts/
    ├── pstack                       # Unified CLI (init|status|route|run|swarm|arena|resume|tree|hook|mcp|verify|test|bench)
    ├── pstack_resolver.py           # PSTACK_HOME and WORKSPACE_ROOT overlay resolver
    ├── pstack_router.py             # Bilingual Repo-Map and multi-language ranked symbol router
    ├── pstack_scheduler.py          # Parallel Worktree DAG pool, 3-way Git merge, and auto-rework loop
    ├── pstack_tree.py               # ASCII DAG tree and events.jsonl visualizer
    ├── pstack_hook.py               # Git pre-commit hook manager (install|uninstall|status)
    ├── pstack_mcp.py                # Zero-dependency JSON-RPC 2.0 Stdio MCP server (5 tools)
    ├── pstack_bench.py              # Reproducible compression and 12-case adversarial mutation benchmark
    ├── pstack_update.py             # Remote Git update checker and self-updater
    ├── pstack-verify.py             # 4-gate harness suite and verifier verdict evaluator
    ├── pstack-correct.py            # 5-tier correction scanner and rule injection tool
    ├── pstack-session.py            # <= 20-line cross-session snapshot (pause / pickup + crash recovery)
    ├── pstack-onboard.py            # Composite toolchain detector and Git commit-to-brief generator
    ├── verify-prose.py              # Bilingual unslop prose and [Builder Restate] validator
    ├── verify-code-slop.py          # Comment Sicko and custom-code-rules.tsv validator
    ├── verify-handoff.py            # Subagent handoff bounds and AST #symbol auto-heal validator
    ├── log-decision.py              # Ledger logging tool for decision.tsv
    ├── ag-spawn.sh                  # Resilient cross-CLI launcher with timeout, quarantine, and --max-rework
    └── bootstrap-repo.sh            # Global 8-host installer and project injector
```
