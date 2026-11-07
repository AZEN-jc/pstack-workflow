#!/usr/bin/env python3
"""
pstack Cross-Session <= 20 Line Snapshot CLI (pause & pickup)
Usage:
  python3 scripts/pstack-session.py pause ["<progress_note>"]
  python3 scripts/pstack-session.py pickup
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from pstack_resolver import ensure_workspace_skeleton, get_workspace_root, resolve_asset


def read_git_summary(workspace_root: Path) -> tuple[str, str, str]:
    branch_proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "untracked"

    status_proc = subprocess.run(
        ["git", "status", "-s"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    status_lines = [ln.strip() for ln in status_proc.stdout.splitlines() if ln.strip()]
    dirty_count = len(status_lines)
    modified_files = ", ".join(ln.split()[-1] for ln in status_lines[:4])
    if dirty_count > 4:
        modified_files += f" (+{dirty_count - 4} more)"
    if not modified_files:
        modified_files = "clean working tree"
    return branch, f"{dirty_count} changed files", modified_files


def read_brief_meta(workspace_root: Path) -> tuple[str, str, str]:
    brief = resolve_asset(".agents/handoffs/active-brief.md", workspace_root)
    if not brief.exists():
        return "none", "none", "pstack verify all"
    raw = brief.read_text(encoding="utf-8")
    tid = re.search(r'^task_id:\s*["\']?([^"\'\n]+)["\']?', raw, re.MULTILINE)
    role = re.search(r'^role:\s*["\']?([^"\'\n]+)["\']?', raw, re.MULTILINE)
    vcmd = re.search(r"^verify_cmd:\s*(.+)$", raw, re.MULTILINE)
    vcmd_val = vcmd.group(1).strip().strip('"').strip("'") if vcmd else "pstack verify all"
    return (
        tid.group(1).strip() if tid else "unknown",
        role.group(1).strip() if role else "implementer",
        vcmd_val,
    )


def read_last_decisions(workspace_root: Path, count: int = 3) -> list[str]:
    ledger = resolve_asset(".agents/decision.tsv", workspace_root)
    if not ledger.exists():
        return ["  - (no decision records)"]
    lines = [ln.strip() for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) <= 1:
        return ["  - (decision.tsv header only)"]
    items: list[str] = []
    for row_str in lines[1:][-count:]:
        cols = row_str.split("\t")
        if len(cols) >= 8:
            items.append(f"  - [{cols[2]}] `{cols[1]}`: {cols[6][:36]} ({cols[4]})")
    return items or ["  - (no decision records)"]


def read_last_spawn_status(workspace_root: Path) -> str | None:
    logs_dir = workspace_root / ".agents" / "handoffs" / "logs"
    if not logs_dir.is_dir():
        return None

    status_json = logs_dir / "last-spawn-status.json"
    if status_json.exists():
        try:
            data = json.loads(status_json.read_text(encoding="utf-8"))
            runner = data.get("runner", "unknown")
            exit_code = int(data.get("exit_code", 0))
            log_rel = data.get("log_file", ".agents/handoffs/logs/")
            tail = str(data.get("tail", "")).strip()[:48]
            label = "FAILED" if exit_code != 0 else "OK"
            tail_suffix = f" ({tail})" if tail else ""
            return f"- **Last Spawn Status**: `{label} (runner={runner}, exit={exit_code})` -> `{log_rel}`{tail_suffix}"
        except (ValueError, OSError):
            return None

    log_files = sorted(logs_dir.glob("spawn-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        return None

    latest = log_files[0]
    log_rel = f".agents/handoffs/logs/{latest.name}"
    lines = [ln.strip() for ln in latest.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    tail = lines[-1][:48] if lines else "empty"
    joined_tail = "\n".join(lines[-5:]).upper()
    is_fail = any(tok in joined_tail for tok in ("FAIL", "ERROR", "TIMEOUT", "CRASH", "EXIT="))
    label = "FAILED" if is_fail else "LOGGED"
    return f"- **Last Spawn Status**: `{label}` -> `{log_rel}` ({tail})"


def generate_snapshot(workspace_root: Path, note: str = "") -> Path:
    ensure_workspace_skeleton(workspace_root)
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    branch, status_summary, modified_files = read_git_summary(workspace_root)
    task_id, role, verify_cmd = read_brief_meta(workspace_root)
    decisions = read_last_decisions(workspace_root, 3)
    spawn_line = read_last_spawn_status(workspace_root)
    clean_note = note.strip() or "Ready for stateless pickup (`[实测 Measured]`)"

    snapshot_lines = [
        f"# Pstack Session Snapshot ({ts})",
        f"- **Note**: {clean_note}",
        f"- **Workspace & Branch**: `{workspace_root.name}` on `{branch}` ({status_summary})",
        f"- **Touched Pointers**: `{modified_files}`",
        f"- **Active Brief**: `task_id={task_id}` | `role={role}` | `verify_cmd={verify_cmd}`",
    ]
    if spawn_line:
        snapshot_lines.append(spawn_line)
    snapshot_lines.extend(
        [
            "- **Recent Empirical Decisions (`.agents/decision.tsv`)**:",
            *decisions[:3],
            "- **Resume Action**: Read `.agents/handoffs/active-brief.md` and run `pstack verify all`.",
        ]
    )
    bounded = "\n".join(snapshot_lines[:20]) + "\n"
    snap_path = workspace_root / ".agents" / "handoffs" / "session-snapshot.md"
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(bounded, encoding="utf-8")
    return snap_path


def main() -> int:
    workspace_root = get_workspace_root()
    action = sys.argv[1] if len(sys.argv) > 1 else "pickup"

    if action == "pause":
        note = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        snap_path = generate_snapshot(workspace_root, note)
        line_count = len(snap_path.read_text(encoding="utf-8").splitlines())
        print(f"[OK] Saved session snapshot ({line_count}/20 lines) -> {snap_path}")
        return 0

    if action == "pickup":
        snap_path = workspace_root / ".agents" / "handoffs" / "session-snapshot.md"
        if not snap_path.exists():
            snap_path = generate_snapshot(workspace_root, "Auto-generated on pickup")
        print(snap_path.read_text(encoding="utf-8").rstrip())
        return 0

    print("Usage: python3 scripts/pstack-session.py <pause [note] | pickup>")
    return 2


if __name__ == "__main__":
    sys.exit(main())
