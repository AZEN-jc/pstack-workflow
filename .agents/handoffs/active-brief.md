---
task_id: "multi-agent-universal-deploy-02"
role: "implementer"
target_agent: "antigravity"
playbook: ".agents/pstack/playbooks/architecture-feature.md"
required_principles:
  - ".agents/pstack/principles/prove-it-works.md"
  - ".agents/pstack/principles/no-comments.md"
  - ".agents/pstack/principles/unslop-zh-en.md"
verify_cmd: "python3 scripts/pstack-verify.py all"
---

## 1. User Goal (Restated)
将当前 Pstack 仓库升级为本机全 Agent（Antigravity、Claude Code、Codex、OpenCode、Cursor）通用版，提供一键全局安装与卸载/状态诊断脚本，并准备好完整的 Git 仓库配置（`CLAUDE.md`、`.cursor/rules/pstack.mdc`、`adapters/opencode/`、`.gitignore`、`README.md`）以供推送至 GitHub。

## 2. Consolidated Directives (History & Delta)
- [Round 1] 已完成基础 Pstack 双引擎目录、6 大剧本、5 大原则与三重校验脚本。
- [Round 2 增量] 新增跨 Agent 适配层：
  1) 根目录新增 `CLAUDE.md`（与 `AGENTS.md` 保持一致的 4 行极简入口，供 Claude Code 自动加载）；
  2) 新增 `.cursor/rules/pstack.mdc`（供 Cursor IDE 自动加载）；
  3) 新增 `adapters/opencode/commands/` 下的 4 个斜杠命令模板（`adapters/opencode/commands/pstack.md`, `adapters/opencode/commands/tech-thread.md`, `adapters/opencode/commands/interrogate.md`, `adapters/opencode/commands/unslop.md`）；
  4) 升级 `.agents/skills/pstack/SKILL.md`，在技能目录内软链或打包 `pstack` 与 `scripts` 引用，使 `codex`、`claude`、`opencode`、`cursor`、`agy` 在任意目录唤醒 `pstack` 技能时都能找到剧本与校验脚本；
  5) 升级 `scripts/bootstrap-repo.sh`，支持 `--global`（一键挂载到本机 `~/.gemini/config/skills/pstack`、`~/.claude/skills/pstack`、`~/.codex/skills/pstack`、`~/.config/opencode/skills/pstack` + `~/.config/opencode/command/`、`~/.cursor/skills-cursor/pstack`）、`--status`（打印 5 大 Agent 挂载状态诊断表）以及 `<target_repo> [copy|symlink]`（跨仓库注入 `AGENTS.md`、`CLAUDE.md`、`.cursor/rules/pstack.mdc`、`.agents/`、`scripts/`）；
  6) 新增 `.gitignore` 与符合 `.agents/pstack/principles/unslop-zh-en.md` 门禁标准的 `README.md`（中英架构与部署文档，必须通过 `scripts/verify-prose.py` 校验）。

## 3. Evidence Pointers (Read-Only Context)
- 本机多 Agent 目录探测结果：`.agents/handoffs/evidence-pack.md:1-14`
- 现有安装脚本：`scripts/bootstrap-repo.sh:1-40`
- 现有技能定义：`.agents/skills/pstack/SKILL.md:1-35`
- 门禁总控脚本：`scripts/pstack-verify.py:1-85`

## 4. Deliverable Contract
完成上述文件新增与升级后，依次运行：
1. `./scripts/bootstrap-repo.sh --global`
2. `./scripts/bootstrap-repo.sh --status`
3. `python3 scripts/pstack-verify.py all`
4. `python3 scripts/verify-prose.py README.md`
确保所有命令返回码为 `0` 且输出 `ALL CHECKS GREEN`。
