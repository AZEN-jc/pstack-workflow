#!/usr/bin/env python3
"""
pstack Decision Ledger CLI (show-me-your-work)
Usage:
  python3 scripts/log-decision.py list
  python3 scripts/log-decision.py add \
    --task-id "bug-lock-05" \
    --verdict "ROOT_CAUSE" \
    --hypothesis "flock timeout caused by unclosed fd" \
    --pointer "scripts/ag-spawn.sh:10-42" \
    --before "deadlock rate 12%" \
    --after "deadlock rate 0%" \
    --lesson "Always close inherited descriptors before exec"
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from pstack_resolver import ensure_workspace_skeleton, get_workspace_root

VALID_VERDICTS = ("KEEP", "REVERT", "ROOT_CAUSE", "PERF_WIN")


def sanitize_cell(value: str) -> str:
    return value.replace("\t", " ").replace("\n", " ").strip()


def cmd_list(ledger: Path) -> int:
    if not ledger.exists():
        print(f"[FAIL] Ledger not found: {ledger}")
        return 1
    rows = [ln.split("\t") for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for idx, row in enumerate(rows):
        if idx == 0:
            print(f"{'#':<3} | {'TASK_ID':<22} | {'VERDICT':<10} | {'BEFORE -> AFTER':<36} | {'POINTER'}")
            print("-" * 100)
            continue
        metrics = f"{row[5]} -> {row[6]}"
        print(f"{idx:<3} | {row[1]:<22} | {row[2]:<10} | {metrics[:36]:<36} | {row[4]}")
    return 0


def cmd_add(ledger: Path, args: argparse.Namespace) -> int:
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    row = [
        ts,
        sanitize_cell(args.task_id),
        sanitize_cell(args.verdict),
        sanitize_cell(args.hypothesis),
        sanitize_cell(args.pointer),
        sanitize_cell(args.before),
        sanitize_cell(args.after),
        sanitize_cell(args.lesson),
    ]
    with ledger.open("a", encoding="utf-8") as f:
        f.write("\t".join(row) + "\n")
    print(f"[OK] Appended decision record `{args.task_id}` ({args.verdict}) to {ledger}")
    return 0


def main() -> int:
    workspace_root = get_workspace_root()
    ensure_workspace_skeleton(workspace_root)
    ledger = workspace_root / ".agents/decision.tsv"

    parser = argparse.ArgumentParser(description="Manage .agents/decision.tsv empirical audit ledger")
    sub = parser.add_subparsers(dest="subcmd", required=True)

    sub.add_parser("list", help="List all empirical records in decision.tsv")

    add_p = sub.add_parser("add", help="Append a verified decision record")
    add_p.add_argument("--task-id", required=True)
    add_p.add_argument("--verdict", required=True, choices=VALID_VERDICTS)
    add_p.add_argument("--hypothesis", required=True)
    add_p.add_argument("--pointer", required=True)
    add_p.add_argument("--before", required=True)
    add_p.add_argument("--after", required=True)
    add_p.add_argument("--lesson", required=True)

    args = parser.parse_args()
    if args.subcmd == "list":
        return cmd_list(ledger)
    return cmd_add(ledger, args)


if __name__ == "__main__":
    sys.exit(main())
