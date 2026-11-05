# Pstack: Protocol Stack Multi-Agent Harness

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Dual--Engine_Harness-2563EB?style=flat-square" alt="Architecture" />
  <img src="https://img.shields.io/badge/Discipline-Deterministic_Coordination-7C3AED?style=flat-square" alt="Discipline" />
  <img src="https://img.shields.io/badge/Verification-0_Slop_%7C_Zero_Sycophancy-10B981?style=flat-square" alt="Verification" />
</p>

<p align="center">
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Ecosystem-6_Agents_Native-06B6D4?style=flat-square" alt="Ecosystem" /></a>
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Handoff-Pointer--Only_(15_Lines_Max)-F97316?style=flat-square" alt="Handoff" /></a>
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Gates-3_Deterministic_Checkers-E11D48?style=flat-square" alt="Gates" /></a>
</p>

> Autonomous protocol stack harness for multi-agent workspaces.
> Left unconstrained, coding agents hallucinate imports and invent verbose conversational filler.
> They paste 500-line diffs across broken paths before anyone notices syntax failures.
> Pstack replaces conversational trust with mechanical verification gates [Measured].
> Immutable playbooks stay separated from mutable repository state.

> 面向多智能体协作工作区的协议栈级确定性工程约束体系。
> 放任自流的编程智能体会发明大量冗长客套的废话。
> 它们在耗尽上下文窗口前，在错误路径上堆砌无法编译的补丁。
> Pstack 以三重自动化物理门禁替代脆弱的人性信任 [推导 Inferred]。
> 静态母版库与易变的业务仓库彻底物理隔离。

---

## 1. 通俗原理解析：一分钟看懂 Pstack (ELI5: What is Pstack?)

> **小白一分钟人话版 (TL;DR for Humans)**  
> 传统多 Agent 协作像几个新手在群聊里互相应酬客套。它们动辄刷屏几百行代码，导致上下文迅速挤爆并频繁报错。  
> Pstack 把它重构为工业级协议栈约束。主从协作禁止任何客套。任务派发只传行号范围指针。交付产物必须通过三重自动化脚本检验。

日常使用 AI 编程时，最常遇到的挫败并非模型能力不足，而是缺乏工程纪律。

| 典型翻车场景 | 传统多 Agent 协作方式 | Pstack 协议栈确定性解法 | 终态实测收益 [实测 Measured] |
| :--- | :--- | :--- | :--- |
| **满屏客套挤爆窗口** | 互相吹捧并大量输出“好的我来为您实现”，挤占宝贵上下文。 | **三行直入主题**。首句强制输出目标、痛点与最小动作，禁止任何寒暄客套。 | 上下文信噪比大幅提升 |
| **代码大爆炸与坏味道** | 一次性甩出数百行巨额补丁，引入大量冗余注释与隐藏语法破坏。 | **指针交接单**。主从协作仅传 `file:start-end` 范围指针，严禁大段贴源码。 | 边界精准，杜绝盲目改写 |
| **跨项目规则频繁断链** | 每次新建项目都要重新复制提示词，规则散落且版本极难同步。 | **双引擎三层自发现**。静态全局母版与业务工作区物理分离，按需层叠解析。 | 任意仓库直接 `pstack init` |
| **人工肉眼检查防不胜防** | 开发者耗费大量精力逐行肉眼排查虚假注释、AI 腔与未捕获异常。 | **三重机械自动化门禁**。交接单格式、文本除油与代码洁癖检测器卡死返回码。 | 门禁不全绿不准交付产物 |

### 三大工程公理 (Core Axioms)

- **只传指针不塞原文**。主从任务派发仅传递行号范围，绝不冗余搬运大段源码。
- **动态状态与静态母版解耦**。业务代码随时更迭，但工程铁律与执行剧本保持全局固化。
- **机械门禁胜过口头嘱咐**。不依赖提示词里的口头叮嘱，以返回码拦截所有不合格产出。

---

## 2. 核心架构与三层自发现 (Core Architecture)

调用者在任意外部仓库运行 `pstack` 时无需手工复制剧本。系统通过静态母版库与动态工作区解耦实现零断链运行 [实测 Measured]。

```text
                      +---------------------------------------+
                      |         Developer / Terminal          |
                      +---------------------------------------+
                                          |
                                    pstack init / verify
                                          v
                      +---------------------------------------+
                      |       pstack_resolver.py (3层解析)     |
                      +---------------------------------------+
                                    /           \
           Overlay Fallback        /             \   Local Workspace
                                  v               v
            +--------------------------+    +--------------------------+
            | PSTACK_HOME (全局母版)   |    | WORKSPACE_ROOT (业务项目)|
            |  ~/.config/pstack/home   |    |  /path/to/any/repo       |
            +--------------------------+    +--------------------------+
            | - pstack-core.md (主控)  |    | - .agents/decision.tsv   |
            | - playbooks/ (6大剧本)   |    | - .agents/handoffs/      |
            | - principles/ (铁律)     |    |   * active-brief.md      |
            | - verification harnesses |    |   * evidence-pack.md     |
            +--------------------------+    +--------------------------+
```

- **4 行极简入口 (`AGENTS.md` / `CLAUDE.md` / `.cursor/rules/pstack.mdc`)**：砍掉冗长提示词，强制所有 Agent 首步读取 `.agents/pstack/pstack-core.md`。
- **三层路径自发现 (`scripts/pstack_resolver.py`)**：自动分离静态母版库 `PSTACK_HOME` (`~/.config/pstack/home`) 与当前业务工作区 `WORKSPACE_ROOT`。
- **层叠资产解析 (`Overlay Asset Lookup`)**：外部轻量工作区仅保留 `.agents/decision.tsv` 与 `handoffs/`，静态剧本与原则自动回退至全局母版 [实测 Measured]。
- **只传指针不塞原文 (`Pointer-Only Handoff`)**：主从交接单 `.agents/handoffs/active-brief.md` 仅允许传递 `file:start-end` 行号指针，严禁粘贴超过 15 行源码。
- **三重确定性门禁 (`Deterministic Harnesses`)**：交付前必须通过交接单检查、零 AI 腔散文检查与 `Comment Sicko` 代码注释检查 [实测 Measured]。

---

## 3. 本机 6 大 Agent 与全局 CLI 挂载矩阵 (Universal Matrix)

运行一次安装脚本即可在本机 6 大 Agent 环境与 `~/.local/bin` 中同步激活 `pstack` [实测 Measured]。

| 挂载目标 | 全局挂载路径 | 项目级自动入口 | 核心定位 |
| :--- | :--- | :--- | :--- |
| **Global Anchor (`PSTACK_HOME`)** | `~/.config/pstack/home` | 供 `pstack_resolver.py` 层叠回退 | 静态剧本母版 |
| **Global CLI (`$PATH`)** | `~/.local/bin/{pstack,pstack-verify,ag-spawn}` | 任意目录直接运行 `pstack` | 统一命令行 |
| **Antigravity (`agy`)** | `~/.gemini/config/skills/pstack` | `AGENTS.md` + `.agents/skills/pstack/SKILL.md` | 双引擎协同 |
| **Claude Code (`claude`)** | `~/.claude/skills/pstack` | `CLAUDE.md` | 自动化终端 |
| **Codex CLI (`codex`)** | `~/.codex/skills/pstack` | `AGENTS.md` | 无状态执行 |
| **OpenCode (`opencode`)** | `~/.config/opencode/skills/pstack` + `~/.config/opencode/command/` | `AGENTS.md` | 斜杠指令 |
| **Cursor IDE (`cursor`)** | `~/.cursor/skills-cursor/pstack` | `.cursor/rules/pstack.mdc` + `AGENTS.md` | 编辑器规则 |
| **WorkBuddy AI (`workbuddy`)** | `~/.workbuddy-ai/skills/pstack` | `AGENTS.md` + `SKILL.md` | 本地 Agent |

---

## 4. 30 秒开箱与跨仓库轻量初始化 (Quick Start)

在终端运行以下命令完成全局挂载与诊断：

```bash
# 1. 一键挂载 5 大 Agent 技能与 ~/.local/bin/pstack 全局命令
./scripts/bootstrap-repo.sh --global

# 2. 检查全局挂载状态
pstack status

# 3. 在任意外部项目初始化轻量工作区 (默认 light 模式，支持 light|symlink|copy)
cd /path/to/your/repo && pstack init

# 4. 查看当前解析出的 PSTACK_HOME 与 WORKSPACE_ROOT
pstack path
```

---

## 5. 统一 CLI 与确定性门禁 (Verification CLI)

所有代码与长文产出必须通过 `pstack verify` 校验且返回码为 `0` [实测 Measured]：

```bash
# 运行全部三重门禁 (Handoff + Prose Unslop + Code Comment Sicko)
pstack verify all

# 单独校验 Markdown 文章的 AI 腔、句长、破折号与证据标签
pstack verify prose README.md

# 单独校验源码中的废话注释与静默吞异常
pstack verify code scripts/

# 派发全新无状态子 Agent (支持 opencode | codex | codex-review | claude | agy | dry-run)
pstack spawn dry-run

# 触发 /correct 机制，将特定套话永久写入黑名单
pstack ban "心智负担"

# 记录实证实验与架构取舍至当前工作区的 .agents/decision.tsv
pstack log add \
  --task-id "self-discovery-07" \
  --verdict "KEEP" \
  --hypothesis "Overlay层叠解析可在外部空目录零复制复用全局剧本与门禁" \
  --pointer "scripts/pstack_resolver.py:1-145" \
  --before "脱离母版目录即报路径断链" \
  --after "任意外部目录pstack init与verify all 100%全绿" \
  --lesson "将静态规则资产与动态工作区状态解耦可彻底消除跨目录断链"
```

### 终端门禁运行样张

```text
====================================================================
PSTACK DETERMINISTIC VERIFICATION SUITE
====================================================================
[1/3] Handoff Brief Check   : .agents/handoffs/active-brief.md -> PASS (0 pointers overflow)
[2/3] Prose Unslop Check    : README.md                        -> PASS (0 slop words, 0 dashes)
[3/3] Comment Sicko Check   : scripts/                         -> PASS (0 redundant comments)
====================================================================
STATUS : ALL CHECKS GREEN (Return Code: 0)
====================================================================
```

---

## 6. 目录拓扑 (Repository Topology)

```text
.
├── AGENTS.md                        # Antigravity / Codex / OpenCode / Cursor 极简入口
├── CLAUDE.md                        # Claude Code 自动加载入口
├── .cursor/rules/pstack.mdc         # Cursor IDE 自动加载规则
├── adapters/opencode/commands/      # OpenCode 全局斜杠命令 (/pstack, /tech-thread, /interrogate, /unslop)
├── .agents/
│   ├── decision.tsv                 # 实证决策与踩坑回滚账本 (动态工作区状态)
│   ├── handoffs/                    # 主从 Agent 指针交接区 (active-brief.md, evidence-pack.md, output-draft.md)
│   ├── pstack/                      # 静态母版资产库 (支持通过 ~/.config/pstack/home 全局层叠回退)
│   │   ├── pstack-core.md           # 主控 Agent 协议栈调度内核
│   │   ├── custom-banned-phrases.txt# /correct 动态追加禁用词库
│   │   ├── playbooks/               # 6 大场景强制执行剧本
│   │   └── principles/              # 5 大底层铁律 (Unslop, No-Comments, Prove-It-Works 等)
│   └── skills/pstack/SKILL.md       # 跨平台通用 Skill 定义
└── scripts/
    ├── pstack                       # 全局统一 CLI 入口 (init|status|path|verify|spawn|log|ban)
    ├── pstack_resolver.py           # PSTACK_HOME 与 WORKSPACE_ROOT 自发现及层叠解析器
    ├── pstack-verify.py             # 门禁总控与 /correct 禁用词追加 CLI
    ├── verify-prose.py              # 中英双语 Unslop 散文校验器
    ├── verify-code-slop.py          # Comment Sicko 代码坏味道校验器
    ├── verify-handoff.py            # 子 Agent 交接单防膨胀校验器
    ├── log-decision.py              # decision.tsv 实证入账工具
    ├── ag-spawn.sh                  # 跨 CLI 无状态子 Agent 派发器
    └── bootstrap-repo.sh            # 5 大 Agent 全局安装与跨仓库注入脚本
```
