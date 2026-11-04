---
task_id: "self-discovery-zero-broken-links-03"
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
彻底解决脱离当前母版目录后的路径断链问题，实现「统一安装器 + 静态母版库 (`PSTACK_HOME`) 与动态工作区 (`WORKSPACE_ROOT`) 自发现解耦 + 全局 `$PATH` 统一 CLI (`~/.local/bin/pstack`)」，确保在任意未初始化或软链外部目录中均可零配置运行。

## 2. Consolidated Directives (History & Delta)
- [Round 1-2] 已完成 5 大 Agent 全局技能挂载与基础三重门禁。
- [Round 3 核心重构] 消除 `Path(__file__).resolve().parent.parent` 耦合与脱离目录断链：
  1) 新建 `scripts/pstack_resolver.py`：
     - `get_pstack_home() -> Path`：按 `$PSTACK_HOME` -> `Path(__file__).resolve().parent.parent` -> `~/.config/pstack/home` 自动定位母版静态资产库。
     - `get_workspace_root(target_hint: Path | None = None) -> Path`：按 `$PSTACK_WORKSPACE` -> 从 `target_hint` 或 `Path.cwd()` 向上逐级检索 `.agents` / `.git` / `AGENTS.md` -> 回退 `Path.cwd()`，精准定位当前业务工作区。
     - `resolve_asset(rel_path: str, workspace_root: Path | None = None) -> Path`：Overlay 层叠查找，优先返回 `workspace_root / rel_path`，若不存在则透明回退至 `get_pstack_home() / rel_path`（使外部项目无需复制 `.agents/pstack/` 即可直接引用所有 `playbooks/`、`principles/`、`handoff-schema.json`）。
     - `ensure_workspace_skeleton(workspace_root: Path) -> None`：在任意新工作区按需惰性初始化 `.agents/decision.tsv` 与 `.agents/handoffs/{active-brief.md,evidence-pack.md,output-draft.md}`。
  2) 改造 `verify-prose.py`、`verify-handoff.py`、`pstack-verify.py`、`log-decision.py`：全部接入 `pstack_resolver.py`，合并读取全局与项目本地 `custom-banned-phrases.txt`，支持在任意外部目录运行。
  3) 新建统一命令入口 `scripts/pstack`（Bash CLI）：支持 `pstack init [dir]`、`pstack status`、`pstack verify [all|prose|handoff|code]`、`pstack spawn [runner]`、`pstack log [list|add ...]`、`pstack ban "<phrase>"`、`pstack path`（打印当前解析出的 `PSTACK_HOME` 与 `WORKSPACE_ROOT`）。
  4) 升级 `scripts/bootstrap-repo.sh` 与 `scripts/ag-spawn.sh`：
     - `--global` 除挂载 5 大 Agent 技能外，自动创建全局稳定锚点 `~/.config/pstack/home` 并将 `pstack`、`pstack-verify`、`ag-spawn` 软链至 `~/.local/bin/`（已在 `$PATH` 中）；
     - 跨仓库注入支持 `light`（默认轻量模式：仅在目标仓库写入 4 行 `AGENTS.md`/`CLAUDE.md`/`.cursor/rules/pstack.mdc` 与 `.agents/decision.tsv` + `.agents/handoffs/`，静态规则与脚本直接通过自发现复用全局母版）、`symlink` 与 `copy` 三种模式。
  5) 更新 `AGENTS.md`、`CLAUDE.md`、`.cursor/rules/pstack.mdc`、`.agents/skills/pstack/SKILL.md`、`adapters/opencode/commands/*.md` 与 `README.md`，支持 `pstack` 全局命令与相对路径双兼容，并通过 `verify-prose.py README.md`。

## 3. Evidence Pointers (Read-Only Context)
- 现有交接校验器路径耦合点：`scripts/verify-handoff.py:60-155`
- 现有门禁总控路径耦合点：`scripts/pstack-verify.py:45-85`
- 现有散文校验器路径耦合点：`scripts/verify-prose.py:25-65`
- 现有安装器实现：`scripts/bootstrap-repo.sh:1-116`
- 现有派发器实现：`scripts/ag-spawn.sh:1-45`

## 4. Deliverable Contract
完成代码实现后，必须运行以下实证检验（包括在 `/tmp` 下创建全新外部目录的脱离母版测试）：
1. `./scripts/bootstrap-repo.sh --global && ./scripts/bootstrap-repo.sh --status`
2. 在 `/tmp` 创建全新隔离目录测试 `cd /tmp/pstack-isolated-test && pstack init && pstack path && pstack verify all`（测试完成后清理 `/tmp/pstack-isolated-test`）
3. `python3 scripts/pstack-verify.py all && python3 scripts/verify-prose.py README.md`
所有命令返回码必须为 `0` 且输出 `ALL CHECKS GREEN`。
