# Playbook: Figure-It-Out (复杂未知系统逆向与深潜取证)

启动本剧本时，必须先将以下 5 个步骤原封不动复制到主控 Todo 列表中，按序推进：

- [ ] **Step 1: Formulate Falsifiable Hypotheses (建立可证伪假说列表)**
  面对未知黑盒行为、跨进程卡死或诡异性能退化，先列出 2-3 个互斥且可通过实验证伪的假说，明确每个假说需要观测的证据指标。

- [ ] **Step 2: Parallel Read-Only Swarm Sweep (并行只读子 Agent 扫掠取证)**
  派发只读 `investigator` 子 Agent 追踪完整调用链（精确到 `file:start-end`），绘制数据流与状态变迁图，写入 `.agents/handoffs/evidence-pack.md`。

- [ ] **Step 3: Prune Hypotheses by Evidence (实证剪枝)**
  对照 `.agents/handoffs/evidence-pack.md` 中的日志、Git Blame 历史（`/why`）与运行时观测，逐一排除不成立的假说。若所有假说均被证伪，基于新观测数据重立假说。

- [ ] **Step 4: Distill Minimal Mental Model (提炼最小心智模型与验证脚本)**
  将复杂的子系统交互浓缩为一张 ASCII 状态机/时序图，并提供一条可随时复验该行为的最小命令。

- [ ] **Step 5: Persist to Decision Ledger & Verify (实证归档与门禁校验)**
  将最终确认的系统机制与证据指针记入 `.agents/decision.tsv`，若产出包含分析报告则通过 `python3 scripts/verify-prose.py` 校验后交付。
