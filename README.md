# Pstack v2.0: Protocol Stack Multi-Agent Harness

<p align="center"><b>English</b> | <b><a href="./README_ZH.md">简体中文</a></b></p>

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Dual--Tab_v2.0_Harness-2563EB?style=flat-square" alt="Architecture" />
  <img src="https://img.shields.io/badge/Context_Budget-Tier_0_%E2%89%A4_48_Lines-7C3AED?style=flat-square" alt="Context Budget" />
  <img src="https://img.shields.io/badge/Verification-4_Deterministic_Gates-10B981?style=flat-square" alt="Verification" />
</p>

<p align="center">
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Ecosystem-8_Local_Hosts_Mounted-06B6D4?style=flat-square" alt="Ecosystem" /></a>
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Handoff-Pointer--Only_(15_Lines_Max)-F97316?style=flat-square" alt="Handoff" /></a>
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Session_Snapshot-%E2%89%A4_20_Lines_Pickup-E11D48?style=flat-square" alt="Snapshot" /></a>
</p>

> Deterministic protocol stack and 4-gate verification harness for coding agents [Measured].
> Left unconstrained, coding agents hallucinate imports and generate verbose conversational filler.
> They paste unvetted diffs across broken paths before exhausting context windows.
> Pstack v2.0 replaces conversational trust with 4 mechanical gates and dual-tab role isolation.
> Static playbooks and volatile projects stay physically decoupled across 8 local hosts.

---

## 1. ELI5: What is Pstack?

> **TL;DR for Humans**  
> Conventional multi-agent setups act like newcomers exchanging pleasantries in group chats. They paste hundreds of code lines, blowing context windows and failing silently.  
> Pstack v2.0 refactors agent workflows into industrial protocol stack constraints. The core stays under 48 lines. Task handoffs pass range pointers only. Dual desktop tabs isolate building from blind verification under 4 deterministic gates.

AI coding failures stem from poor discipline, not weak models.

| Failure Mode | Conventional Agent Setup | Pstack v2.0 Deterministic Solution | Measured Payoff [Measured] |
| :--- | :--- | :--- | :--- |
| **Conversational Bloat** | Excessive politeness and verbose filler exhausting context windows. | **Tier 0 Minimal Core (≤48 lines)**. Immediate 3-line triage, mandatory 3-line draft restate header. | Baseline context compressed to ~450 tokens |
| **Code Smells & Explosions** | Massive diffs pasted at once, introducing redundant comments and broken syntax. | **Pointer-Only Handoffs**. Handoffs pass `file:start-end` pointers only; code snippets capped at 15 lines. | Per-turn brief drops to 620 tokens |
| **Conflicted Self-Review** | Agents declare their own code tested and approved without running builds. | **Gate 4 Runtime Digest + Blind Dual-Tab Review**. Auto-runs `verify_cmd`, records SHA256, 4-tier verdict in fresh tab. | Zero falsified test passes |
| **Lost Session Resumption** | Re-pasting thousands of chat lines to resume work, repeating past failures. | **Zero-Token Offline Toolchain**. `pause/pickup` generates ≤20-line snapshots; `correct` registers regex bans. | Full session recovery in ~150 tokens |

---

## 2. Core Architecture: 3-Tier Context Budgeting & Dual-Tab Isolation

Running pstack needs no manual playbook copying. Decoupled templates ensure zero-break execution [Measured].

```text
                       +---------------------------------------+
                       |  Desktop Host (Tab 1 Builder / Tab 2) |
                       +---------------------------------------+
                                           |
                        /pstack-build -> verify all -> /pstack-verify
                                           v
                       +---------------------------------------+
                       |       pstack_resolver.py (3-Tier)     |
                       +---------------------------------------+
                                     /           \
            Overlay Fallback        /             \   Local Workspace
                                   v               v
             +--------------------------+    +--------------------------+
             | PSTACK_HOME (Template)   |    | WORKSPACE_ROOT (Project) |
             |  ~/.config/pstack/home   |    |  /path/to/any/repo       |
             +--------------------------+    +--------------------------+
             | - pstack-core.md (≤48 L) |    | - .agents/decision.tsv   |
             | - playbooks/ (6 books)   |    | - .agents/handoffs/      |
             | - custom-code-rules.tsv  |    |   * active-brief.md      |
             | - 4-gate harnesses       |    |   * evidence-pack.md     |
             | - correct/session/onboard|    |   * output-draft/final   |
             +--------------------------+    +--------------------------+
```

- **Tier 0 Resident Routing (`pstack-core.md` ≤ 48 lines)**: Minimal 3-line entry mandates every agent to read `.agents/pstack/pstack-core.md` first [Measured].
- **Tier 1 Dual-Zone Evidence Pack (`evidence-pack.md`)**: Preserves static line pointers alongside Gate 4 generated `## Runtime Verification Digest` (exit code, 12-char SHA256, last 10 log lines) [Measured].
- **Desktop Dual-Tab Isolation**: Tab 1 runs `/pstack-build` for implementation and 4-gate validation. Fresh Tab 2 runs `/pstack-verify`, emits 4-tier verdict (`ACT_ON / CONSIDER / NOTED / DISMISSED`), and exports sanitized `output-final.md` [Measured].
- **Tier 2 Zero-Token Offline Toolchain (`correct / pause / pickup / onboard`)**: Consumes 0 tokens during normal operation, output strictly capped at 20 lines when invoked [Measured].

---

## 3. 8-Host Matrix & Global CLI Mounts

One bootstrap run mounts pstack across 8 hosts. Global CLI activates simultaneously in ~/.local/bin [Measured].

| Target Host | Global Mount Path | Project Auto Entry | Core Role |
| :--- | :--- | :--- | :--- |
| **Global Anchor (`PSTACK_HOME`)** | `~/.config/pstack/home` | Fallback root for `pstack_resolver.py` | Static playbook templates |
| **Global CLI (`$PATH`)** | `~/.local/bin/{pstack,pstack-verify,ag-spawn}` | Run `pstack` directly anywhere | Unified command-line interface |
| **Antigravity (`agy`)** | `~/.gemini/config/skills/pstack` | `AGENTS.md` + `SKILL.md` | Native subagent orchestration |
| **Claude Code (`claude`)** | `~/.claude/skills/pstack` | `CLAUDE.md` | Automated terminal workflow |
| **Codex CLI & App (`codex`)** | `~/.codex/skills/pstack` | `AGENTS.md` | Dual-tab drills and blind verification |
| **OpenCode (`opencode`)** | `~/.config/opencode/skills/pstack` + `command/*.md` | `AGENTS.md` + 7 slash commands | Slash command workspace |
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

All deliverables must pass 4 harness gates. Verdicts require review via pstack verify verdict [Measured].

```bash
# Run all 4 deterministic gates (Gate 1 Handoff + Gate 2 Prose + Gate 3 Code Slop + Gate 4 Runtime cmd)
pstack verify all

# Generate a ≤20-line read-only review summary for fresh Independent Verifier tab
pstack verify prep-verifier

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

# Run unit tests and 0-token reproducible benchmark (outputs benchmarks/latest-report.md)
pstack test
pstack bench
pstack verify handoff --fix
```

See [benchmarks/latest-report.md](./benchmarks/latest-report.md) for full benchmark metrics [Measured].

### Terminal 4-Gate Output Sample

```text
====================================================================
PSTACK v2.0 FOUR-GATE VERIFICATION SUITE
====================================================================
[1/4] Handoff Brief Check   : .agents/handoffs/active-brief.md -> PASS (Schema V2 + Symbol Auto-Heal)
[2/4] Prose & Restate Check : .agents/handoffs/output-draft.md -> PASS (Builder Restate + 0 slop)
[3/4] Comment Sicko & Rules : scripts/ (1 custom rule)         -> PASS (0 violations)
[4/4] Runtime verify_cmd    : exit=0, sha256=1aefa2e6acf7      -> PASS (evidence-pack.md updated)
====================================================================
STATUS : ALL 4 HARNESS GATES GREEN (Return Code: 0)
====================================================================
```

---

## 6. Repository Topology

See [UPGRADE_V2.md](./UPGRADE_V2.md) for full v2.0/v2.1 specifications.

```text
.
├── AGENTS.md                        # Antigravity / Codex / OpenCode / Cursor / Pi entry
├── CLAUDE.md                        # Claude Code entry
├── UPGRADE_V2.md                    # Pstack v2.0/v2.1 dual-role isolation and upgrade specs
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
    ├── pstack                       # Unified CLI (init|status|verify|correct|pause|pickup|onboard|bench|test|update)
    ├── pstack_resolver.py           # PSTACK_HOME and WORKSPACE_ROOT overlay resolver
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
    ├── ag-spawn.sh                  # Resilient cross-CLI launcher with timeout and crash trap
    └── bootstrap-repo.sh            # Global 8-host installer and project injector
```
