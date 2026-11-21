#!/usr/bin/env python3
"""
pstack Git Pre-Commit Hook Manager
Usage:
  python3 scripts/pstack_hook.py install [--repo <path>]
  python3 scripts/pstack_hook.py uninstall [--repo <path>]
  python3 scripts/pstack_hook.py status [--repo <path>]
"""
import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path

from pstack_resolver import ensure_workspace_skeleton, get_pstack_home, get_workspace_root

MANAGED_MARKER = "# [PSTACK-MANAGED-PRE-COMMIT]"


def resolve_hooks_dir(repo_path: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--git-path", "hooks"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    raw_hooks = Path(proc.stdout.strip())
    if raw_hooks.is_absolute():
        return raw_hooks
    return (repo_path / raw_hooks).resolve()


def _render_pre_commit_script(pstack_bin: Path) -> str:
    escaped_bin = str(pstack_bin).replace('"', '\\"')
    return (
        "#!/usr/bin/env bash\n"
        f"{MANAGED_MARKER}\n"
        "set -euo pipefail\n\n"
        'HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        'if [[ -x "$HOOK_DIR/pre-commit.pstack-backup" ]]; then\n'
        '  "$HOOK_DIR/pre-commit.pstack-backup" "$@"\n'
        "fi\n\n"
        'REPO_ROOT="$(git rev-parse --show-toplevel)"\n'
        'export PSTACK_WORKSPACE="$REPO_ROOT"\n\n'
        'PSTACK_CLI=""\n'
        'if [[ -x "$REPO_ROOT/scripts/pstack" ]]; then\n'
        '  PSTACK_CLI="$REPO_ROOT/scripts/pstack"\n'
        f'elif [[ -x "{escaped_bin}" ]]; then\n'
        f'  PSTACK_CLI="{escaped_bin}"\n'
        'elif [[ -x "${HOME}/.config/pstack/home/scripts/pstack" ]]; then\n'
        '  PSTACK_CLI="${HOME}/.config/pstack/home/scripts/pstack"\n'
        'elif command -v pstack >/dev/null 2>&1; then\n'
        '  PSTACK_CLI="$(command -v pstack)"\n'
        "fi\n\n"
        'if [[ -z "$PSTACK_CLI" ]]; then\n'
        '  echo "[pstack pre-commit] pstack CLI not found; skipping."\n'
        "  exit 0\n"
        "fi\n\n"
        'echo ">>> [pstack pre-commit] Enforcing handoff scope lock & code anti-slop gate..."\n'
        '"$PSTACK_CLI" verify handoff --check-scope\n'
        '"$PSTACK_CLI" verify code\n'
    )


def install_hook(repo_path: Path) -> int:
    hooks_dir = resolve_hooks_dir(repo_path)
    if hooks_dir is None:
        print(f"[FAIL] Not a valid git repository: {repo_path}")
        return 1

    ensure_workspace_skeleton(repo_path.resolve())
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"
    backup_file = hooks_dir / "pre-commit.pstack-backup"

    if hook_file.exists():
        existing = hook_file.read_text(encoding="utf-8", errors="ignore")
        if MANAGED_MARKER not in existing:
            hook_file.replace(backup_file)
            backup_file.chmod(backup_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"[OK] Preserved existing pre-commit hook -> {backup_file}")

    pstack_bin = (Path(__file__).resolve().parent / "pstack")
    if not pstack_bin.is_file():
        pstack_bin = get_pstack_home() / "scripts" / "pstack"

    hook_file.write_text(_render_pre_commit_script(pstack_bin), encoding="utf-8")
    hook_file.chmod(0o755)
    print(f"[OK] Installed Pstack pre-commit hook -> {hook_file}")
    return 0


def status_hook(repo_path: Path) -> int:
    hooks_dir = resolve_hooks_dir(repo_path)
    if hooks_dir is None:
        print(f"[FAIL] Not a valid git repository: {repo_path}")
        return 1

    hook_file = hooks_dir / "pre-commit"
    if not hook_file.is_file():
        print(f"[NOT INSTALLED] Missing pre-commit hook at {hook_file}")
        return 1

    content = hook_file.read_text(encoding="utf-8", errors="ignore")
    is_exec = os.access(hook_file, os.X_OK)
    if MANAGED_MARKER in content and is_exec:
        backup_note = " (chained existing hook)" if (hooks_dir / "pre-commit.pstack-backup").exists() else ""
        print(f"[INSTALLED] Active Pstack pre-commit hook at {hook_file}{backup_note}")
        return 0

    print(f"[NOT INSTALLED] Pre-commit hook exists but is not Pstack-managed or executable: {hook_file}")
    return 1


def uninstall_hook(repo_path: Path) -> int:
    hooks_dir = resolve_hooks_dir(repo_path)
    if hooks_dir is None:
        print(f"[FAIL] Not a valid git repository: {repo_path}")
        return 1

    hook_file = hooks_dir / "pre-commit"
    backup_file = hooks_dir / "pre-commit.pstack-backup"

    if hook_file.is_file():
        content = hook_file.read_text(encoding="utf-8", errors="ignore")
        if MANAGED_MARKER in content:
            hook_file.unlink()
            if backup_file.is_file():
                backup_file.replace(hook_file)
                print(f"[OK] Uninstalled Pstack hook and restored previous hook -> {hook_file}")
            else:
                print(f"[OK] Uninstalled Pstack pre-commit hook -> {hook_file}")
            return 0
        print(f"[SKIP] Existing pre-commit hook at {hook_file} is not Pstack-managed.")
        return 0

    print(f"[OK] No Pstack pre-commit hook installed at {hook_file}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack Git Pre-Commit Hook Manager")
    parser.add_argument("action", choices=["install", "uninstall", "status"], help="Hook management action")
    parser.add_argument("--repo", type=Path, default=None, help="Target git repository path")
    args = parser.parse_args()

    repo = (args.repo or get_workspace_root()).expanduser().resolve()
    if args.action == "install":
        return install_hook(repo)
    if args.action == "status":
        return status_hook(repo)
    if args.action == "uninstall":
        return uninstall_hook(repo)
    return 2


if __name__ == "__main__":
    sys.exit(main())
