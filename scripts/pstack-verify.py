#!/usr/bin/env python3
"""
pstack Unified Verification & /correct Ban CLI
Usage:
  python3 scripts/pstack-verify.py all
  python3 scripts/pstack-verify.py prose [file]
  python3 scripts/pstack-verify.py handoff [brief_file]
  python3 scripts/pstack-verify.py code [file_or_dir]
  python3 scripts/pstack-verify.py ban "<phrase>"
"""
import subprocess
import sys
from pathlib import Path


def run_step(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def add_banned_phrase(workspace_root: Path, phrase: str) -> int:
    clean = phrase.strip()
    if not clean:
        print("[FAIL] Empty phrase cannot be banned.")
        return 1
    ban_file = workspace_root / ".agents" / "pstack" / "custom-banned-phrases.txt"
    ban_file.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if ban_file.exists():
        existing = {
            ln.strip()
            for ln in ban_file.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        }
    if clean in existing:
        print(f"[OK] Phrase already in blacklist: 「{clean}」 ({ban_file})")
        return 0
    with ban_file.open("a", encoding="utf-8") as f:
        f.write(f"{clean}\n")
    print(f"[OK] Added 「{clean}」 to permanent Pstack blacklist ({ban_file}).")
    return 0


def main() -> int:
    workspace_root = Path(__file__).resolve().parent.parent
    scripts_dir = workspace_root / "scripts"
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "ban":
        if len(sys.argv) < 3:
            print("Usage: python3 scripts/pstack-verify.py ban \"<phrase>\"")
            return 2
        return add_banned_phrase(workspace_root, sys.argv[2])

    if mode == "prose":
        target = sys.argv[2] if len(sys.argv) > 2 else str(workspace_root / ".agents/handoffs/output-draft.md")
        return run_step([sys.executable, str(scripts_dir / "verify-prose.py"), target])

    if mode == "handoff":
        target = sys.argv[2] if len(sys.argv) > 2 else str(workspace_root / ".agents/handoffs/active-brief.md")
        return run_step([sys.executable, str(scripts_dir / "verify-handoff.py"), target])

    if mode == "code":
        targets = sys.argv[2:] if len(sys.argv) > 2 else [str(scripts_dir)]
        return run_step([sys.executable, str(scripts_dir / "verify-code-slop.py"), *targets])

    if mode == "all":
        rc1 = run_step([sys.executable, str(scripts_dir / "verify-handoff.py")])
        rc2 = run_step(
            [sys.executable, str(scripts_dir / "verify-prose.py"), str(workspace_root / ".agents/handoffs/output-draft.md")]
        )
        rc3 = run_step([sys.executable, str(scripts_dir / "verify-code-slop.py"), str(scripts_dir)])
        if rc1 == 0 and rc2 == 0 and rc3 == 0:
            print("\n>>> [PSTACK SUITE] ALL 3 HARNESS GATES GREEN <<<")
            return 0
        print("\n>>> [PSTACK SUITE] GATE FAILURE DETECTED <<<")
        return 1

    print(f"Unknown mode: {mode}. Use one of: all | prose | handoff | code | ban")
    return 2


if __name__ == "__main__":
    sys.exit(main())
