# Pstack v3.0: Protocol Stack Multi-Agent Harness

<p align="center"><b><a href="./README.md">English</a></b> | <b>简体中文</b></p>

<p align="center">
  <a href="https://github.com/AZEN-jc/pstack-workflow/actions/workflows/pstack-ci.yml"><img src="https://github.com/AZEN-jc/pstack-workflow/actions/workflows/pstack-ci.yml/badge.svg" alt="Pstack CI" /></a>
  <img src="https://img.shields.io/badge/Architecture-Dual--Tab_v3.0_Harness-2563EB?style=flat-square" alt="Architecture" />
  <img src="https://img.shields.io/badge/Context_Budget-Tier_0_%E2%89%A4_48_Lines-7C3AED?style=flat-square" alt="Context Budget" />
  <img src="https://img.shields.io/badge/Verification-4_Deterministic_Gates-10B981?style=flat-square" alt="Verification" />
</p>

<p align="center">
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Ecosystem-8_Local_Hosts_Mounted-06B6D4?style=flat-square" alt="Ecosystem" /></a>
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Handoff-Pointer--Only_(15_Lines_Max)-F97316?style=flat-square" alt="Handoff" /></a>
  <a href="https://github.com/AZEN-jc/pstack-workflow"><img src="https://img.shields.io/badge/Session_Snapshot-%E2%89%A4_20_Lines_Pickup-E11D48?style=flat-square" alt="Snapshot" /></a>
</p>

> 面向多智能体协作工作区的确定性协议栈与四重门禁工程约束体系 [离线实测 Offline-Measured]。
> 放任自流的编程智能体会发明大量冗长客套的会话废话，并在耗尽上下文前堆砌无法运行的补丁。
> Pstack v3.0 以四重自动化物理门禁与双标签页角色隔离替代脆弱的人性信任。
> 静态母版库与易变的业务仓库彻底物理隔离，在 8 大本地宿主实现全流程确定性工程约束。

---

## 1. 通俗原理解析：一分钟看懂 Pstack v3.0 (ELI5: What is Pstack?)

> **小白一分钟人话版 (TL;DR for Humans)**  
> 传统多 Agent 协作像几个新手在群聊里互相应酬客套。它们动辄刷屏几百行代码，导致上下文迅速挤爆并频繁报错。  
> Pstack v3.0 把它重构为工业级协议栈约束。常驻内核控制在 48 行以内。任务派发只传行号范围指针。桌面端双 Tab 分别承担构建与独立盲审，交付产物必须通过四重脚本检验。

日常使用 AI 编程时，最常遇到的挫败并非模型能力不足，而是缺乏工程纪律。
初始交接单载荷相对传统全量塞入压缩达 92.5% [离线实测 Offline-Measured]。
多轮长会话的综合 Token 变化取决于交互轮次与工具调用 [沙箱模拟 Sim-Verified]。

| 典型翻车场景 | 传统多 Agent 协作方式 | Pstack v3.0 确定性解法 | 终态实测收益 [离线实测 Offline-Measured] |
| :--- | :--- | :--- | :--- |
| **满屏客套挤爆窗口** | 互相吹捧并大量输出寒暄废话，长提示词挤占宝贵上下文。 | **Tier 0 极简内核 (≤48行)**。首句强制三行直入主题，草稿顶部强制 3 行复述头。 | 常驻上下文压缩至 ~450 Tokens |
| **代码大爆炸与坏味道** | 一次性甩出数百行巨额补丁，引入冗余注释与隐藏语法破坏。 | **指针交接单**。主从协作仅传 `file:start-end` 范围指针，严禁贴超 15 行源码。 | 单次交接降至 620 Tokens |
| **既当运动员又当裁判** | 同一个窗口写完代码自己夸自己通过，测试根本没跑或静默失败。 | **Gate 4 运行时摘要 + 双 Tab 盲审**。自动跑 `verify_cmd` 落盘 SHA256，新 Tab 四级裁决。 | 彻底杜绝口头谎报验证通过 |
| **跨天恢复靠翻聊天记录** | 换个窗口就要重贴几千行历史，或者把同一错误反复犯十次。 | **零 Token 离线工具链**。`pause/pickup` 生成 ≤20 行快照，`correct` 自动下沉正则禁令。 | ~150 Tokens 瞬间恢复完整状态 |

---

## 2. 核心架构：三级上下文预算与双 Tab 隔离 (Core Architecture)

调用者在任意外部仓库运行 `pstack` 时无需手工复制剧本。系统通过静态母版库与动态工作区解耦实现零断链运行 [离线实测 Offline-Measured]。

```text
                       +---------------------------------------+
                       |  Desktop Host (Tab 1 Builder / Tab 2) |
                       +---------------------------------------+
                                           |
                        /pstack-build -> verify all -> /pstack-verify
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
             | - pstack-core.md (≤48行) |    | - .agents/decision.tsv   |
             | - playbooks/ (6大剧本)   |    | - .agents/handoffs/      |
             | - custom-code-rules.tsv  |    |   * active-brief.md      |
             | - 4-gate harnesses       |    |   * evidence-pack.md     |
             | - correct/session/onboard|    |   * output-draft/final   |
             +--------------------------+    +--------------------------+
```

- **Tier 0 常驻路由层 (`pstack-core.md` ≤ 48 行)**：极简 3 行入口强制所有宿主首步读取 `.agents/pstack/pstack-core.md` [离线实测 Offline-Measured]。
- **Tier 1 双区证据包 (`evidence-pack.md`)**：同时保留静态代码行号指针与 Gate 4 自动生成的 `## Runtime Verification Digest`（含退出码、12 位 SHA256 与末尾 10 行输出）[沙箱模拟 Sim-Verified]。
- **桌面端同宿主双 Tab 闭环**：Tab 1 运行 `/pstack-build` 完成构建与四重门禁；同宿主新建空白 Tab 2 运行 `/pstack-verify`，输出 `ACT_ON / CONSIDER / NOTED / DISMISSED` 四级裁决并自动导出剥离复述头的 `.agents/handoffs/output-final.md` [沙箱模拟 Sim-Verified]。
- **Tier 2 零 Token 离线工具链 (`correct / pause / pickup / onboard`)**：平时消耗 0 Token，触发时输出严格控制在 20 行以内 [离线实测 Offline-Measured]。

---

## 3. 本机 8 大宿主与全局 CLI 挂载矩阵 (8-Host Matrix)

运行一次安装脚本即可在本机 8 大 Agent 宿主目录与 `~/.local/bin` 中同步激活 `pstack` [离线实测 Offline-Measured]。

| 挂载目标 | 全局挂载路径 | 项目级自动入口 | 核心定位 |
| :--- | :--- | :--- | :--- |
| **Global Anchor (`PSTACK_HOME`)** | `~/.config/pstack/home` | 供 `pstack_resolver.py` 层叠回退 | 静态剧本母版 |
| **Global CLI (`$PATH`)** | `~/.local/bin/{pstack,pstack-verify,ag-spawn}` | 任意目录直接运行 `pstack` | 统一命令行 |
| **Antigravity (`agy`)** | `~/.gemini/config/skills/pstack` | `AGENTS.md` + `SKILL.md` | 原生子进程协同 |
| **Claude Code (`claude`)** | `~/.claude/skills/pstack` | `CLAUDE.md` | 自动化终端 |
| **Codex CLI & App (`codex`)** | `~/.codex/skills/pstack` | `AGENTS.md` | 双 Tab 演练与盲审 |
| **OpenCode (`opencode`)** | `~/.config/opencode/skills/pstack` + `command/*.md` | `AGENTS.md` + 7 个 `/` 快捷命令 | 斜杠指令工作台 |
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

# 运行标准库单元测试套件与 0 Token 可复现基准测试 (生成 benchmarks/latest-report.md)
pstack test
pstack bench
pstack verify handoff --fix
```

完整的上下文压缩比与 12 组变异样本 100% 拦截实测数据请参阅 [benchmarks/latest-report.md](./benchmarks/latest-report.md) [离线实测 Offline-Measured]。

### 终端四重门禁运行样张

```text
====================================================================
PSTACK v3.0 FOUR-GATE VERIFICATION SUITE
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

完整 v3.0 升级规范请参阅 [UPGRADE_V2.md](./UPGRADE_V2.md)。

```text
.
├── AGENTS.md                        # Antigravity / Codex / OpenCode / Cursor / Pi 极简入口
├── CLAUDE.md                        # Claude Code 自动加载入口
├── UPGRADE_V2.md                    # Pstack v3.0 桌面端双角色隔离与可验证工程规范
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
    ├── pstack                       # 全局统一 CLI (init|status|verify|correct|pause|pickup|onboard|bench|test|update)
    ├── pstack_resolver.py           # PSTACK_HOME 与 WORKSPACE_ROOT 自发现及层叠解析器
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
    ├── ag-spawn.sh                  # 带超时保护与崩溃自动快照的跨宿主派发器
    └── bootstrap-repo.sh            # 8 路宿主全局安装与跨仓库注入脚本
```
