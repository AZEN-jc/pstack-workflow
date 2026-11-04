# Antigravity Pstack Directives
1. 收到任何架构剖析、代码实现、Bug 修复或技术推文/长文创作任务，必须首先读取 `.agents/pstack/poteto-core.md`（轻量工作区直接读取 `~/.config/pstack/home/.agents/pstack/poteto-core.md`）。
2. 严禁在主线程直接生成长篇初稿或全量扫描大文件；必须写入 `.agents/handoffs/active-brief.md` 并通过原生 `invoke_subagent`、`pstack spawn` 或 `./scripts/ag-spawn.sh` 派发全新子 Agent。
3. 任何代码或文字产出交付前，必须通过 `pstack verify all`（或 `python3 scripts/pstack-verify.py all`）门禁校验，返回码非 0 严禁提交。
