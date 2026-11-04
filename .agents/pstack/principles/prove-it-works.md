# Principle: Prove It Works & Control Blast Radius

未经运行时验证的代码和未经脚本校验的文章，在 Pstack 中一律视为不存在（Unverified = Broken）。

## 1. 实证四铁律
1. **复现先行（Reproduce Before Touching Code）**：修 Bug 时，在看到稳定的失败输出（报错栈、失败断言或错误返回码）之前，严禁修改任何一行源码。
2. **测试可观测行为而非内部实现（Test Behavior, Not Implementation）**：禁止写一堆 Mock 内部私有函数的脆弱测试。测试必须只绑定输入与可观测的外部输出（返回值、文件落盘、状态码）。
3. **爆炸半径显式审计（Blast Radius Audit）**：修改任何公共函数、协议字段或配置前，先用静态搜索列出所有调用方（Callers）。在提交报告中必须明确回答：“如果这行改动出错，哪条链路会挂？我是如何用真实命令验证它没挂的？”
4. **最小可验证单元（Sequence into Verifiable Units）**：严禁一次性修改 15 个文件后再跑测试。每完成一个独立闭合的数据结构或脚本，立刻运行验证命令并将结果记入 `.agents/decision.tsv`。
