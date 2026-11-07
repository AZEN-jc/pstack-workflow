---
task_id: "pstack-v2.2-empirical-ci-harness"
role: "implementer"
target_agent: "antigravity"
playbook: ".agents/pstack/playbooks/architecture-feature.md"
required_principles:
  - ".agents/pstack/principles/prove-it-works.md"
  - ".agents/pstack/principles/no-comments.md"
  - ".agents/pstack/principles/unslop-zh-en.md"
verify_cmd: "python3 -m unittest discover -s tests -q && python3 scripts/verify-handoff.py && python3 scripts/verify-code-slop.py scripts tests"
---

## 1. User Goal (Restated)
根据 Pstack v2.2 演进计划与评审意见，补全实证可信闭环：落地三级实证标签（离线/沙箱/真机）、原子级半写入隔离与混沌故障注入、严格盲审模式（--blind）、3-Task 确定性沙箱 A/B 评测套件及 GitHub Actions 自动公证流水线。

## 2. Consolidated Directives (History & Delta)
- [Module 1: 3-Tier Epistemic Honesty] 升级 `scripts/verify-prose.py` 支持三级标签，更新 README 及 benchmark 报告消除指标混淆。
- [Module 2: Atomic Dirty-Tree Quarantine & Chaos Tests] 升级 `scripts/ag-spawn.sh` 与 `pstack_session.py` 实现崩溃与超时半写入自动剥离与恢复，并在 `tests/test_pstack_harness.py` 补充混沌测试。
- [Module 3: Blind Verifier & 3-Task Sandbox Suite] 升级 `scripts/pstack-verify.py` 支持 `--blind` 严格盲审（<=25行），并在 `scripts/pstack_bench.py` 落地 3-Task 确定性沙箱对照实验。
- [Module 4: GitHub Actions CI] 落地 `.github/workflows/pstack-ci.yml` 自动化公证流水线与 CI 徽章。

## 3. Evidence Pointers (Read-Only Context)
- 三级实证校验器：`scripts/verify-prose.py:76-80#strip_inline_markup`
- 跨客户端派发与隔离：`scripts/ag-spawn.sh:233-317#run_with_timeout_and_log`
- 会话快照与隔离记录：`scripts/pstack_session.py:112-147#generate_snapshot`
- 严格盲审模式实现：`scripts/pstack-verify.py:147-275#prep_verifier_digest`
- 确定性基准评测套件：`scripts/pstack_bench.py:687-770#run_live_ab_experiment`
- 自动化测试用例：`tests/test_pstack_harness.py:261-303#TestPstackHarness.test_spawner_workbuddy_and_crash_trap`

## 4. Deliverable Contract
1. `python3 -m unittest discover -s tests -q` 与新增的混沌故障注入测试全部通过。
2. `scripts/ag-spawn.sh` 在进程崩溃或超时后自动导出 `crash-partial-*.patch` 并清理脏树。
3. `pstack verify prep-verifier --blind` 输出 strictly <= 25 行并写入 `blind-review-pack.md`。
4. `pstack bench` 运行 3-Task 确定性沙箱评测并更新 `benchmarks/latest-report.md` 与 metrics。
5. `pstack verify all && pstack verify prep-verifier --blind && pstack verify verdict` 全部返回码 0。
6. GitHub Actions CI 配置文件 `.github/workflows/pstack-ci.yml` 正常生效。
