---
task_id: "pstack-v3.1-kernel-hardening"
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
  - ".cursor/rules/*"
  - ".github/*"
  - "adapters/*"
  - "benchmarks/*"
  - "scripts/*"
  - "tests/*"
  - "AGENTS.md"
  - "CLAUDE.md"
  - "README.md"
  - "README_ZH.md"
  - "UPGRADE_V2.md"
model_tier: "deep_tier"
---

## 1. User Goal (Restated)
落地 Pstack v3.1 四大内核硬化模块：中英双语 Repo-Map 多语言符号排序发现、真并行 Worktree 层级池与三方 Git 补丁合并、有界自愈自动返工闭环 (`--max-rework`)、以及 Git Pre-Commit 钩子管理器 (`pstack hook`) 与零依赖 Stdio MCP 服务器 (`pstack mcp`)。

## 2. Consolidated Directives (History & Delta)
- [Module 1: Bilingual Repo-Map] 升级 `scripts/pstack_router.py`，内置中英工程词典与多语言 (`.py/.ts/.tsx/.js/.go/.rs/.sh`) 符号跨文件加权排序，消除中文关键词失明与字母序回退缺陷。
- [Module 2: Parallel Worktree & 3-Way Merge] 升级 `scripts/pstack_scheduler.py`，新增 `topological_levels` 与 `ThreadPoolExecutor` 同层并发执行，使用 `git apply --3way` 传播非重叠同文件修改与文件删除并捕获 `[Merge Conflict]`。
- [Module 3: Bounded Auto-Rework] 在 `scripts/pstack_scheduler.py`、`scripts/pstack_router.py` 与 `scripts/ag-spawn.sh` 落地 `run_with_auto_rework` 与 `--max-rework <N>`，自动提取 `[Gate Failure Digest]` 注入简报并拉起全新无状态子 Agent。
- [Module 4: Hook & MCP Server] 新增 `scripts/pstack_hook.py` (`pstack hook`) 与 `scripts/pstack_mcp.py` (`pstack mcp`)，暴露 5 个 JSON-RPC 2.0 MCP 工具并同步挂载至 `bootstrap-repo.sh`、文档与 CI。

## 3. Evidence Pointers (Read-Only Context)
- 任务路由与符号发现：`scripts/pstack_router.py:486-645#auto_discover_pointers_and_scope`
- 拓扑调度与沙箱合入：`scripts/pstack_scheduler.py:72-235#merge_worktree_to_workspace`
- 多语言正则大括号跨度：`scripts/verify-handoff.py:284-327#_find_regex_symbol_span`
- 无状态派发与脏树隔离：`scripts/ag-spawn.sh:103-245#on_spawn_exit`
- 门禁总控入口：`scripts/pstack-verify.py:342-432#main`

## 4. Deliverable Contract
1. 新增并跑通 5 项核心硬化单元测试（总计 25 项测试全部通过）。
2. `./scripts/pstack mcp --self-test`、`./scripts/pstack hook status`、`./scripts/pstack test` 与 `./scripts/pstack bench` 全部返回码 0。
3. `python3 scripts/verify-code-slop.py scripts tests` 零违规，`verify-prose.py` 校验文档零违规。
4. `./scripts/bootstrap-repo.sh --global`、`./scripts/pstack verify handoff --fix`、`./scripts/pstack verify all`、`./scripts/pstack verify prep-verifier --blind` 与 `./scripts/pstack verify verdict` 全部退出码 0。
