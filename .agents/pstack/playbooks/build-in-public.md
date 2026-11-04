# Playbook: Build-in-Public Postmortem (从 decision.tsv 提炼踩坑复盘长文)

启动本剧本时，必须先将以下 6 个步骤原封不动复制到主控 Todo 列表中，按序推进：

- [ ] **Step 1: Ledger Mining (审计表高信噪比筛选)**
  读取 `.agents/decision.tsv`，筛选出包含 `REVERT`（试错回滚）、`ROOT_CAUSE`（隐蔽根因）或 `PERF_WIN`（性能突破）的记录。提取其 `hypothesis`、`evidence_pointer` 及前后对比指标（`metric_before` -> `metric_after`），汇总至 `.agents/handoffs/evidence-pack.md`。

- [ ] **Step 2: Premise Reversal Extraction (提炼认知反转弧线)**
  结合 `.agents/pstack/principles/attack-the-premise.md`，明确写出：
  1) 我们最初信奉的错误假设（What we thought was true）；
  2) 打脸该假设的那条具体实测数据或报错（The exact moment reality broke the hypothesis）；
  3) 修正后的系统不变量（The new structural invariant）。

- [ ] **Step 3: Narrative & Artifact Blueprint (长文结构与可复现产物设计)**
  规划 4 节高密度工程复盘结构：
  - **Section 1: The Symptom & Cost（故障现场与真实代价）**：首句直接给出故障影响与实测指标。
  - **Section 2: The Dead Ends（为什么常规修法全败了）**：诚实展示 `.agents/decision.tsv` 中的 `REVERT` 记录，解释为何表面补丁无效。
  - **Section 3: The Structural Fix（状态机与边界重构）**：用真实源码行号指针与最小代码片段展示最终收敛方案。
  - **Section 4: The Verification Script（10行可复现实验）**：提炼一段读者可直接拿走运行的验证命令或检查规则。

- [ ] **Step 4: Fresh Subagent Drafting (全新子 Agent 独立起草)**
  将结构蓝图与证据指针写入 `.agents/handoffs/active-brief.md`，挂载 `unslop-zh-en.md` 与 `sharpen.md`，通过原生 `invoke_subagent` 或 `./scripts/ag-spawn.sh` 拉起全新 `prose-architect` 写入 `.agents/handoffs/output-draft.md`。

- [ ] **Step 5: Prose Compilation Gate (文章静态编译门禁)**
  运行 `python3 scripts/verify-prose.py .agents/handoffs/output-draft.md`。任何违规项必须写入 `active-brief.md` 的 Delta 区块并拉起全新 Worker 修复，直至 `ALL CHECKS GREEN`。

- [ ] **Step 6: Delivery & Ledger Cross-Check (定稿交付与事实核对)**
  主控逐一核对文内数字与 `.agents/decision.tsv` 完全一致后，向用户交付全文并说明应用的核心原则。
