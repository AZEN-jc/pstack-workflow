# Pstack (Poteto Stack) Multi-Agent Harness

Pstack 是一套面向硬核软件工程与技术深潜写作的双引擎工作流。它使调用者在 5 大主流 Agent 中获得一致的零废话代码与实证长文产出 `[实测 Measured]`。

本仓库受 Lauren Tan (`@poteto`) 的 `pstack` 与 `unslop` 启发构建。系统通过主从物理隔离与三重确定性脚本门禁消除上下文污染 `[推导 Inferred]`。

## 1. 核心架构与设计纪律 (Core Architecture)

调用者在启动任何开发或写作任务时，主控线程仅负责对齐目标与挂载剧本。繁重的源码扫描、初稿撰写与对抗挑刺全部交由全新子 Agent 执行 `[实测 Measured]`。

- **4 行极简入口 (`AGENTS.md` / `CLAUDE.md` / `.cursor/rules/pstack.mdc`)**：砍掉冗长提示词，强制所有 Agent 首步读取 `.agents/pstack/poteto-core.md`。
- **首句三行对齐 (`In-Your-Own-Words`)**：禁止寒暄，首句直接输出 `Target`、`Premise & Bottleneck` 与 `Smallest Leap`。
- **剧本原样挂载 (`Playbooks`)**：内置 `tech-thread`、`build-in-public`、`bug-fix`、`architecture-feature`、`interrogate` 与 `figure-it-out` 六大剧本。
- **只传指针不塞原文 (`Pointer-Only Handoff`)**：主从交接单 `.agents/handoffs/active-brief.md` 仅允许传递 `file:start-end` 行号指针，严禁粘贴超过 15 行源码。
- **三重确定性门禁 (`Deterministic Harnesses`)**：交付前必须通过交接单检查、零 AI 腔散文检查与 `Comment Sicko` 代码注释检查 `[实测 Measured]`。

## 2. 本机 5 大 Agent 全局挂载矩阵 (Universal Agent Matrix)

运行一次安装脚本即可在本机 5 大 Agent 环境中同步激活 `pstack` 技能 `[实测 Measured]`。

| Agent 平台 | 全局技能挂载路径 | 项目级自动入口 |
| :--- | :--- | :--- |
| **Antigravity (`agy`)** | `~/.gemini/config/skills/pstack` | `AGENTS.md` + `.agents/skills/pstack/SKILL.md` |
| **Claude Code (`claude`)** | `~/.claude/skills/pstack` | `CLAUDE.md` |
| **Codex CLI (`codex`)** | `~/.codex/skills/pstack` | `AGENTS.md` |
| **OpenCode (`opencode`)** | `~/.config/opencode/skills/pstack` + `~/.config/opencode/command/` | `AGENTS.md` |
| **Cursor IDE (`cursor`)** | `~/.cursor/skills-cursor/pstack` | `.cursor/rules/pstack.mdc` + `AGENTS.md` |

## 3. 快速安装与跨仓库注入 (Quick Start)

在终端运行以下命令完成全局挂载、状态诊断与跨项目注入：

```bash
# 1. 一键挂载至本机全部 5 大 Agent 全局目录
./scripts/bootstrap-repo.sh --global

# 2. 检查 5 大 Agent 全局挂载状态
./scripts/bootstrap-repo.sh --status

# 3. 将 Pstack 注入任意目标业务仓库 (支持 copy 或 symlink)
./scripts/bootstrap-repo.sh /path/to/your/repo symlink
```

## 4. 确定性门禁与 `/correct` 永久拉黑 (Verification CLI)

所有代码与长文产出必须通过 `scripts/pstack-verify.py` 校验且返回码为 `0` `[实测 Measured]`：

```bash
# 运行全部三重门禁 (Handoff + Prose Unslop + Code Comment Sicko)
python3 scripts/pstack-verify.py all

# 单独校验 Markdown 文章的 AI 腔、句长、破折号与证据标签
python3 scripts/verify-prose.py README.md

# 单独校验源码中的废话注释与静默吞异常
python3 scripts/verify-code-slop.py scripts/

# 触发 /correct 机制，将特定套话永久写入黑名单
python3 scripts/pstack-verify.py ban "心智负担"

# 记录实证实验与架构取舍至 .agents/decision.tsv
python3 scripts/log-decision.py add \
  --task-id "multi-agent-mount-05" \
  --verdict "KEEP" \
  --hypothesis "统一软链可将Pstack同步挂载至5大本机Agent" \
  --pointer "scripts/bootstrap-repo.sh:1-102" \
  --before "仅Antigravity单端可用" \
  --after "5/5本机Agent全部挂载通过" \
  --lesson "通过各Agent全局skills目录软链同源SKILL.md实现零漂移复用"
```

## 5. 目录拓扑 (Repository Topology)

```text
.
├── AGENTS.md                        # Antigravity / Codex / OpenCode / Cursor 极简入口
├── CLAUDE.md                        # Claude Code 自动加载入口
├── .cursor/rules/pstack.mdc         # Cursor IDE 自动加载规则
├── adapters/opencode/commands/      # OpenCode 全局斜杠命令 (/pstack, /tech-thread, /interrogate, /unslop)
├── .agents/
│   ├── decision.tsv                 # 实证决策与踩坑回滚账本
│   ├── handoffs/                    # 主从 Agent 指针交接区 (active-brief.md, evidence-pack.md, output-draft.md)
│   ├── pstack/
│   │   ├── poteto-core.md           # 主控 Agent 路由内核
│   │   ├── custom-banned-phrases.txt# /correct 动态追加禁用词库
│   │   ├── playbooks/               # 6 大场景强制执行剧本
│   │   └── principles/              # 5 大底层铁律 (Unslop, No-Comments, Prove-It-Works 等)
│   └── skills/pstack/SKILL.md       # 跨平台通用 Skill 定义
└── scripts/
    ├── pstack-verify.py             # 门禁总控与 /correct 禁用词追加 CLI
    ├── verify-prose.py              # 中英双语 Unslop 散文校验器
    ├── verify-code-slop.py          # Comment Sicko 代码坏味道校验器
    ├── verify-handoff.py            # 子 Agent 交接单防膨胀校验器
    ├── log-decision.py              # decision.tsv 实证入账工具
    ├── ag-spawn.sh                  # 跨 CLI 无状态子 Agent 派发器
    └── bootstrap-repo.sh            # 5 大 Agent 全局安装与跨仓库注入脚本
```
