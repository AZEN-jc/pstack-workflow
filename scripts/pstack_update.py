#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

from pstack_resolver import get_pstack_home

def run_git(args: list[str], cwd: Path, timeout: int = 10) -> tuple[int, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    for proxy_var in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        env.pop(proxy_var, None)
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd)] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        output = proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip()
        return proc.returncode, output
    except subprocess.TimeoutExpired:
        return 124, "Network timeout"
    except Exception as exc:
        return 1, str(exc)

def get_remote_branch(repo_dir: Path) -> str:
    code, out = run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo_dir)
    if code == 0 and "/" in out:
        return out.split("/", 1)[1]
    return "main"

def check_update(repo_dir: Path, timeout: int = 5) -> dict:
    code, local_head = run_git(["rev-parse", "HEAD"], repo_dir)
    if code != 0:
        return {"status": "error", "message": f"Failed to get local HEAD: {local_head}"}

    remote_branch = get_remote_branch(repo_dir)
    code, ls_out = run_git(["ls-remote", "origin", f"refs/heads/{remote_branch}"], repo_dir, timeout=timeout)
    if code != 0:
        return {
            "status": "offline",
            "local_head": local_head[:7],
            "remote_head": "unknown",
            "message": f"Remote check skipped: {ls_out}",
        }

    parts = ls_out.split()
    if not parts:
        return {
            "status": "error",
            "local_head": local_head[:7],
            "message": "Empty response from remote origin",
        }

    remote_head = parts[0]
    if local_head == remote_head:
        return {
            "status": "up_to_date",
            "local_head": local_head[:7],
            "remote_head": remote_head[:7],
            "remote_branch": remote_branch,
            "message": f"Up to date with origin/{remote_branch} ({local_head[:7]})",
        }

    fetch_code, _ = run_git(["fetch", "origin", remote_branch, "--quiet"], repo_dir, timeout=15)
    commit_list = []
    if fetch_code == 0:
        _, log_out = run_git(["log", f"HEAD..origin/{remote_branch}", "--oneline", "-n", "5"], repo_dir)
        if log_out:
            commit_list = [line.strip() for line in log_out.splitlines() if line.strip()]

    return {
        "status": "update_available",
        "local_head": local_head[:7],
        "remote_head": remote_head[:7],
        "remote_branch": remote_branch,
        "commits": commit_list,
        "message": f"Update available: {len(commit_list)} new commits (local {local_head[:7]} -> remote {remote_head[:7]})",
    }

def print_status_line(repo_dir: Path, timeout: int = 3) -> None:
    res = check_update(repo_dir, timeout=timeout)
    st = res["status"]
    if st == "up_to_date":
        print(f"  [UP TO DATE] Remote Sync (origin/{res.get('remote_branch', 'main')})  -> {res['local_head']} (Latest) [实测 Measured]")
    elif st == "update_available":
        print(f"  [UPDATE]     Remote Sync (origin/{res.get('remote_branch', 'main')})  -> {res['local_head']} -> {res['remote_head']} ({len(res.get('commits', []))} commits behind) [实测 Measured]")
    elif st == "offline":
        print(f"  [CACHED]     Remote Sync (origin/main)  -> {res.get('local_head', 'unknown')} (Offline / Cached)")
    else:
        print(f"  [WARNING]    Remote Sync check failed   -> {res.get('message', 'unknown error')}")

def apply_update(repo_dir: Path) -> int:
    check = check_update(repo_dir, timeout=10)
    if check["status"] == "up_to_date":
        print(f"[OK] Pstack is already up to date ({check['local_head']}) [实测 Measured]")
        return 0

    if check["status"] == "offline":
        print(f"[WARNING] Cannot reach remote origin: {check['message']}")
        return 2

    if check["status"] == "error":
        print(f"[ERROR] Update check failed: {check['message']}")
        return 1

    print(f"Applying update to {repo_dir}...")
    code, status_out = run_git(["status", "--porcelain"], repo_dir)
    dirty_files = [line for line in status_out.splitlines() if not line.startswith("??")]
    if dirty_files:
        print("[WARNING] Working tree has tracked modifications. Stashing before fast-forward...")
        run_git(["stash", "push", "-m", "pstack-auto-update"], repo_dir)

    remote_branch = check.get("remote_branch", "main")
    code, pull_out = run_git(["pull", "--ff-only", "origin", remote_branch], repo_dir, timeout=30)
    if code != 0:
        print(f"[ERROR] git pull failed: {pull_out}")
        return 1

    bootstrap_script = repo_dir / "scripts" / "bootstrap-repo.sh"
    if bootstrap_script.is_file():
        print("Re-mounting global agent links and slash commands...")
        subprocess.run(["bash", str(bootstrap_script), "--global"], cwd=repo_dir, check=True)

    print(f"[OK] Successfully updated Pstack to {check['remote_head']} [实测 Measured]")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Pstack remote update checker and updater")
    parser.add_argument("--check", action="store_true", help="Check remote for updates without pulling")
    parser.add_argument("--status-line", action="store_true", help="Print single status line for pstack status")
    parser.add_argument("--apply", action="store_true", help="Apply updates via git pull and re-bootstrap")
    args = parser.parse_args()

    repo_dir = get_pstack_home()
    if not (repo_dir / ".git").exists():
        print(f"[WARNING] {repo_dir} is not a git repository; cannot check remote updates.")
        return 0

    if args.status_line:
        print_status_line(repo_dir)
        return 0

    if args.check:
        res = check_update(repo_dir, timeout=8)
        print("=" * 68)
        print("PSTACK REMOTE UPDATE CHECK")
        print("=" * 68)
        print(f"Local Commit  : {res.get('local_head', 'unknown')}")
        print(f"Remote Commit : {res.get('remote_head', 'unknown')}")
        print(f"Status        : {res['status'].upper()} - {res['message']}")
        if res.get("commits"):
            print("Recent incoming commits:")
            for c in res["commits"]:
                print(f"  * {c}")
        print("=" * 68)
        if res["status"] == "up_to_date":
            return 0
        elif res["status"] == "update_available":
            return 10
        elif res["status"] == "offline":
            return 2
        return 1

    return apply_update(repo_dir)

if __name__ == "__main__":
    sys.exit(main())
