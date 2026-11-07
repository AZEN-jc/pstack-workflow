---
task_id: "pstack-v2.1-verifiable-harness"
role: "implementer"
target_agent: "antigravity"
playbook: ".agents/pstack/playbooks/architecture-feature.md"
required_principles:
  - ".agents/pstack/principles/prove-it-works.md"
  - ".agents/pstack/principles/no-comments.md"
  - ".agents/pstack/principles/unslop-zh-en.md"
verify_cmd: "python3 -m unittest discover -s tests -q && python3 scripts/verify-handoff.py && python3 scripts/verify-code-slop.py scripts"
---

## 1. User Goal (Restated)
针对外部工程评估指出的 4 个核心短板（质量门禁深度不足、文件修改后行号指针漂移、子 Agent 崩溃恢复缺失、缺少可复现 Benchmark 实验），在不增加 Codex 与 WorkBuddy 日常操作负担的前提下，规划并落地 Pstack v2.1 可验证工程 Harness。

## 2. Consolidated Directives (History & Delta)
- [Module 1: Deep Toolchain Gate 4 & Self-Tests] 升级 `scripts/pstack_onboard.py` 支持组合质量门禁探测（Test + Lint + Typecheck），并新增 `tests/test_pstack_harness.py` 标准库单元测试套件。
- [Module 2: Symbol Anchor & Auto-Heal Pointers] 升级 `scripts/verify-handoff.py` 支持 `file.py:20-60#func_name` 符号锚定、行号越界检查及 `--fix` 漂移行号自动重定位。
- [Module 3: Resilient Spawner & Crash Recovery] 升级 `scripts/ag-spawn.sh` 支持超时保护、`.agents/handoffs/logs/` 日志黑匣子、Codex `--full-auto` 非交互模式与 WorkBuddy 指令卡，异常退出时自动触发 `pstack pause` 保护现场。
- [Module 4: Reproducible Benchmark (`pstack bench`)] 新增 `scripts/pstack_bench.py`，默认离线模式（0 Token、<3s）实测三级上下文压缩比与 12 组正反例变异样本 100% 拦截率并生成 `benchmarks/latest-report.md`，同时支持 `--live` 真机双盲 A/B 实验。

## 3. Evidence Pointers (Read-Only Context)
- 入职与验证命令探测：`scripts/pstack_onboard.py:18-83#detect_verify_cmd`
- 交接单与指针校验器：`scripts/verify-handoff.py:239-329#verify_brief`
- 跨客户端派发脚本：`scripts/ag-spawn.sh:96-134#run_with_timeout_and_log`
- 跨窗口快照工具：`scripts/pstack_session.py:108-137#generate_snapshot`
- 四重门禁总控脚本：`scripts/pstack-verify.py:67-124#execute_verify_cmd`
- 核心单元测试套件：`tests/test_pstack_harness.py:43-277#TestPstackHarness`

## 4. Deliverable Contract
1. `python3 -m unittest discover -s tests -q` 单元测试全部通过（返回码 0）。
2. `pstack verify handoff --fix` 准确校验行号越界并自动修复 `#symbol` 漂移行号。
3. `pstack bench` 在 3 秒内完成上下文压缩比实测与 12 组变异样本 100% 拦截验证，输出 `benchmarks/latest-report.md`。
4. `pstack verify all` 四重门禁全部绿灯（返回码 0）。
