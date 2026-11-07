---
task_id: "pstack-v2-desktop-dual-role-04"
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
将仓库从 Pstack v1.0 升级至 v2.0（桌面端双角色隔离、四重实证门禁、8 路本机宿主全局挂载与零 Token 离线辅助工具链 `correct / pause / pickup / onboard`），确保所有新增脚本与文档 100% 通过静态与运行时门禁。

## 2. Consolidated Directives (History & Delta)
- [Round 1-3] 已完成基础双引擎剧本、三级路径自发现解析器 `pstack_resolver.py` 与 6 大 Agent 挂载。
- [Round 4 v2.0 升级指令] 按 Phase 1 -> Phase 2 -> Phase 3 顺序落地：
  1) **Phase 1（协议与四重门禁升级）**：
     - `.agents/handoffs/handoff-schema.json`：升级为 `PstackHandoffBriefV2`，`target_agent` 扩充为 `["opencode", "codex", "codex-review", "workbuddy", "pi", "claude", "antigravity"]`。
     - `.agents/pstack/custom-code-rules.tsv` + `scripts/verify-code-slop.py`：支持合并加载全局与本地 `custom-code-rules.tsv`（`rule_id\tpattern\treason`）自定义代码正则规则。
     - `scripts/verify-prose.py`：仅当被测文件名为 `output-draft.md`（或传 `--require-restate`）时，强制要求前 6 行包含 `> [Builder Restate]`（≤ 4 行）；并提供 `strip_builder_restate()` 支持导出干净定稿 `.agents/handoffs/output-final.md`。
     - `scripts/pstack-verify.py`：新增 Gate 4（执行 `verify_cmd`，若为递归 `pstack verify all` 则联动 `pstack_onboard.detect_verify_cmd` 获取非递归命令，将退出码、12 位 SHA256、`git diff --stat` 与末尾 10 行输出非破坏性更新至 `evidence-pack.md` 的 `## Runtime Verification Digest` 区块）；新增 `prep-verifier`、`verdict`（校验 `.agents/handoffs/verifier-verdict.md` 含 `ACT_ON`、`CONSIDER`、`NOTED`、`DISMISSED` 及 `VERDICT: PASS`，通过后自动生成 `output-final.md`）与 `export` 子模式。
  2) **Phase 2（桌面端同宿主双 Tab 闭环与 8 路挂载）**：
     - `.agents/pstack/pstack-core.md`：严格控制在 ≤ 48 行，纳入三级上下文预算与桌面端同宿主 Builder (`/pstack-build`) + Independent Verifier (`/pstack-verify`) 流程。
     - `.agents/skills/pstack/SKILL.md`：同步更新为 8 路宿主挂载与 v2.0 命令说明。
     - `adapters/opencode/commands/`：新增 `pstack-build.md`、`pstack-verify.md`、`pstack-pickup.md`。
     - `.agents/handoffs/output-draft.md` 与 `.agents/handoffs/verifier-verdict.md`：在 `output-draft.md` 顶部加入合规 `> [Builder Restate]` 块，新建 `verifier-verdict.md` 标准四级裁决样本。
     - `scripts/bootstrap-repo.sh` 与 `scripts/ag-spawn.sh`：在 `skill_targets` 与状态检查中新增 `"$HOME/.pi/agent/skills/pstack"` 与 `"$HOME/.agents/skills/pstack"`（共 8 路宿主），支持 `--light` / `--full` 别名；`ag-spawn.sh` 支持 `pi` 与 `workbuddy`。
  3) **Phase 3（零 Token 离线工具链 B/C/D 与文档归档）**：
     - 新建 `scripts/pstack_correct.py`（及 `scripts/pstack-correct.py` 入口）：支持 `--scan`（扫描 `decision.tsv` 的 `REVERT`/`ROOT_CAUSE` 高频教训）、`--code-rule "<regex>" "<reason>"`、`--prose-ban "<phrase>"`。
     - 新建 `scripts/pstack_session.py`（及 `scripts/pstack-session.py` 入口）：支持 `pause ["<note>"]`（生成严格 ≤ 20 行的 `.agents/handoffs/session-snapshot.md`）与 `pickup`（打印快照）。
     - 新建 `scripts/pstack_onboard.py`（及 `scripts/pstack-onboard.py` 入口）：支持 `--detect`（自动探测仓库测试/验证命令）与 `--to-thread [--commits 3] [--playbook tech-thread|build-in-public]`（从最近 Git Commit 与 `decision.tsv` 自动生成 `active-brief.md`）。
     - 升级 `scripts/pstack` 统一入口与 `scripts/pstack_resolver.py` 默认模板，创建合规的 `UPGRADE_V2.md` 并更新 `README.md`（均须通过 `verify-prose.py`）。

## 3. Evidence Pointers (Read-Only Context)
- 现有路径自发现解析器：`scripts/pstack_resolver.py:1-165`
- 现有门禁总控实现：`scripts/pstack-verify.py:1-90`
- 现有散文编译器实现：`scripts/verify-prose.py:1-155`
- 现有代码去噪器实现：`scripts/verify-code-slop.py:1-110`
- 现有全局安装器实现：`scripts/bootstrap-repo.sh:1-150`
- 现有主控调度核心：`.agents/pstack/pstack-core.md:1-30`

## 4. Deliverable Contract
完成 Phase 1 -> Phase 3 全部实现后，依次运行并确保退出码均为 `0`：
1. `./scripts/bootstrap-repo.sh --global && pstack status`（8/8 local agents + global CLI mounted）
2. `wc -l .agents/pstack/pstack-core.md`（必须 ≤ 48 行）
3. `pstack pause "v2.0 upgrade complete" && pstack pickup`（确认 `.agents/handoffs/session-snapshot.md` ≤ 20 行）
4. `pstack correct --scan && pstack onboard --detect`
5. `pstack verify all && pstack verify prep-verifier && pstack verify verdict`
6. `python3 scripts/verify-prose.py README.md && python3 scripts/verify-prose.py UPGRADE_V2.md`
