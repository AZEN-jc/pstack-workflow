# Pstack：面向编程 Agent 的确定性 Worktree 并行调度与 4-Gate 验证引擎

<p align="center"><b><a href="./README.md">English</a></b> | <b>简体中文</b></p>

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

> 面向多智能体工作区的跨客户端自动路由、并行 Worktree 调度与四重门禁引擎 [离线实测 Offline-Measured]。
> 放任自流的编程智能体会输出冗长客套废话，并在并发修改时互相覆盖主分支文件。
> Pstack v3.1 以双语 Repo-Map 路由、物理 Worktree 沙箱、自动回炉闭环与提交钩子替代人性信任。
> 静态母版库与易变的业务仓库彻底物理隔离，在 8 大本地宿主与原生 MCP 客户端实现确定性约束。

---

## 1. 通俗原理解析：一分钟看懂 Pstack v3.1 (ELI5: What is Pstack?)

> **小白一分钟人话版 (TL;DR for Humans)**  
> 传统多 Agent 协作像几个新手在同一个文件夹里乱改。它们动辄刷屏几百行代码，互相覆盖文件并谎报测试通过。  
> Pstack v3.1 将其升级为自动化调度与验证引擎。输入一句话目标即可跨 7 种语言自动提取 AST 符号指针。各子任务在独立 Git Worktree 并发运行，门禁失败自动拉起全新子进程回炉，并通过三路补丁安全合入。

日常使用 AI 编程时，最常遇到的挫败并非模型能力不足，而是缺乏工程纪律。
初始交接单载荷相对传统全量塞入压缩达 93.5% [离线实测 Offline-Measured]。
多轮长会话的综合 Token 变化取决于交互轮次与工具调用 [沙箱模拟 Sim-Verified]。

| 典型翻车场景 | 传统多 Agent 协作方式 | Pstack v3.1 确定性引擎解法 | 终态实测收益 [离线实测 Offline-Measured] |
| :--- | :--- | :--- | :--- |
| **记不住命令与手写找文件** | 调用者手动查文件行号填模板，纯中文目标无法匹配英文代码。 | **双语 Repo-Map 自动路由 (`pstack route/run`)**。跨 `.py/.ts/.js/.go/.rs/.sh` 提取加权符号，按 `models.json` 自动分流模型。 | 0 Token 毫秒级自动建单 (<50ms) |
| **多 Agent 并发互踩文件** | 多个子进程在主工作区同时改代码，互相覆盖或漏删文件。 | **真并行 Worktree Swarm 与 Arena (`pstack swarm/arena`)**。分波次线程池并发、路径白名单锁与 `git apply --3way` 三路合入。 | 并发修改与文件删除 0 冲突丢码 |
| **门禁一报错就要人擦屁股** | 单测或代码检查没过就原地停摆，等待人工手动重发提示词。 | **有界自动回炉闭环 (`--max-rework 2`) 与脏树补丁隔离**。自动提取报错注入交接单并拉起全新子进程修复；崩溃残骸剥离为 `.patch`。 | 门禁失败全自动无状态回炉自愈 |
| **满屏客套与行号漂移失灵** | 寒暄废话挤爆上下文，改几行代码后原有的行号指针全部指偏。 | **Tier 0 极简核 (≤48行) + AST 符号自愈 (`file:start-end#symbol`)**。`--fix` 自动重定位漂移函数行号，内联代码限制 15 行。 | 首轮交接载荷缩减 93.5% |
| **既当运动员又当裁判** | 同一个窗口写完代码自己夸自己通过，测试根本没跑或静默失败。 | **Gate 4 组合工具链 + 严格盲审 (`--blind`)**。自动串联 `Test + Lint + Typecheck` 落盘 SHA256，剥离自述供 Tab 2 盲审。 | 12/12 变异故障样本 100% 拦截 |
| **绕过检查直接提交 Git** | Agent 忘记执行检查命令，直接把带坏味道的代码提交入库。 | **物理 Pre-Commit 钩子 (`pstack hook`) + 原生 MCP 服务 (`pstack mcp`)**。在 `git commit` 时强制锁死门禁，暴露 5 个标准 Stdio MCP 工具。 | 提交阶段 100% 物理级防绕过 |

---

## 2. 核心架构：双语 Repo-Map 路由、并行 Worktree 与自动回炉闭环

调用者在任意外部仓库运行 `pstack` 时无需手工复制剧本。系统通过静态母版解耦与物理 Worktree 沙箱实现零断链运行 [离线实测 Offline-Measured]。

```text
                 一句话目标: pstack run "修复状态机超时恢复异常" --max-rework 2
                                            |
                                            v
           +-----------------------------------------------------------------+
           | 1. 双语 Repo-Map 自动路由器 (pstack_router.py + models.json)    |
           |    - 意图与复杂度识别 -> fast_tier (Flash) / deep_tier (Pro)    |
           |    - 多语言 AST/正则符号加权排序 (.py/.ts/.go/.rs/.sh)          |
           +-----------------------------------------------------------------+
                                            |
                                            v
           +-----------------------------------------------------------------+
           | 2. 真并行 Worktree 隔离调度器 (pstack_scheduler.py)             |
           |    - Swarm 波次并发线程池 / Arena 多模型同题竞技                |
           |    - 独立 Git Worktree 沙箱 (.agents/worktrees/<node_id>)       |
           |    - allowed_paths 越权拦截 + 崩溃半写入 .patch 剥离回滚        |
           +-----------------------------------------------------------------+
                                            |
                         +------------------+------------------+
                         |     四重确定性物理门禁 (Gate 1-4)    |
                         |   通过? ----否 (r <= max_rework)----+--> 提取报错注入 Brief
                         +------------------+------------------+    并拉起全新子进程回炉
                                            | 是
                                            v
           +-----------------------------------------------------------------+
           | 3. git apply --3way 三路合入 + 严格盲审 (--blind) + 定稿导出    |
           |    - Pre-Commit 物理钩子 (.git/hooks/pre-commit) & MCP Server   |
           |    - DAG 检查点续跑 (dag-state.json) & 终端任务树 (pstack tree) |
           +-----------------------------------------------------------------+
```

- **Tier 0 常驻路由层 (`pstack-core.md` ≤ 48 行)**：极简 3 行入口强制所有宿主首步读取 `.agents/pstack/pstack-core.md` [离线实测 Offline-Measured]。
- **中英双语 Repo-Map 与五角色模型矩阵 (`models.json`)**：将 `coordinator`、`architect`、`builder`、`reviewer`、`verifier` 按复杂度映射至 `fast_tier` 或 `deep_tier` 模型 [离线实测 Offline-Measured]。
- **真并行 Worktree 层级池与 Git 三路合并**：按拓扑波次并发运行无依赖节点，强制校验 `allowed_paths` 边界，并通过 `git apply --3way` 同步同文件并发修改与文件删除 [沙箱模拟 Sim-Verified]。
- **有界自动回炉与双 Tab 严格盲审**：门禁失败时自动注入报错摘要并拉起全新子进程重试（上限 `--max-rework` 次），通过后输出 ≤25 行 `--blind` 盲审包供 Tab 2 独立裁决 [沙箱模拟 Sim-Verified]。
- **物理 Pre-Commit 钩子与零依赖 MCP Server**：将门禁挂载至 `.git/hooks/pre-commit`，并通过 JSON-RPC 2.0 Stdio 原生暴露 `pstack_route`、`pstack_verify`、`pstack_swarm`、`pstack_arena`、`pstack_tree` 五大工具 [离线实测 Offline-Measured]。

---

## 3. 本机 8 大宿主、全局 CLI 与原生 MCP 挂载矩阵 (8-Host & MCP Matrix)

运行一次安装脚本即可在本机 8 大 Agent 宿主目录与 `~/.local/bin` 中同步激活 `pstack` [离线实测 Offline-Measured]。

| 挂载目标 | 全局挂载路径 | 项目级自动入口 | 核心定位 |
| :--- | :--- | :--- | :--- |
| **Global Anchor (`PSTACK_HOME`)** | `~/.config/pstack/home` | 供 `pstack_resolver.py` 层叠回退 | 静态剧本母版 |
| **Global CLI (`$PATH`)** | `~/.local/bin/pstack*` (13 个 CLI) | 任意目录直接运行 `pstack` | 统一命令行 |
| **Native MCP Server (`stdio`)** | `~/.local/bin/pstack-mcp` (`pstack mcp`) | JSON-RPC 2.0 Stdio (5 个 MCP 工具) | 原生 MCP 协议服务 |
| **Git Pre-Commit Hook** | `.git/hooks/pre-commit` (`pstack hook install`) | 提交代码时自动强制触发门禁 | 物理级防绕过锁 |
| **Antigravity (`agy`)** | `~/.gemini/config/skills/pstack` | `AGENTS.md` + `SKILL.md` | 原生子进程协同 |
| **Claude Code (`claude`)** | `~/.claude/skills/pstack` | `CLAUDE.md` | 自动化终端 |
| **Codex CLI & App (`codex`)** | `~/.codex/skills/pstack` | `AGENTS.md` | Worktree 演练与盲审 |
| **OpenCode (`opencode`)** | `~/.config/opencode/skills/pstack` + `command/*.md` | `AGENTS.md` + 9 个 `/` 快捷命令 | 斜杠指令工作台 |
| **Cursor IDE (`cursor`)** | `~/.cursor/skills-cursor/pstack` | `.cursor/rules/pstack.mdc` + `AGENTS.md` | 编辑器内联规则 |
| **WorkBuddy AI (`workbuddy`)** | `~/.workbuddy-ai/skills/pstack` | `AGENTS.md` + `SKILL.md` | 桌面端双 Tab 宿主 |
| **Pi Agent (`pi`)** | `~/.pi/agent/skills/pstack` | `AGENTS.md` + `SKILL.md` | 极简桌面与终端宿主 |
| **Universal Agent Pool** | `~/.agents/skills/pstack` | 跨宿主通用技能发现池 | 通用标准挂载点 |

---

## 4. 30 秒开箱与跨仓库轻量初始化 (Quick Start)

在终端运行以下命令完成 8 路宿主全局挂载与跨项目初始化：

```bash
# 1. 一键挂载 8 路 Agent 技能、OpenCode 斜杠命令与 ~/.local/bin/pstack
./scripts/bootstrap-repo.sh --global

# 2. 检查 8/8 宿主与全局 CLI 挂载状态
pstack status

# 3. 在任意外部项目初始化轻量工作区 (支持 --light | --full | --symlink)
cd /path/to/your/repo && pstack init --light

# 4. 自动探测当前项目的验证命令，或从最近 3 次提交直接生成技术推文简报
pstack onboard --detect
pstack onboard --to-thread --commits 3 --playbook tech-thread
```

---

## 5. 统一 CLI、四重门禁与零 Token 工具链 (Verification & Tooling CLI)

所有代码与长文产出必须通过 `pstack verify all` 四重门禁与 `pstack verify verdict` 裁决校验 [沙箱模拟 Sim-Verified]。

```bash
# 运行全部四重门禁 (Gate 1 Handoff + Gate 2 Prose + Gate 3 Code Slop + Gate 4 Runtime cmd)
pstack verify all

# 为新建的 Independent Verifier 标签页输出 ≤25 行盲审包
pstack verify prep-verifier --blind

# 校验 .agents/handoffs/verifier-verdict.md 四级裁决并自动导出干净定稿 output-final.md
pstack verify verdict

# 五层纠错下沉：扫描 decision.tsv 高频 REVERT 教训，追加自定义代码正则或散文禁令
pstack correct --scan
pstack correct --code-rule "^\s*print\([\"']DEBUG" "禁止遗留临时 DEBUG print 语句"
pstack correct --prose-ban "心智负担"

# 跨窗口/跨天断点续传：生成与读取严格 ≤20 行的 session-snapshot.md
pstack pause "完成核心模块重构与四重门禁验证"
pstack pickup

# 远程更新检查与自更新同步
pstack update --check
pstack update

# 运行标准库单元测试、0 Token 可复现基准与 MCP 自检
pstack test
pstack bench
pstack mcp --self-test
pstack verify handoff --fix

# 中英双语 Repo-Map 路由、前置 /reframe -> /sharpen 暂存转建单、有界自动返工、真并行 Swarm 与 Git 提交前钩子
pstack route "修复状态机超时恢复异常" --json
pstack route --from-sharpen
pstack run --from-sharpen --max-rework 2
pstack run "修复路由 Bug" --runner codex --max-rework 2
pstack swarm --dry-run && pstack arena --dry-run && pstack tree
pstack hook install && pstack hook status
```

完整的上下文压缩比与 12 组变异样本 100% 拦截实测数据请参阅 [benchmarks/latest-report.md](./benchmarks/latest-report.md) [离线实测 Offline-Measured]。

### 终端四重门禁运行样张

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

## 6. 目录拓扑 (Repository Topology)

完整 v3.0 与 v3.1 内核硬化规范请参阅 [UPGRADE_V2.md](./UPGRADE_V2.md)。

```text
.
├── AGENTS.md                        # Antigravity / Codex / OpenCode / Cursor / Pi 极简入口
├── CLAUDE.md                        # Claude Code 自动加载入口
├── UPGRADE_V2.md                    # Pstack v3.0 与 v3.1 内核硬化工程规范
├── benchmarks/                      # 可复现基准测试报告 (latest-report.md, latest-metrics.json)
├── tests/                           # 标准库单元测试套件 (test_pstack_harness.py)
├── .cursor/rules/pstack.mdc         # Cursor IDE 自动加载规则
├── adapters/opencode/commands/      # OpenCode 全局斜杠命令 (/pstack-build, /pstack-verify, /pstack-bench 等)
├── .agents/
│   ├── decision.tsv                 # 实证决策与踩坑回滚账本 (动态工作区状态)
│   ├── handoffs/                    # 交接区 (active-brief, evidence-pack, output-draft/final, verifier-verdict, logs/)
│   ├── pstack/                      # 静态母版资产库 (通过 ~/.config/pstack/home 全局层叠回退)
│   │   ├── pstack-core.md           # Tier 0 主控调度内核 (严格 ≤ 48 行)
│   │   ├── custom-banned-phrases.txt# /correct 动态追加散文禁用词库
│   │   ├── custom-code-rules.tsv    # /correct 动态追加代码正则禁令表
│   │   ├── playbooks/               # 6 大场景强制执行剧本
│   │   └── principles/              # 5 大底层铁律 (Unslop, No-Comments, Prove-It-Works 等)
│   └── skills/pstack/SKILL.md       # 8 路宿主通用 Skill 定义
└── scripts/
    ├── pstack                       # 全局统一 CLI (init|status|route|run|swarm|arena|resume|tree|hook|mcp|verify|test|bench)
    ├── pstack_resolver.py           # PSTACK_HOME 与 WORKSPACE_ROOT 自发现及层叠解析器
    ├── pstack_router.py             # 中英双语 Repo-Map 与多语言符号加权路由器
    ├── pstack_scheduler.py          # 真并行 Worktree 层级池、三方 Git 合入与自动返工调度器
    ├── pstack_tree.py               # ASCII 任务树与 events.jsonl 可视化引擎
    ├── pstack_hook.py               # Git Pre-Commit 钩子管理器 (install|uninstall|status)
    ├── pstack_mcp.py                # 零依赖 JSON-RPC 2.0 Stdio MCP 服务器 (暴露 5 大工具)
    ├── pstack_bench.py              # 可复现上下文压缩比与 12 组变异样本拦截基准测试套件
    ├── pstack_update.py             # 远程 Git 更新检查与跨 Agent 自同步工具
    ├── pstack-verify.py             # 四重门禁总控、Verifier 摘要与裁决校验器
    ├── pstack-correct.py            # 五层纠错扫描与自定义代码/散文规则下沉工具
    ├── pstack-session.py            # ≤ 20 行跨窗口断点快照 (pause / pickup + 崩溃日志恢复)
    ├── pstack-onboard.py            # 组合质量门禁探测与 Git Commit 转推文 Brief 生成器
    ├── verify-prose.py              # 中英双语 Unslop 散文与 [Builder Restate] 校验器
    ├── verify-code-slop.py          # Comment Sicko 与 custom-code-rules.tsv 校验器
    ├── verify-handoff.py            # 交接单行号边界校验与 AST #symbol 漂移自愈器
    ├── log-decision.py              # decision.tsv 实证入账工具
    ├── ag-spawn.sh                  # 带超时保护、脏树隔离与 --max-rework 的跨宿主派发器
    └── bootstrap-repo.sh            # 8 路宿主全局安装与跨仓库注入脚本
```
