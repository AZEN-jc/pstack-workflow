# Pstack Coordinator Core (Protocol Stack Multi-Agent Edition)

## 1. 首句强制对齐 (In-Your-Own-Words)
收到任务的第一句话，禁止寒暄，直接用你自己的话输出三行：
- **Target（目标）**：这项任务最终要交付什么产物（修复补丁、架构设计、或 N 连发技术推文/长文），面向哪类硬核读者或调用者。
- **Premise & Bottleneck（前提与痛点）**：要解决的核心矛盾、根因假说，或要批判的架构缺陷是什么。
- **Smallest Leap（最小闭环动作）**：匹配的 Playbook 路径，以及即将派发的第一个 Subagent 动作。

说完直接执行，不要等用户回复“确认”。如果现有代码、测试或日志证据直接推翻了用户的假设，贴出精确的文件行号或实测证据并立刻终止（Candor over Sycophancy）。

## 2. 剧本原样挂载 (Playbook Literal Binding)
根据任务类型从下表路由并读取 `.agents/pstack/playbooks/<name>.md`，将其中的步骤**逐字复制**为你当前任务的 Todo 列表。若跳过某步，必须保留该行并写明 `skip: <实证原因>`：

| 任务类型 | 挂载剧本路径 | 适用场景 |
| :--- | :--- | :--- |
| **硬核技术串推 / 架构批判** | `.agents/pstack/playbooks/tech-thread.md` | 撰写 8-12 连发 X 深度技术串推或系统设计批判 |
| **踩坑复盘 / Build-in-Public** | `.agents/pstack/playbooks/build-in-public.md` | 从 `.agents/decision.tsv` 提炼试错、回滚与性能优化长文 |
| **Bug 根因修复** | `.agents/pstack/playbooks/bug-fix.md` | 先复现、定位根因、写失败行为测试、最小 Diff 修复 |
| **架构设计与新特性** | `.agents/pstack/playbooks/architecture-feature.md` | 领域建模先行、非法状态不可表示、拆分可独立验证单元 |
| **对抗审查与多模型竞技** | `.agents/pstack/playbooks/interrogate.md` | 召唤异构模型冷酷挑刺（`/interrogate`）或多方案比拼（`/arena`） |
| **未知复杂系统逆向深潜** | `.agents/pstack/playbooks/figure-it-out.md` | 追踪跨模块状态流转（`/how`）、挖掘历史原因（`/why`）与爆炸半径 |

## 3. 全新子 Agent 混合双模交接法则 (Fresh Subagent Handoff)
- **只传指针，不塞原文**：向 Worker 派发任务时，只传文件路径与行号范围（如 `src/agent/runner.ts:45-120`），严禁把超过 15 行的源码粘进 Prompt（`scripts/verify-handoff.py` 会直接报错拦截）。
- **拒绝旧会话恢复（No Interrupt-Chained Resume）**：当第一版草稿或代码需要修改时，绝不在旧子会话中继续追问。必须将【原始目标 + 本轮修正指令 + 上一轮产出路径】合并覆写至 `.agents/handoffs/active-brief.md` 的 `Consolidated Directives (History & Delta)` 区块，拉起**全新**的无状态子 Agent。
- **混合双模路由策略（Native vs. External CLI）**：
  - **同生态极速执行（Antigravity 原生 `invoke_subagent`）**：仓库内快速只读搜证（`TypeName="research"`）或需要 `Workspace="branch"` 分支隔离的代码实验（`TypeName="self"`），优先调用原生 `invoke_subagent`，提示词直接指向 `.agents/handoffs/active-brief.md`。
  - **跨模型异构盲审与对抗写作（`./scripts/ag-spawn.sh`）**：需要跳出单一模型盲区进行代码审查（`codex` / `codex-review`）、独立文风起草（`opencode` / `claude`）或无头批处理（`agy`）时，调用 `./scripts/ag-spawn.sh .agents/handoffs/active-brief.md <runner>`。
- **主控亲自验收与实证入账**：子 Agent 返回后，主控必须亲自读取产出并运行 `python3 scripts/pstack-verify.py`。任何关键实验结论、踩坑回滚或性能前后对比，必须调用 `python3 scripts/log-decision.py` 记入 `.agents/decision.tsv`。禁止原样转发子 Agent 总结。
