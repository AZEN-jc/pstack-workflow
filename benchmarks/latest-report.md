# Pstack v2.1 Reproducible Benchmark Report

> 任何开发者克隆仓库后运行 `pstack bench` 即可在 3 秒内复现本报告全部实测指标 `[实测 Measured]`。
> 离线基准测试在不消耗任何 API Token 的前提下完成上下文压缩测算与 12 组变异攻击拦截验证 `[实测 Measured]`。

---

## 1. 实验一：三级上下文压缩比实测 (Context Compression Benchmark)

工程团队在派发子任务时无需再粘贴整份源码文件与全量剧本。
Pstack 通过 `file:start-end#symbol` 指针交接大幅压缩单轮提示词体积 `[实测 Measured]`。

| 上下文加载模式 | 包含资产范围 | 总行数 | 字节数 (Bytes) | 估算 Tokens | 相对缩减率 `[实测 Measured]` |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **传统全量塞入 (Naive Stuffing)** | 6 剧本 + 5 原则 + 5 核心脚本 + README | 1851 | 87036 | ~16269 | Baseline (0.0%) |
| **Tier 0 常驻路由核 (`pstack-core.md`)** | 极简三行对齐与路由表 (上限 48 行) | 27 | - | ~757 | **-95.3%** |
| **Tier 0 + Tier 1 指针交接单 (`active-brief.md`)** | 常驻核 + 指针交接包 (代码块 ≤ 15 行) | 61 | 6390 | ~1219 | **-92.5%** |
| **Tier 2 跨窗口断点续传 (`session-snapshot.md`)** | 20 行内快照含崩溃日志指针 | 8 | - | ~101 | **-99.4%** |

---

## 2. 实验二：12 组正反例变异样本拦截与符号自愈实测 (12-Case Adversarial Suite)

我们在隔离沙箱内构造 12 类典型 AI 劣质产出与漂移指针。
四重物理门禁与 AST 符号自愈器实现了 12/12 (100.0%) 确定性拦截与自愈 `[实测 Measured]`。

| 用例编号 | 所属门禁 | 注入变异故障类型 | 预期拦截或自愈信号 | 实测结果 `[实测 Measured]` |
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

## 3. 一键复现命令 (Reproduce Locally)

在终端执行以下命令即可重新生成本报告与 JSON 指标文件 `[实测 Measured]`：

```bash
# 运行离线可复现基准测试 (0 Token, 耗时 0.198s)
pstack bench

# 运行 Pstack 核心单元测试套件
pstack test
```
