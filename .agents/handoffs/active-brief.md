---
task_id: "pstack-v3.0-universal-orchestration-engine"
role: "coordinator"
target_agent: "antigravity"
playbook: ".agents/pstack/playbooks/architecture-feature.md"
required_principles:
  - ".agents/pstack/principles/prove-it-works.md"
  - ".agents/pstack/principles/no-comments.md"
  - ".agents/pstack/principles/unslop-zh-en.md"
verify_cmd: "python3 -m unittest discover -s tests -q && python3 scripts/verify-handoff.py && python3 scripts/verify-code-slop.py scripts tests"
allowed_paths:
  - ".agents/*"
  - ".github/*"
  - "adapters/*"
  - "benchmarks/*"
  - "scripts/*"
  - "tests/*"
  - "README.md"
  - "README_ZH.md"
  - "UPGRADE_V2.md"
model_tier: "deep_tier"
---

## 1. User Goal (Restated)
构建 Pstack v3.0 通用 Agent 自动路由与 Worktree 隔离调度引擎，解决 Cursor 官方 PStack 深度绑定生态、缺少确定性物理隔离和机械门禁的问题，实现一句话目标自动意图分类建单、五角色模型矩阵路由、Swarm 并行 Worktree DAG 与 Arena 竞技调度、四组 ABCD 随机化对照基准以及 CLI 任务树与事件流可观测性。

## 2. Consolidated Directives (History & Delta)
- [Module 1: Task Router & Model Matrix] 落地 `.agents/pstack/models.json`、`scripts/pstack_router.py`，支持 `pstack route` 与 `pstack run` 毫秒级意图识别、模型分流与自动交接单生成。
- [Module 2: Worktree Scheduler] 落地 `scripts/pstack_scheduler.py`，实现 `WorktreeSandbox` 物理隔离、`allowed_paths` 越权修改拦截、`Swarm` DAG 并行拓扑合入、`Arena` 择优竞技与 `dag-state.json` 断点续跑。
- [Module 3: ABCD Benchmark] 升级 `scripts/pstack_bench.py` 支持 A/B/C/D 四组随机化对照实验（Native Codex/OpenCode vs Pstack+Codex/OpenCode），评测成功率、耗时、Token 与返工次数。
- [Module 4: Observability & Version Unification] 落地 `scripts/pstack_tree.py` 与 `events.jsonl` 事件流协议，全仓统一升级至 `Pstack v3.0`。

## 3. Evidence Pointers (Read-Only Context)
- 自动路由与意图分类实现：`scripts/pstack_router.py:99-156#classify_goal`
- 符号与上下文自动发现：`scripts/pstack_router.py:178-268#auto_discover_pointers_and_scope`
- 物理 Worktree 隔离沙箱：`scripts/pstack_scheduler.py:66-200#WorktreeSandbox`
- 任务树终端可视化引擎：`scripts/pstack_tree.py:15-64#render_ascii_tree`
- 自动化门禁测试套件：`tests/test_pstack_harness.py:548-604#TestPstackHarness.test_router_goal_classification_and_brief_generation`

## 4. Deliverable Contract
1. `python3 -m unittest discover -s tests -q` 20 项单元测试全部通过。
2. `pstack route "修复状态机异常" --json` 准确输出意图分类与模型路由。
3. `pstack swarm --dry-run`、`pstack arena --dry-run`、`pstack tree` 正常运行。
4. `pstack bench` 完成 ABCD 评测并在 `benchmarks/latest-report.md` 生成完整报告。
5. `pstack verify all && pstack verify prep-verifier --blind && pstack verify verdict` 全部返回码 0。
