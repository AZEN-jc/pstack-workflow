# Pstack v3.0 架构升级规范：通用 Agent 执行、任务自动路由与 Worktree 隔离调度

> 调用者在桌面端同宿主新建两个空白标签页，即可完成生产实现与独立对抗验收 `[离线实测 Offline-Measured]`。
> 常驻路由内核严格锁定在 48 行以内，彻底杜绝系统提示词挤占业务窗口 `[离线实测 Offline-Measured]`。
> 离线辅助工具平时消耗零上下文，触发时仅输出 20 行以内的高信噪比摘要 `[推导 Inferred]`。

---

## 1. 升级目标与受众感知 (Impact First)

工程团队在日常使用多智能体协作时，无需再把终端输出人肉复制到聊天窗口。
Pstack v3.0 将协议栈拆分为三级上下文预算与四重机械门禁 `[离线实测 Offline-Measured]`。

| 架构维度 | 早期版本状态 | Pstack v3.0 生产终版 | 实测收益 `[离线实测 Offline-Measured]` |
| :--- | :--- | :--- | :--- |
| **常驻上下文预算** | 无硬性行数上限 | **Tier 0 锁定 ≤ 48 行** (`.agents/pstack/pstack-core.md`) | 常驻体积压缩至约 450 Tokens |
| **桌面端角色隔离** | 依赖外部命令行切换 | **同宿主双 Tab 闭环** (`/pstack-build` + `/pstack-verify`) | 零人肉复制完成跨会话盲审 |
| **验证门禁深度** | 三重静态文本与注释检查 | **四重门禁** (新增 Gate 4 自动执行 `verify_cmd` 落盘 SHA256) | 杜绝模型口头谎报测试通过 |
| **本机宿主覆盖** | 6 路宿主挂载 | **8 路本机宿主全绿** (新增 `Pi` 与 `~/.agents/skills`) | 一次安装覆盖本机全部入口 |
| **离线辅助工具** | 仅支持手工记账与拉黑 | **新增 `correct / pause / pickup / onboard` 四大工具** | 约 150 Tokens 瞬间恢复跨天进度 |

---

## 2. 三级上下文预算模型 (Tier 0 / Tier 1 / Tier 2)

- **Tier 0 常驻路由层 (`≤ 48 行`)**：主控每次启动仅读取 `.agents/pstack/pstack-core.md`，完成首句三行对齐与剧本路由。
- **Tier 1 单轮交接层 (`≤ 15 行代码块`)**：`.agents/handoffs/active-brief.md` 仅传文件行号指针，`.agents/handoffs/evidence-pack.md` 采用静态证据与运行时摘要双区合并 `[离线实测 Offline-Measured]`。
- **Tier 2 零 Token 离线脚本层 (`≤ 20 行输出`)**：`pstack correct`、`pstack pause`、`pstack pickup` 与 `pstack onboard` 平时不占任何上下文，按需调用。

---

## 3. 桌面端同宿主双 Tab 零复制闭环 (Builder + Verifier)

```text
[Tab 1: Builder (/pstack-build)]
   | 1. 在 output-draft.md 顶部写入 3 行 > [Builder Restate]
   | 2. 完成代码或长文后运行 pstack verify all (自动执行 Gate 4 verify_cmd)
   v
[.agents/handoffs/evidence-pack.md] (追加 ExitCode + 12位SHA256 + 末尾10行)
   |
   | 新建同宿主空白 Tab 2 输入 /pstack-verify
   v
[Tab 2: Independent Verifier (/pstack-verify)]
   | 1. 运行 pstack verify prep-verifier --blind 只读提取 ≤25 行盲审包
   | 2. 将 ACT_ON / CONSIDER / NOTED / DISMISSED 四级裁决写入 verifier-verdict.md
   | 3. 运行 pstack verify verdict 校验通过并自动剥离复述头导出 output-final.md
```

- **作用域隔离的复述头校验**：`scripts/verify-prose.py` 仅对 `output-draft.md` 强制要求前 6 行包含 `> [Builder Restate]`，不污染 `README.md` 等普通文档 `[离线实测 Offline-Measured]`。
- **干净定稿自动导出**：当 `pstack verify verdict` 校验 `VERDICT: PASS` 通过后，系统自动剥离顶部复述块并生成 `.agents/handoffs/output-final.md` `[沙箱模拟 Sim-Verified]`。

---

## 4. 四大零 Token 辅助工具链 (Offline Tooling)

```bash
# 1. 入职探测：自动识别当前仓库的轻量非递归验证命令
pstack onboard --detect

# 2. 推文提炼：从最近 3 次 Git Commit 与 decision.tsv 自动生成推文交接单
pstack onboard --to-thread --commits 3 --playbook tech-thread

# 3. 五层纠错：扫描高频 REVERT 教训并晋升为自定义代码正则或散文禁令
pstack correct --scan
pstack correct --code-rule "^\s*console\.log\(" "禁止遗留调试 console.log"
pstack correct --prose-ban "心智负担"

# 4. 断点续传：生成并读取严格 ≤ 20 行的跨窗口快照 (.agents/handoffs/session-snapshot.md)
pstack pause "v3.0 upgrade complete"
pstack pickup

# 5. 远程同步：自动检查 GitHub 远端更新并全量刷新本机 8 路宿主挂载
pstack update --check
pstack update

# 6. 路由调度与基准测试 (v3.0 Orchestration & Harness)
pstack test
pstack bench
pstack verify handoff --fix
```

---

## 5. 端到端验收契约 (Deliverable Verification)

在仓库根目录依次执行以下 7 条命令，返回码均为 `0` 即代表 v3.0 升级完备 `[离线实测 Offline-Measured]`：

```bash
./scripts/bootstrap-repo.sh --global && pstack status
wc -l .agents/pstack/pstack-core.md
pstack test && pstack bench
pstack pause "v3.0 upgrade complete" && pstack pickup
pstack correct --scan && pstack onboard --detect
pstack verify handoff --fix && pstack verify all && pstack verify prep-verifier --blind && pstack verify verdict
python3 scripts/verify-prose.py README.md && python3 scripts/verify-prose.py README_ZH.md && python3 scripts/verify-prose.py UPGRADE_V2.md && python3 scripts/verify-prose.py benchmarks/latest-report.md
```
