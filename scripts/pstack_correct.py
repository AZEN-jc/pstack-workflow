#!/usr/bin/env python3
"""
pstack 5-Tier Correction Pyramid CLI
Usage:
  python3 scripts/pstack-correct.py --scan
  python3 scripts/pstack-correct.py --code-rule "<regex>" "<reason>" [--id <rule_id>]
  python3 scripts/pstack-correct.py --prose-ban "<phrase>"
"""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

from pstack_resolver import get_pstack_home, get_workspace_root, resolve_asset


def scan_decision_ledger(workspace_root: Path) -> int:
    ledger = resolve_asset(".agents/decision.tsv", workspace_root)
    if not ledger.exists():
        print(f"[FAIL] Decision ledger not found: {ledger}")
        return 1

    lines = [ln.strip() for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    candidates: list[str] = []
    for row_str in lines[1:]:
        cols = row_str.split("\t")
        if len(cols) < 8:
            continue
        verdict = cols[2].strip()
        if verdict in ("REVERT", "ROOT_CAUSE"):
            task_id = cols[1].strip()
            pointer = cols[4].strip()
            lesson = cols[7].strip()
            candidates.append(f"  - [{verdict}] {task_id} ({pointer}): {lesson[:62]}")

    report = [
        "=== PSTACK 5-TIER CORRECTION PYRAMID SCAN ===",
        f"LEDGER : {ledger} ({len(candidates)} REVERT/ROOT_CAUSE records)",
        "CANDIDATES FOR MECHANICAL PROMOTION:",
        *(candidates[-8:] or ["  (0 REVERT/ROOT_CAUSE records found)"]),
        "PROMOTE ACTIONS:",
        "  Code Rule : pstack correct --code-rule \"<regex>\" \"<reason>\"",
        "  Prose Ban : pstack correct --prose-ban \"<phrase>\"",
    ]
    print("\n".join(report[:15]))
    return 0


def add_code_rule(workspace_root: Path, pattern: str, reason: str, rule_id: str | None = None) -> int:
    clean_pat = pattern.strip().replace("\t", " ")
    clean_reason = reason.strip().replace("\t", " ")
    if not clean_pat or not clean_reason:
        print("[FAIL] Both regex pattern and reason are required.")
        return 1

    short_hash = hashlib.sha256(clean_pat.encode("utf-8")).hexdigest()[:6]
    final_id = (rule_id or f"custom-rule-{short_hash}").strip().replace("\t", "-")

    tsv_path = workspace_root / ".agents" / "pstack" / "custom-code-rules.tsv"
    tsv_path.parent.mkdir(parents=True, exist_ok=True)
    if not tsv_path.exists():
        tsv_path.write_text("rule_id\tpattern\treason\n", encoding="utf-8")

    existing_lines = tsv_path.read_text(encoding="utf-8").splitlines()
    for ln in existing_lines[1:]:
        parts = ln.split("\t")
        if len(parts) >= 2 and (parts[0].strip() == final_id or parts[1].strip() == clean_pat):
            print(f"[OK] Code rule already registered: {parts[0].strip()} ({tsv_path})")
            return 0

    with tsv_path.open("a", encoding="utf-8") as f:
        f.write(f"{final_id}\t{clean_pat}\t{clean_reason}\n")
    print(f"[OK] Promoted code rule `{final_id}` -> {tsv_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack 5-Tier Correction Pyramid CLI")
    parser.add_argument("--scan", action="store_true", help="Scan decision.tsv for REVERT/ROOT_CAUSE lessons")
    parser.add_argument(
        "--code-rule",
        nargs=2,
        metavar=("REGEX", "REASON"),
        help="Append a regex code rule to .agents/pstack/custom-code-rules.tsv",
    )
    parser.add_argument("--id", type=str, help="Optional rule_id for --code-rule")
    parser.add_argument("--prose-ban", type=str, metavar="PHRASE", help="Add phrase to custom-banned-phrases.txt")
    args = parser.parse_args()

    workspace_root = get_workspace_root()
    pstack_home = get_pstack_home()

    if args.code_rule:
        return add_code_rule(workspace_root, args.code_rule[0], args.code_rule[1], args.id)

    if args.prose_ban:
        verify_script = pstack_home / "scripts" / "pstack-verify.py"
        proc = subprocess.run([sys.executable, str(verify_script), "ban", args.prose_ban], check=False)
        return proc.returncode

    return scan_decision_ledger(workspace_root)


if __name__ == "__main__":
    sys.exit(main())
