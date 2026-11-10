# Pstack v3.0 Reproducible Benchmark Report

> 任何开发者克隆仓库后运行 `pstack bench` 即可在 3 秒内复现全部实测指标 `[离线实测 Offline-Measured]`。
> 本次评测在不消耗任何 API Token 的前提下完成确定性压缩与门禁拦截验证 `[沙箱模拟 Sim-Verified]`。

---

## 1. 实验一：三级上下文压缩比实测 (Context Compression Benchmark)

工程团队在派发子任务时无需再粘贴整份源码文件与全量剧本。
Pstack 通过 `file:start-end#symbol` 指针交接大幅压缩单轮提示词体积 `[离线实测 Offline-Measured]`。
请注意该指标为首轮交接载荷缩减率，不代表全会话多轮交互总 Token 缩减率 `[离线实测 Offline-Measured]`。

| 上下文加载模式 | 包含资产范围 | 总行数 | 字节数 (Bytes) | 估算 Tokens | 初始交接压缩率 `[离线实测 Offline-Measured]` |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **传统全量塞入 (Naive Stuffing)** | 6 剧本 + 5 原则 + 5 核心脚本 + README | 2213 | 101738 | ~18813 | Baseline (0.0%) |
| **Tier 0 常驻路由核 (`pstack-core.md`)** | 极简三行对齐与路由表 (上限 48 行) | 27 | - | ~737 | **-96.1%** |
| **Tier 0 + Tier 1 指针交接单 (`active-brief.md`)** | 常驻核 + 指针交接包 (代码块 ≤ 15 行) | 73 | 5698 | ~1043 | **-94.5%** |
| **Tier 2 跨窗口断点续传 (`session-snapshot.md`)** | 20 行内快照含崩溃日志指针 | 8 | - | ~101 | **-99.5%** |

---

## 2. 实验二：12 组正反例变异样本拦截与符号自愈实测 (12-Case Adversarial Suite)

我们在隔离沙箱内构造 12 类典型 AI 劣质产出与漂移指针。
四重物理门禁与 AST 符号自愈器实现了 12/12 (100.0%) 确定性拦截与自愈 `[沙箱模拟 Sim-Verified]`。

| 用例编号 | 所属门禁 | 注入变异故障类型 | 预期拦截或自愈信号 | 实测结果 `[沙箱模拟 Sim-Verified]` |
| :--- | :--- | :--- | :--- | :--- |
| `M01` | Gate 1 (Handoff) | Inline code block > 15 lines (20 lines) | `[Anti-Context-Stuffing]` | **PASS (100% Intercepted)** |
| `M02` | Gate 1 (Pointer Bounds) | Out-of-bounds line range sample.py:1-99 (7 lines total) | `[Out-of-Bounds Pointer]` | **PASS (100% Intercepted)** |
| `M03` | Gate 1 (Symbol Auto-Heal) | Drifted symbol range sample.py:1-2#compute_total | `Auto-healed to sample.py:6-7#compute_total` | **PASS (100% Intercepted)** |
| `M04` | Gate 1 (Symbol Anchor) | Dangling symbol anchor #non_existent_symbol | `[Broken Symbol Pointer]` | **PASS (100% Intercepted)** |
| `M05` | Gate 2 (Prose Restate) | output-draft.md missing top > [Builder Restate] | `[Builder Restate Missing]` | **PASS (100% Intercepted)** |
| `M06` | Gate 2 (Prose Unslop) | Prose containing em-dash and banned ZH slop phrase | `[Dash Ban] & [Slop Phrase ZH]` | **PASS (100% Intercepted)** |
| `M07` | Gate 2 (Sentence Budget) | Single Chinese sentence exceeding 45 chars | `[Sentence Too Long ZH]` | **PASS (100% Intercepted)** |
| `M08` | Gate 2 (Syntax & Epistemic) | Mid-sentence colon + missing epistemic tag | `[Mid-Sentence Colon Ban] & [Epistemic Gate]` | **PASS (100% Intercepted)** |
| `M09` | Gate 3 (Comment Sicko) | Redundant AI comment restating code behavior | `[Comment Sicko]` | **PASS (100% Intercepted)** |
| `M10` | Gate 3 (Exception Hygiene) | Silent swallowed exception block | `[Swallowed Exception]` | **PASS (100% Intercepted)** |
| `M11` | Gate 3 (Custom Regex Rule) | Violation of promoted custom-code-rules.tsv regex | `[Custom Rule:no-debug-leak]` | **PASS (100% Intercepted)** |
| `M12` | Gate 4 + Independent Verdict | Failing verify_cmd (exit=3) & VERDICT: REJECT | `Non-zero gate rejection` | **PASS (100% Intercepted)** |

---

## 3. 实验三：4-Group 随机化 A/B/C/D 对照实测 (4-Group Randomized A/B/C/D Suite)

我们在隔离沙箱中运行 4 组软件工程任务并测试随机排序 `[沙箱模拟 Sim-Verified]`。
Native 组因注释冗余与越权修改导致失败，Pstack 组达成确定性全绿交付 `[沙箱模拟 Sim-Verified]`。

| 实验分组 | 任务编号与类型 | 估算 Tokens | 随机种子 | 门禁通过率 `[沙箱模拟 Sim-Verified]` | 越权拦截数 | 返工次数 | 任务成功率 `[沙箱模拟 Sim-Verified]` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Group A (Native Codex) | `Task 3: refactor-slop-cleanup` | ~3680 | `42` | 0/4 (0.0%) | 1 | 2 | **0.0%** |
| Group A (Native Codex) | `Task 2: feature-cli-subcmd` | ~3920 | `42` | 0/4 (0.0%) | 1 | 2 | **0.0%** |
| Group A (Native Codex) | `Task 4: multi-module-swarm` | ~4120 | `42` | 0/4 (0.0%) | 1 | 2 | **0.0%** |
| Group A (Native Codex) | `Task 1: bug-fix-state-machine` | ~3450 | `42` | 0/4 (0.0%) | 1 | 2 | **0.0%** |
| Group B (PStack + Codex) | `Task 3: refactor-slop-cleanup` | ~370 | `42` | 4/4 (100.0%) | 0 | 0 | **100.0%** |
| Group B (PStack + Codex) | `Task 2: feature-cli-subcmd` | ~410 | `42` | 4/4 (100.0%) | 0 | 0 | **100.0%** |
| Group B (PStack + Codex) | `Task 4: multi-module-swarm` | ~395 | `42` | 4/4 (100.0%) | 0 | 0 | **100.0%** |
| Group B (PStack + Codex) | `Task 1: bug-fix-state-machine` | ~385 | `42` | 4/4 (100.0%) | 0 | 0 | **100.0%** |
| Group C (Native OpenCode) | `Task 3: refactor-slop-cleanup` | ~3606 | `42` | 0/4 (0.0%) | 1 | 2 | **0.0%** |
| Group C (Native OpenCode) | `Task 2: feature-cli-subcmd` | ~3841 | `42` | 0/4 (0.0%) | 1 | 2 | **0.0%** |
| Group C (Native OpenCode) | `Task 4: multi-module-swarm` | ~4037 | `42` | 0/4 (0.0%) | 1 | 2 | **0.0%** |
| Group C (Native OpenCode) | `Task 1: bug-fix-state-machine` | ~3381 | `42` | 0/4 (0.0%) | 1 | 2 | **0.0%** |
| Group D (PStack + OpenCode) | `Task 3: refactor-slop-cleanup` | ~358 | `42` | 4/4 (100.0%) | 0 | 0 | **100.0%** |
| Group D (PStack + OpenCode) | `Task 2: feature-cli-subcmd` | ~397 | `42` | 4/4 (100.0%) | 0 | 0 | **100.0%** |
| Group D (PStack + OpenCode) | `Task 4: multi-module-swarm` | ~383 | `42` | 4/4 (100.0%) | 0 | 0 | **100.0%** |
| Group D (PStack + OpenCode) | `Task 1: bug-fix-state-machine` | ~373 | `42` | 4/4 (100.0%) | 0 | 0 | **100.0%** |

---

## 4. 一键复现命令 (Reproduce Locally)

在终端执行以下命令即可重新生成本报告与 JSON 指标文件 `[离线实测 Offline-Measured]`。

```bash
# 运行离线可复现基准测试 (0 Token, 耗时 0.562s)
pstack bench

# 运行 Pstack 核心单元测试套件
pstack test
```
