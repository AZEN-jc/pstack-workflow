# Playbook: Bug Fix (复现先行与根因修复)

启动本剧本时，必须先将以下 6 个步骤原封不动复制到主控 Todo 列表中，按序推进：

- [ ] **Step 1: Reproduce First (强制先复现)**
  读取 `.agents/pstack/principles/prove-it-works.md`。派发只读或沙箱子 Agent 构造最小复现命令。在亲眼看到确定性的失败输出（报错栈、错误状态码或错误数据）前，**严禁修改任何业务源码**。将复现命令与报错现场写入 `.agents/handoffs/evidence-pack.md`。

- [ ] **Step 2: Isolate Root Cause vs. Symptom (根因剥离)**
  顺着报错点向上游追溯数据流与状态迁移，定位状态最早被污染的边界。结合 `.agents/pstack/principles/attack-the-premise.md`，拒绝任何“加个空值判断 / 吞掉异常 / 盲目调大超时”的表面补丁。

- [ ] **Step 3: Write Failing Behavioral Test (编写失败行为测试)**
  先写一个只测外部可观测行为的自动化测试用例，运行测试确认它因该 Bug 而稳定失败（Red）。

- [ ] **Step 4: Smallest Diff Implementation (全新 Worker 最小侵入修复)**
  将根因位置指针、复现测试命令及 `.agents/pstack/principles/no-comments.md` 写入 `.agents/handoffs/active-brief.md`，拉起全新 Worker 实施最小 Diff 修复，使失败测试转绿（Green）。

- [ ] **Step 5: Blast Radius & Comment Sicko Gate (爆炸半径与代码去噪门禁)**
  运行全量相关测试，并对修改过的文件执行 `python3 scripts/verify-code-slop.py <modified_files>`。若检测到废话注释、空 catch 或未声明的副作用，打回重写直至 `ALL CHECKS GREEN`。

- [ ] **Step 6: Commit to Decision Ledger (实证入账)**
  调用 `python3 scripts/log-decision.py` 将本次 Bug 的根因、代码指针及修复前后表现记入 `.agents/decision.tsv`（`verdict=ROOT_CAUSE`），为后续技术推文沉淀一手素材。
