# Playbook: Tech-Thread & Architecture Critique (技术串推与架构深潜)

启动本剧本时，必须先将以下 6 个步骤原封不动复制到主控 Todo 列表中，按序推进：

- [ ] **Step 1: Evidence Sweep (只读实证搜集)**
  派发一个只读 `investigator` 子 Agent，扫描代码库、`.agents/decision.tsv`、Git 历史或报错日志。找出：
  1) 至少 1 个具体的反直觉现象或失败模式（精确到函数名、状态迁移或协议字段）；
  2) 至少 2 组前后对比数据或具体报错现场。
  产出物写入 `.agents/handoffs/evidence-pack.md`。若没有找到硬核证据，直接停下向用户索取，严禁无米之炊。

- [ ] **Step 2: Sharpen the Thesis (专家透镜深化立意)**
  主控读取 `.agents/pstack/principles/sharpen.md` 与 `.agents/handoffs/evidence-pack.md`。回答三个问题：
  1) 普通开发者对这个问题的表面认知（Strawman）是什么？
  2) 真正的系统根因（Root Cause，而非症状）在架构的哪一层？
  3) 读者读完后，明天就能直接抄走的一个结构化机制（Lever / Script / Rule）是什么？
  将这三点浓缩为 1 句话的核心论点（Thesis）。

- [ ] **Step 3: Architecture & Spine Mapping (骨架排布)**
  构建 N 连推（默认 6-8 推）或长文分节大纲，每推/每节只承载 **1 个核心认知增量**：
  - **1/N (The Hook & Verdict)**：第一句直接抛出反直觉结论与实证结果（禁止用“大家好，今天聊聊…”开篇）。点明这对每天写代码的工程师意味着什么。
  - **2/N (The Failure Mode)**：展示真实踩坑现场或普遍失效的做法（附代码片段/日志指针）。
  - **3/N - 5/N (First-Principles Anatomy)**：顺着数据流或状态机拆解根因。使用 ASCII 架构图或紧凑对比表展示“脆弱设计 vs 收敛设计”的差异。
  - **6/N - 7/N (Build the Lever)**：给出你的工程级解法（如一行 Verify 脚本、状态机改造、协议字段设计），展示实测收益。
  - **8/N (The Meta Rule)**：升华一条可跨项目复用的设计公理（如 `Your codebase is memory`），干脆收尾。

- [ ] **Step 4: Clean-Room Drafting (全新子 Agent 撰写初稿)**
  将大纲、`.agents/handoffs/evidence-pack.md` 指针以及 `.agents/pstack/principles/unslop-zh-en.md` 打包写入 `.agents/handoffs/active-brief.md`，拉起一个全新的高推理模型子 Agent（`prose-architect`）撰写正文至 `.agents/handoffs/output-draft.md`。要求在起草第一遍时就严格遵守 Unslop 铁律，不依赖事后洗稿。

- [ ] **Step 5: Automated Unslop & Fact Gate (自动化消肿与事实门禁)**
  对 `.agents/handoffs/output-draft.md` 运行 `python3 scripts/verify-prose.py .agents/handoffs/output-draft.md`。
  - 如果报错（检测到破折号、句中冒号、AI 套话、超长句、未标注来源的断言），将该报错信息追加进 `.agents/handoffs/active-brief.md`，拉起全新子 Agent 重写违规段落，直到脚本输出 `ALL CHECKS GREEN`。

- [ ] **Step 6: Final Delivery & Principle Citation (交付与原则归因)**
  主控向用户输出最终定稿，并在末尾用 2-3 句话说明：本次创作具体应用了哪条 Principle，它砍掉了哪个原本平庸的表达或结构。
