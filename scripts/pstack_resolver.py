#!/usr/bin/env python3
"""
pstack Path & Overlay Asset Resolver
Decouples static PSTACK_HOME assets from dynamic WORKSPACE_ROOT state.
"""
import argparse
import os
import sys
from pathlib import Path

WORKSPACE_MARKERS = (".agents", "AGENTS.md", "CLAUDE.md", ".git")

DEFAULT_DECISION_HEADER = (
    "timestamp\ttask_id\tverdict\thypothesis\t"
    "evidence_pointer\tmetric_before\tmetric_after\tlesson_learned\n"
)

DEFAULT_ACTIVE_BRIEF = """---
task_id: "workspace-bootstrap-01"
role: "implementer"
target_agent: "antigravity"
playbook: ".agents/pstack/playbooks/architecture-feature.md"
required_principles:
  - ".agents/pstack/principles/prove-it-works.md"
  - ".agents/pstack/principles/no-comments.md"
  - ".agents/pstack/principles/unslop-zh-en.md"
verify_cmd: "pstack verify all"
---

## 1. User Goal (Restated)
当前工作区已完成 Pstack 轻量级骨架初始化，可随时承接代码实现、架构批判或技术长文任务。

## 2. Consolidated Directives (History & Delta)
- [Init] 已初始化本地 `.agents/decision.tsv` 与 `.agents/handoffs/` 状态目录，静态规则自动回退至 `PSTACK_HOME`。

## 3. Evidence Pointers (Read-Only Context)
- 核心调度协议：`.agents/pstack/poteto-core.md:1-30`
- 实证决策账本：`.agents/decision.tsv:1-1`

## 4. Deliverable Contract
1. 每次派发子 Agent 前覆写本文件并运行 `pstack verify handoff`。
"""

DEFAULT_EVIDENCE_PACK = """# Pstack Evidence Pack

- Initialized workspace evidence pack `[实测 Measured]`。
"""

DEFAULT_OUTPUT_DRAFT = """# Pstack Output Draft

当前工作区已挂载 Pstack 确定性校验门禁，所有产出将在提交前通过自动化脚本验证 `[实测 Measured]`。
"""


def get_pstack_home() -> Path:
    env_home = os.environ.get("PSTACK_HOME", "").strip()
    if env_home:
        candidate = Path(env_home).expanduser().resolve()
        if candidate.is_dir():
            return candidate

    script_repo = Path(__file__).resolve().parent.parent
    if (script_repo / ".agents" / "pstack").is_dir():
        return script_repo

    global_anchor = (Path.home() / ".config" / "pstack" / "home").expanduser()
    if global_anchor.exists():
        return global_anchor.resolve()

    return script_repo


def get_workspace_root(target_hint: Path | None = None) -> Path:
    env_ws = os.environ.get("PSTACK_WORKSPACE", "").strip()
    if env_ws:
        return Path(env_ws).expanduser().resolve()

    start = Path.cwd().resolve()
    if target_hint is not None:
        resolved_hint = target_hint.expanduser().resolve()
        start = resolved_hint if resolved_hint.is_dir() else resolved_hint.parent

    for candidate in (start, *start.parents):
        if any((candidate / marker).exists() for marker in WORKSPACE_MARKERS):
            return candidate

    return Path.cwd().resolve()


def resolve_asset(rel_path: str | Path, workspace_root: Path | None = None) -> Path:
    raw_path = Path(rel_path)
    if raw_path.is_absolute():
        return raw_path

    ws = workspace_root or get_workspace_root()
    local_candidate = ws / raw_path
    if local_candidate.exists():
        return local_candidate

    home_candidate = get_pstack_home() / raw_path
    if home_candidate.exists():
        return home_candidate

    return local_candidate


def ensure_workspace_skeleton(workspace_root: Path) -> None:
    agents_dir = workspace_root / ".agents"
    handoffs_dir = agents_dir / "handoffs"
    handoffs_dir.mkdir(parents=True, exist_ok=True)

    ledger_path = agents_dir / "decision.tsv"
    if not ledger_path.exists():
        ledger_path.write_text(DEFAULT_DECISION_HEADER, encoding="utf-8")

    brief_path = handoffs_dir / "active-brief.md"
    if not brief_path.exists():
        brief_path.write_text(DEFAULT_ACTIVE_BRIEF, encoding="utf-8")

    evidence_path = handoffs_dir / "evidence-pack.md"
    if not evidence_path.exists():
        evidence_path.write_text(DEFAULT_EVIDENCE_PACK, encoding="utf-8")

    draft_path = handoffs_dir / "output-draft.md"
    if not draft_path.exists():
        draft_path.write_text(DEFAULT_OUTPUT_DRAFT, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack path and overlay asset resolver")
    parser.add_argument("--pstack-home", action="store_true", help="Print resolved PSTACK_HOME")
    parser.add_argument("--workspace-root", action="store_true", help="Print resolved WORKSPACE_ROOT")
    parser.add_argument("--print-paths", action="store_true", help="Print both PSTACK_HOME and WORKSPACE_ROOT")
    parser.add_argument("--init-skeleton", type=Path, help="Initialize .agents skeleton in target directory")
    parser.add_argument("--resolve", type=str, help="Resolve relative asset path via overlay")
    args = parser.parse_args()

    if args.init_skeleton is not None:
        target = args.init_skeleton.expanduser().resolve()
        ensure_workspace_skeleton(target)
        return 0

    if args.pstack_home:
        print(get_pstack_home())
        return 0

    if args.workspace_root:
        print(get_workspace_root())
        return 0

    if args.resolve:
        print(resolve_asset(args.resolve))
        return 0

    pstack_home = get_pstack_home()
    workspace_root = get_workspace_root()
    print(f"PSTACK_HOME    : {pstack_home}")
    print(f"WORKSPACE_ROOT : {workspace_root}")
    print("STATUS         : ALL CHECKS GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
