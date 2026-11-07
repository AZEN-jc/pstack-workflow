#!/usr/bin/env python3
"""
pstack Onboarding & Commit-to-Thread Brief Generator
Usage:
  python3 scripts/pstack-onboard.py --detect
  python3 scripts/pstack-onboard.py --to-thread [--commits 3] [--playbook tech-thread|build-in-public] [--output <path>]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from pstack_resolver import ensure_workspace_skeleton, get_workspace_root, resolve_asset


def detect_verify_cmd(workspace_root: Path) -> str:
    pkg_json = workspace_root / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            test_script = data.get("scripts", {}).get("test", "")
            if test_script and "no test specified" not in test_script:
                return "npm test"
        except ValueError:
            return "npm test"

    if (workspace_root / "pyproject.toml").exists() or (workspace_root / "pytest.ini").exists():
        return "pytest -q"
    if (workspace_root / "Cargo.toml").exists():
        return "cargo test --quiet"
    if (workspace_root / "go.mod").exists():
        return "go test ./..."
    if (workspace_root / "Makefile").exists():
        return "make test"
    if (workspace_root / "scripts" / "verify-handoff.py").exists():
        return "python3 scripts/verify-handoff.py && python3 scripts/verify-code-slop.py scripts"
    if (workspace_root / ".git").exists():
        return "git status -s"
    return "python3 -m unittest"


def collect_recent_commits(workspace_root: Path, count: int) -> tuple[list[str], list[str]]:
    log_proc = subprocess.run(
        ["git", "log", f"-n{count}", "--pretty=format:%h %s"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    commits = [ln.strip() for ln in log_proc.stdout.splitlines() if ln.strip()]

    files_proc = subprocess.run(
        ["git", "log", f"-n{count}", "--pretty=format:", "--name-only"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    pointers: list[str] = []
    seen: set[str] = set()
    for raw in files_proc.stdout.splitlines():
        rel = raw.strip()
        if not rel or rel in seen:
            continue
        candidate = workspace_root / rel
        if candidate.is_file():
            seen.add(rel)
            line_count = min(max(len(candidate.read_text(encoding="utf-8", errors="ignore").splitlines()), 1), 60)
            pointers.append(f"{rel}:1-{line_count}")
        if len(pointers) >= 6:
            break

    if not pointers:
        ledger = resolve_asset(".agents/decision.tsv", workspace_root)
        if ledger.exists():
            pointers.append(".agents/decision.tsv:1-5")
    return commits, pointers


def collect_recent_decisions(workspace_root: Path, limit: int = 3) -> list[str]:
    ledger = workspace_root / ".agents" / "decision.tsv"
    if not ledger.exists():
        return []
    lines = [ln.strip() for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) <= 1:
        return []
    summaries: list[str] = []
    for row_str in lines[1:][-limit:]:
        cols = row_str.split("\t")
        if len(cols) >= 8:
            summaries.append(f"[{cols[2]} | {cols[1]}] {cols[5]} -> {cols[6]} ({cols[7]})")
    return summaries


def generate_thread_brief(
    workspace_root: Path,
    commits_count: int = 3,
    playbook_key: str = "tech-thread",
    output_path: Path | None = None,
) -> Path:
    ensure_workspace_skeleton(workspace_root)
    commits, pointers = collect_recent_commits(workspace_root, commits_count)
    decisions = collect_recent_decisions(workspace_root, 3)

    pb_map = {
        "tech-thread": ".agents/pstack/playbooks/tech-thread.md",
        "build-in-public": ".agents/pstack/playbooks/build-in-public.md",
    }
    pb_path = pb_map.get(playbook_key, pb_map["tech-thread"])

    commit_bullets = "\n".join(f"- [Commit] {c}" for c in commits) or "- [Commit] 近期工作区增量提交"
    decision_bullets = "\n".join(f"- [Decision] {d}" for d in decisions) or "- [Decision] 见 `.agents/decision.tsv`"
    pointer_bullets = "\n".join(f"- `{p}`" for p in pointers)

    brief_content = f"""---
task_id: "onboard-{playbook_key}-01"
role: "prose-architect"
target_agent: "opencode"
playbook: "{pb_path}"
required_principles:
  - ".agents/pstack/principles/unslop-zh-en.md"
  - ".agents/pstack/principles/prove-it-works.md"
verify_cmd: "pstack verify prose"
---

## 1. User Goal (Restated)
基于当前仓库最近 {commits_count} 次代码提交与 `.agents/decision.tsv` 实证记录，起草一篇零 AI 腔的硬核技术演进推文并写入 `.agents/handoffs/output-draft.md`。

## 2. Consolidated Directives (History & Delta)
{commit_bullets}
{decision_bullets}

## 3. Evidence Pointers (Read-Only Context)
{pointer_bullets}
- `.agents/decision.tsv:1-8`

## 4. Deliverable Contract
1. 在 `.agents/handoffs/output-draft.md` 顶部写入 3 行内 `> [Builder Restate]` 复述头。
2. 完成正文后运行 `pstack verify prose` 并确保输出 `ALL CHECKS GREEN`。
"""
    target = output_path or (workspace_root / ".agents" / "handoffs" / "active-brief.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(brief_content, encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack project onboarding and thread brief generator")
    parser.add_argument("--detect", action="store_true", help="Detect recommended verify_cmd for current repo")
    parser.add_argument("--to-thread", action="store_true", help="Generate active-brief.md from recent git commits")
    parser.add_argument("--commits", type=int, default=3, help="Number of recent commits to extract")
    parser.add_argument(
        "--playbook",
        choices=("tech-thread", "build-in-public"),
        default="tech-thread",
        help="Target prose playbook",
    )
    parser.add_argument("--output", type=Path, help="Custom output path for generated brief")
    args = parser.parse_args()

    workspace_root = get_workspace_root()
    if args.to_thread:
        out = generate_thread_brief(workspace_root, args.commits, args.playbook, args.output)
        print(f"[OK] Generated thread handoff brief -> {out}")
        return 0

    cmd = detect_verify_cmd(workspace_root)
    print(cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
