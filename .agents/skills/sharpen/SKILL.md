---
name: sharpen
description: "Make a clear task deeper (not bigger), add top-expert steps, rawest materials, specific methods, and objective verification, then rewrite and stage the prompt. Use for /sharpen."
disable-model-invocation: true
---

# /sharpen — 任务深水区提纯（加深不加大 · 不直接干活）

我要的是这个任务的**更深版本（Deeper），绝不是更大版本（Not Bigger，严禁扩充需求范围或堆砌新功能）**。
**严格红线**：严禁修改任何业务源码、严禁覆写 `.agents/handoffs/active-brief.md`、严禁直接派发实现或修改工作树代码。

## 执行步骤

在重写 Prompt 之前，先结合当前仓库真实结构与工具链（可只读查看关键模块、`file:line#symbol` 或运行只读的 `pstack onboard --detect` 识别现有测试与门禁命令），逐项回答以下四件事：

1. **顶尖专家的暗步（Expert Unasked Steps）**：
   该领域的顶尖工程师拿到这个任务，会默认多做哪几步关键动作，而我现在的描述里漏掉了？（聚焦根因隔离、不变量建模、并发/边界退化防护，而非加功能）。
2. **最原始的一手材料（Rawest Material）**：
   他们会直接从什么最底层的一手证据切入（如 AST、协议字节流、Git 历史演进、火焰图/Trace、真实失败样本、`file:line#symbol`），而不是依赖已被二手消化的摘要或猜测？
3. **具体方法与工具（Specific Methods & Tools）**：
   他们会动用哪些具体的分析方法、命令行工具、构造不变量的手段或基准验证方法？
4. **独立于你我的客观证明（Objective Proof）**：
   除了你口头宣称“改好了”和我肉眼审查之外，什么客观机器证据能证明结果绝对正确？（优先对齐本仓库真实可执行的 `verify_cmd`、失败先行的行为回归测试、属性测试或可复现的 Gate 4 指标对比）。

## 输出重写与非侵入暂存

完成以上四点剖析后：

1. **重写深水区 Prompt**：将我的需求重写为一份直接要求编码 Agent 做到上述四点的紧凑 Prompt：
   - 凡是能通过小实验/原型对比定夺的技术分歧，要求 Agent 先做最小原型实验并用实测观测数据推荐方案；
   - 凡是实验无法定夺的产品取向或偏好权衡，明确留给我来拍板。
2. **暂存草稿（不碰 `active-brief.md`）**：
   将重写后的纯 Prompt 正文写入 `.agents/handoffs/sharpened-prompt.md`（若当前环境无写权限则仅在代码块输出），并在回复末尾附上两条待命指令供我确认后手动执行：
   - 仅生成正式建单：`pstack route --from-sharpen`
   - 建单并启动自愈执行：`pstack run --from-sharpen --max-rework 2`
