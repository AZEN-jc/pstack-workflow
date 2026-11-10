#!/usr/bin/env python3
"""
pstack CLI Task Tree & Event Stream Visualizer
Usage:
  python3 scripts/pstack_tree.py [--json] [--state <path>] [--events <path>]
"""
import argparse
import json
import sys
from pathlib import Path

from pstack_resolver import get_workspace_root


def render_ascii_tree(dag_data: dict, events: list[dict]) -> str:
    task_id = dag_data.get("task_id", "(no-active-task)")
    updated = dag_data.get("updated_at", "")
    nodes = dag_data.get("nodes", {})

    lines: list[str] = [
        "=" * 68,
        f"PSTACK v3.0 TASK DAG TREE: {task_id}",
        f"Last Updated: {updated}" if updated else "Status: Initialized",
        "=" * 68,
    ]

    if not nodes:
        lines.append("  (No DAG nodes recorded in dag-state.json)")
    else:
        node_ids = list(nodes.keys())
        for idx, nid in enumerate(node_ids):
            node = nodes[nid]
            is_last = idx == len(node_ids) - 1
            branch = "└──" if is_last else "├──"
            pipe = "   " if is_last else "│  "

            status = node.get("status", "PENDING")
            role = node.get("role", "builder")
            tier = node.get("tier", "fast_tier")
            model = node.get("model", "default")
            name = node.get("name", nid)
            sha = node.get("artifact_sha256", "none")
            rework = node.get("rework_count", 0)
            deps = node.get("depends_on", [])
            allowed = ", ".join(node.get("allowed_paths", [])) or "*"

            badge = f"[{status}]"
            lines.append(f"{branch} {badge} {nid}: {name} (role: {role}, tier: {tier}, model: {model})")
            if deps:
                lines.append(f"{pipe} ├── depends_on : {deps}")
            lines.append(f"{pipe} ├── scope lock : {allowed}")
            lines.append(f"{pipe} ├── sha256     : {sha} | rework: {rework}")
            lines.append(f"{pipe} └── worktree   : .agents/worktrees/{nid}")

    if events:
        lines.append("-" * 68)
        lines.append(f"RECENT EVENTS STREAM ({len(events)} logged):")
        for ev in events[-5:]:
            ts = ev.get("timestamp", "")
            etype = ev.get("event_type", "UNKNOWN")
            tid = ev.get("task_id", "")
            lines.append(f"  • {ts} [{etype}] {tid}")
    lines.append("=" * 68)
    return "\n".join(lines)


def load_tree_data(
    workspace_root: Path,
    state_path: Path | None = None,
    events_path: Path | None = None,
) -> tuple[dict, list[dict]]:
    state_file = state_path or (workspace_root / ".agents" / "handoffs" / "dag-state.json")
    events_file = events_path or (workspace_root / ".agents" / "handoffs" / "events.jsonl")

    dag_data = {"version": "3.0", "task_id": "(empty)", "nodes": {}}
    if state_file.is_file():
        try:
            dag_data = json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    events: list[dict] = []
    if events_file.is_file():
        try:
            for line in events_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    events.append(json.loads(line))
        except (json.JSONDecodeError, OSError):
            pass

    return dag_data, events


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack CLI Task Tree & Event Stream Visualizer")
    parser.add_argument("--json", action="store_true", help="Output tree and event stream as JSON")
    parser.add_argument("--state", type=Path, default=None, help="Custom path to dag-state.json")
    parser.add_argument("--events", type=Path, default=None, help="Custom path to events.jsonl")
    args = parser.parse_args()

    ws = get_workspace_root()
    dag_data, events = load_tree_data(ws, args.state, args.events)

    if args.json:
        combined = {
            "version": "3.0",
            "dag_state": dag_data,
            "events_count": len(events),
            "events": events[-20:],
        }
        print(json.dumps(combined, indent=2, ensure_ascii=False))
        return 0

    print(render_ascii_tree(dag_data, events))
    return 0


if __name__ == "__main__":
    sys.exit(main())
