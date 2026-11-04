# Playbook: Architecture & Feature Development (领域建模与最小 Diff 开发)

启动本剧本时，必须先将以下 6 个步骤原封不动复制到主控 Todo 列表中，按序推进：

- [ ] **Step 1: Domain & Invariant Modeling (领域建模与非法状态不可表示)**
  动工前先定义核心数据结构、状态机迁移表与边界契约。检查是否存在“两个布尔值组合出非法状态”的脆弱设计，通过类型系统或 Schema 将非法状态在入口处直接拦截。

- [ ] **Step 2: Blast Radius & Boundary Mapping (爆炸半径与依赖边界测绘)**
  派发 `investigator` 扫描现有调用链，明确新特性触碰哪些现有模块，输出文件行号指针清单至 `.agents/handoffs/evidence-pack.md`。

- [ ] **Step 3: Sequence into Verifiable Units (拆分为可独立验证的最小单元)**
  将特性拆解为 2-4 个可独立运行验证的微小步骤（如：Unit 1 数据结构与校验器 -> Unit 2 核心状态转换 -> Unit 3 CLI/接口挂载）。每个单元必须自带一条一行命令即可跑通的 `verify_cmd`。

- [ ] **Step 4: Stateless Worker Execution (按单元拉起全新子 Agent 实现)**
  每次将一个单元的指针契约写入 `.agents/handoffs/active-brief.md`，派发全新子 Agent 实现并运行该单元的 `verify_cmd`。

- [ ] **Step 5: Comment Sicko & Unslop Gate (代码与文档双重静态门禁)**
  对新增代码运行 `python3 scripts/verify-code-slop.py`，对新增文档或 PR 描述运行 `python3 scripts/verify-prose.py`，确保零废话注释与零 AI 腔。

- [ ] **Step 6: Empirical Proof & Ledger Record (端到端实证与入账)**
  运行真实端到端场景验证产出，并将架构取舍与实测指标通过 `python3 scripts/log-decision.py` 记录至 `.agents/decision.tsv`。
