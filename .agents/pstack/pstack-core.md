# Pstack v2.0 Coordinator Core (Tier 0: <= 48 Lines)

## 1. 首句三行对齐 (In-Your-Own-Words) & Tier 0/1/2 上下文预算
收到任务禁止寒暄，首句必须用你自己的话输出三行并立即执行（若现有证据推翻用户假设，贴出 `file:line` 立刻终止）：
- **Target（目标）**：交付产物（修复补丁、架构设计、或 N 连发技术推文/长文）及目标硬核受众。
- **Premise & Bottleneck（前提与痛点）**：要解决的核心矛盾、根因假说，或要批判的架构缺陷。
- **Smallest Leap（最小闭环动作）**：匹配的 Playbook 路径，以及首个 Builder / Subagent 动作。
- **三级上下文预算**：Tier 0 常驻本文件（≤48行）；Tier 1 单轮交接（`active-brief.md` 代码块≤15行 + `evidence-pack.md` 静态指针与≤15行运行时摘要）；Tier 2 离线脚本（`correct/pause/pickup/onboard` 平时 0 Token，触发输出≤20行）。

## 2. 剧本原样挂载 (Playbook Literal Binding)
从下表读取 `.agents/pstack/playbooks/<name>.md`，将其步骤**逐字复制**为 Todo 列表（跳过某步须保留并写明 `skip: <实证原因>`）：

| 任务类型 | 挂载剧本路径 | 适用场景 |
| :--- | :--- | :--- |
| **硬核技术串推 / 架构批判** | `.agents/pstack/playbooks/tech-thread.md` | 撰写 8-12 连发 X 深度技术串推或系统设计批判 |
| **踩坑复盘 / Build-in-Public** | `.agents/pstack/playbooks/build-in-public.md` | 从 `.agents/decision.tsv` 提炼试错、回滚与性能优化长文 |
| **Bug 根因修复** | `.agents/pstack/playbooks/bug-fix.md` | 先复现、定位根因、写失败行为测试、最小 Diff 修复 |
| **架构设计与新特性** | `.agents/pstack/playbooks/architecture-feature.md` | 领域建模先行、非法状态不可表示、拆分可独立验证单元 |
| **对抗审查与多模型竞技** | `.agents/pstack/playbooks/interrogate.md` | 召唤异构模型冷酷挑刺（`/interrogate`）或多方案比拼（`/arena`） |
| **未知复杂系统逆向深潜** | `.agents/pstack/playbooks/figure-it-out.md` | 追踪跨模块状态流转（`/how`）、挖掘历史原因（`/why`）与爆炸半径 |

## 3. 桌面端双 Tab 隔离与全新子 Agent 交接 (Builder + Independent Verifier)
- **只传指针、拒绝旧会话恢复**：严禁粘贴 >15 行源码。需修改时必须将【原始目标 + 本轮修正 + 上轮指针】合并覆写至 `.agents/handoffs/active-brief.md`，拉起**全新**无状态会话。
- **桌面端同宿主双 Tab 闭环（OpenCode / Codex / WorkBuddy / Pi / Claude / Cursor / AGY）**：
  1. **Tab 1 Builder（`/pstack-build`）**：读取 `active-brief.md`，在 `output-draft.md` 顶部前 6 行写入 3 行内 `> [Builder Restate]`，执行实现后运行 `pstack verify all`（自动触发 Gate 4 执行 `verify_cmd` 并将 SHA256 与末尾 10 行写入 `evidence-pack.md`）。
  2. **Tab 2 Independent Verifier（新建空白 Tab 运行 `/pstack-verify`）**：运行 `pstack verify prep-verifier` 只读审查 `active-brief.md`、`evidence-pack.md` 与 `git diff --stat`，按 `ACT_ON / CONSIDER / NOTED / DISMISSED` 四级分类写入 `.agents/handoffs/verifier-verdict.md` 并标注 `VERDICT: PASS | REJECT`，最后执行 `pstack verify verdict` 自动导出剥离复述头的干净定稿 `output-final.md`。
- **零 Token 辅助工具链**：入职探测与推文提炼用 `pstack onboard (--detect | --to-thread)`；五层纠错下沉用 `pstack correct (--scan | --code-rule | --prose-ban)`；跨天 ≤20 行断点续传用 `pstack pause` 与 `pstack pickup`。
