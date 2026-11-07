---
task_id: "pstack-v2-readme-default-en-02"
role: "implementer"
target_agent: "antigravity"
playbook: ".agents/pstack/playbooks/architecture-feature.md"
required_principles:
  - ".agents/pstack/principles/prove-it-works.md"
  - ".agents/pstack/principles/no-comments.md"
  - ".agents/pstack/principles/unslop-zh-en.md"
verify_cmd: "python3 scripts/pstack-verify.py all"
---

## 1. User Goal (Restated)
将仓库默认主文档 `README.md` 设为纯英文版（全英 README），并将中文版设为 `README_ZH.md`，支持通过顶部点击“简体中文”无缝切换至中文版，在中文版点击“English”可切换回主英文版。

## 2. Consolidated Directives (History & Delta)
- [README.md] 替换为纯英文版内容，顶部提供语言切换：
  `<b>English</b> | <b><a href="./README_ZH.md">简体中文</a></b>`
- [README_ZH.md] 放置中文版内容，顶部提供语言切换：
  `<b><a href="./README.md">English</a></b> | <b>简体中文</b>`
- [Cleanup] 移除冗余的 `README_EN.md`（因主 `README.md` 已是全英版本）。
- [Gate Verification] 确保 `verify-prose.py README.md` 和 `verify-prose.py README_ZH.md` 及 `pstack-verify.py all` 100% 绿灯。

## 3. Evidence Pointers (Read-Only Context)
- 现存中文母版：`README_ZH.md:1-198`
- 现存英文主档：`README.md:1-198`
- 散文门禁检查脚本：`scripts/verify-prose.py:1-155`
- 门禁总控调度脚本：`scripts/pstack-verify.py:1-90`

## 4. Deliverable Contract
1. 默认 `README.md` 为纯英文，内含指向 `README_ZH.md` 的跳转链接。
2. `README_ZH.md` 为中文版，内含指向 `README.md` 的跳转链接。
3. `python3 scripts/verify-prose.py README.md` 返回 0。
4. `python3 scripts/verify-prose.py README_ZH.md` 返回 0。
5. `python3 scripts/pstack-verify.py all` 返回 0。
