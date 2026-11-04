# Playbook: Interrogate & Arena (对抗审查与多模型竞技场)

启动本剧本时，必须先将以下 5 个步骤原封不动复制到主控 Todo 列表中，按序推进：

- [ ] **Step 1: Strip Author Bias (剥离作者辩解，构建盲审包)**
  将待审查的架构方案、代码 Diff 指针或文章草稿路径写入 `.agents/handoffs/active-brief.md`（`role: "verifier"`）。**严禁在简报中解释“我为什么要这样写”**，只给目标契约与文件路径，让审查者处于零预设冷酷视角。

- [ ] **Step 2: Adversarial Interrogation Dispatch (异构模型对抗挑刺)**
  通过 `./scripts/ag-spawn.sh .agents/handoffs/active-brief.md <codex|claude|opencode>` 拉起异构模型子进程，强制从以下 4 个维度寻找致命缺陷：
  1) **并发与重入（Concurrency & Reentrancy）**：两个进程同时跑这段逻辑会损坏状态吗？
  2) **部分失败与脏状态（Partial Failure）**：第 3 步挂了，前 2 步留下的副作用怎么回滚？
  3) **隐式假设泄漏（Implicit Premise Leak）**：哪个未校验的外部输入会直接击穿边界？
  4) **伪抽象与过度设计（Premature Abstraction）**：哪些代码或段落删掉后系统依然正常工作？

- [ ] **Step 3: Filter Signal from Nitpicks (实证过滤，拒绝表面吹毛求疵)**
  主控审阅盲审报告：直接丢弃纯风格偏好的建议，仅保留能构造出具体失败反例（Counterexample）的缺陷。

- [ ] **Step 4: Clean-Room Remediation (全新子 Agent 靶向修复)**
  将确认成立的反例更新至 `.agents/handoffs/active-brief.md` 的 Delta 区块，拉起全新 Worker 修复并补充回归校验。

- [ ] **Step 5: Log Revert or Keep to Ledger (记录审查结论)**
  将本次盲审抓出的真实漏洞或被推翻的设计记入 `.agents/decision.tsv`，并运行 `python3 scripts/pstack-verify.py all` 确认全绿收尾。
