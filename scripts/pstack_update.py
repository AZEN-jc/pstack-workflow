#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None

from pstack_resolver import get_pstack_home

DIRECTIVE_VERSION = "v3.1"

DIRECTIVE_SPECS: tuple[tuple[str, str, str], ...] = (
    (".codex/AGENTS.md", "v3.1 Codex CLI Edition", "，并通过 `pstack spawn` 或无状态全新任务执行"),
    (".config/opencode/AGENTS.md", "v3.1 OpenCode Edition", "，并通过 `pstack spawn`、`/pstack-build`、`/pstack-swarm` 派发全新子 Agent"),
    (".claude/CLAUDE.md", "v3.1 Claude Code Global Edition", "，并通过 `Subagent` 工具或 `pstack spawn` 派发全新子 Agent"),
    (".workbuddy-ai/SOUL.md", "v3.1 WorkBuddy AI Edition", "，并通过无状态全新任务或桌面端双 Tab 闭环执行"),
    (".workbuddy/SOUL.md", "v3.1 WorkBuddy AI Edition", "，并通过无状态全新任务或桌面端双 Tab 闭环执行"),
)

SKILL_TARGET_SPECS: tuple[tuple[str, str], ...] = (
    (".gemini/config", ".gemini/config/skills/pstack"),
    (".claude", ".claude/skills/pstack"),
    (".codex", ".codex/skills/pstack"),
    (".config/opencode", ".config/opencode/skills/pstack"),
    (".cursor", ".cursor/skills-cursor/pstack"),
    (".workbuddy-ai", ".workbuddy-ai/skills/pstack"),
    (".workbuddy", ".workbuddy/skills/pstack"),
    (".pi/agent", ".pi/agent/skills/pstack"),
    (".agents", ".agents/skills/pstack"),
)

TOML_TABLE_HEADER_RE = re.compile(r"^[ \t]*\[(?:[^\[\]\n]|\"[^\n]*\")+\][ \t]*(?:#.*)?$|^[ \t]*\[\[(?:[^\[\]\n]|\"[^\n]*\")+\]\][ \t]*(?:#.*)?$", re.MULTILINE)
TOML_PSTACK_HEADER_RE = re.compile(r"^[ \t]*\[mcp_servers\.pstack\][ \t]*(?:#.*)?$", re.MULTILINE)


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


def _build_directive_block(edition: str, dispatch_hint: str) -> str:
    return (
        f"# Pstack Directives ({edition})\n"
        "1. 收到任何架构剖析、代码实现、Bug 修复或技术推文/长文创作任务，必须首先读取 `.agents/pstack/pstack-core.md`（轻量工作区直接读取 `~/.config/pstack/home/.agents/pstack/pstack-core.md`）。\n"
        f"2. 严禁在主线程直接生成长篇初稿或全量扫描大文件；路由建单用 `pstack route/run --max-rework 2` 写入 `.agents/handoffs/active-brief.md`{dispatch_hint}，多阶段并行/竞技使用 `pstack swarm/arena/resume/tree`。\n"
        "3. 优先通过 `pstack hook/mcp`（原生 MCP `pstack-mcp`）执行门禁与拓扑调度；任何代码或文字产出交付前，必须通过 `pstack verify all`（或 `python3 scripts/pstack-verify.py all`）门禁校验，返回码非 0 严禁提交。\n"
    )


def _upsert_directive_file(path: Path, block: str) -> str:
    if not path.is_file() and not path.parent.is_dir():
        return "skipped"

    existed = path.is_file()
    existing = path.read_text(encoding="utf-8") if existed else ""
    match = re.search(r"(?m)^# Pstack Directives\b", existing)
    prefix = existing[:match.start()].rstrip() if match else existing.rstrip()
    new_text = f"{prefix}\n\n{block.strip()}\n" if prefix else f"{block.strip()}\n"
    if existed and new_text == existing:
        return "unchanged"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    return "updated" if existed else "created"


def _upsert_json_mcp(
    config_path: Path,
    parent_key: str,
    server_name: str,
    payload: dict,
    allow_create: bool,
) -> str:
    existed = config_path.is_file()
    if not existed and not allow_create:
        return "skipped"

    if existed:
        raw = config_path.read_text(encoding="utf-8")
        if raw.strip():
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                return f"error: invalid JSON ({exc})"
        else:
            data = {}
    else:
        data = {}

    if not isinstance(data, dict):
        return "error: root JSON value must be an object"

    section = data.get(parent_key)
    if section is None:
        section = {}
        data[parent_key] = section
    if not isinstance(section, dict):
        return f"error: '{parent_key}' must be a JSON object"

    if section.get(server_name) == payload:
        return "unchanged"

    section[server_name] = payload
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return "updated" if existed else "created"


def _upsert_codex_toml_mcp(config_path: Path, mcp_bin: str) -> str:
    existed = config_path.is_file()
    if not existed and not config_path.parent.is_dir():
        return "skipped"

    desired_obj = {"command": mcp_bin, "args": []}
    desired_block = f"[mcp_servers.pstack]\ncommand = {json.dumps(mcp_bin)}\nargs = []\n"

    raw = config_path.read_text(encoding="utf-8") if existed else ""
    if existed and raw.strip() and tomllib is not None:
        try:
            parsed = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as exc:
            return f"error: invalid TOML ({exc})"
        existing_srv = parsed.get("mcp_servers", {}).get("pstack") if isinstance(parsed.get("mcp_servers"), dict) else None
        if existing_srv == desired_obj:
            return "unchanged"

    match = TOML_PSTACK_HEADER_RE.search(raw)
    if match:
        next_table = TOML_TABLE_HEADER_RE.search(raw, match.end())
        end_idx = next_table.start() if next_table else len(raw)
        replacement = desired_block.rstrip() + ("\n\n" if end_idx < len(raw) else "\n")
        new_raw = raw[:match.start()] + replacement + raw[end_idx:]
    else:
        new_raw = f"{raw.rstrip()}\n\n{desired_block}" if raw.strip() else desired_block

    if tomllib is not None:
        try:
            parsed_after = tomllib.loads(new_raw)
        except tomllib.TOMLDecodeError as exc:
            return f"error: TOML validation failed after edit ({exc})"
        if parsed_after.get("mcp_servers", {}).get("pstack") != desired_obj:
            return "error: TOML post-write verification mismatch"

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(new_raw, encoding="utf-8")
    return "updated" if existed else "created"


def _ensure_symlink(source: Path, target: Path) -> str:
    if target.is_symlink():
        try:
            if target.exists() and target.resolve() == source.resolve():
                return "unchanged"
        except OSError:
            pass
        target.unlink()
        target.symlink_to(source)
        return "updated"
    if target.exists():
        return "skipped_existing_non_symlink"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source)
    return "created"


def sync_all_coding_agents(repo_dir: Path, home_dir: Path | None = None, quiet: bool = False) -> dict:
    repo = repo_dir.expanduser().resolve()
    home = (home_dir or Path.home()).expanduser().resolve()
    mcp_bin = str(home / ".local" / "bin" / "pstack-mcp")

    results: dict = {
        "home_dir": str(home),
        "mcp_bin": mcp_bin,
        "directives": {},
        "mcp_configs": {},
        "symlinks": {},
        "errors": [],
    }

    for rel_path, edition, dispatch_hint in DIRECTIVE_SPECS:
        target = home / rel_path
        block = _build_directive_block(edition, dispatch_hint)
        status = _upsert_directive_file(target, block)
        results["directives"][rel_path] = status
        if status.startswith("error:"):
            results["errors"].append(f"{rel_path}: {status}")

    codex_status = _upsert_codex_toml_mcp(home / ".codex" / "config.toml", mcp_bin)
    results["mcp_configs"][".codex/config.toml"] = codex_status

    opencode_cfg = home / ".config" / "opencode" / "opencode.json"
    opencode_status = _upsert_json_mcp(
        opencode_cfg,
        "mcp",
        "pstack",
        {"type": "local", "command": [mcp_bin], "enabled": True},
        allow_create=opencode_cfg.parent.is_dir(),
    )
    results["mcp_configs"][".config/opencode/opencode.json"] = opencode_status

    claude_cfg = home / ".claude.json"
    claude_status = _upsert_json_mcp(
        claude_cfg,
        "mcpServers",
        "pstack",
        {"command": mcp_bin, "args": []},
        allow_create=claude_cfg.is_file() or (home / ".claude").is_dir(),
    )
    results["mcp_configs"][".claude.json"] = claude_status

    cursor_cfg = home / ".cursor" / "mcp.json"
    cursor_status = _upsert_json_mcp(
        cursor_cfg,
        "mcpServers",
        "pstack",
        {"command": mcp_bin, "args": []},
        allow_create=cursor_cfg.parent.is_dir(),
    )
    results["mcp_configs"][".cursor/mcp.json"] = cursor_status

    for cfg_rel, cfg_status in results["mcp_configs"].items():
        if cfg_status.startswith("error:"):
            results["errors"].append(f"{cfg_rel}: {cfg_status}")

    for skill_name in ("pstack", "reframe", "sharpen"):
        skill_source = repo / ".agents" / "skills" / skill_name
        if not skill_source.is_dir():
            continue
        for agent_root_rel, base_skill_rel in SKILL_TARGET_SPECS:
            skill_rel = str(Path(base_skill_rel).parent / skill_name)
            target = home / skill_rel
            if (home / agent_root_rel).is_dir() or target.is_symlink():
                results["symlinks"][skill_rel] = _ensure_symlink(skill_source, target)

    opencode_cmd_src = repo / "adapters" / "opencode" / "commands"
    if opencode_cmd_src.is_dir() and (home / ".config" / "opencode").is_dir():
        opencode_cmd_dst = home / ".config" / "opencode" / "command"
        for cmd_file in sorted(opencode_cmd_src.glob("*.md")):
            rel_cmd = f".config/opencode/command/{cmd_file.name}"
            results["symlinks"][rel_cmd] = _ensure_symlink(cmd_file, opencode_cmd_dst / cmd_file.name)

    if not quiet:
        changed = sum(
            1
            for group in (results["directives"], results["mcp_configs"], results["symlinks"])
            for val in group.values()
            if val in ("created", "updated")
        )
        print(f"[OK] Synced global directives, MCP configs, and skills across coding agents ({changed} updated/created)")
        for err in results["errors"]:
            print(f"[WARNING] {err}")

    return results


def _read_last_synced_commit(home: Path) -> str:
    stamp_file = home / ".config" / "pstack" / ".last_synced_commit"
    if not stamp_file.is_file():
        return ""
    return stamp_file.read_text(encoding="utf-8").strip()


def _write_last_synced_commit(home: Path, commit_sha: str) -> None:
    stamp_file = home / ".config" / "pstack" / ".last_synced_commit"
    stamp_file.parent.mkdir(parents=True, exist_ok=True)
    stamp_file.write_text(commit_sha.strip() + "\n", encoding="utf-8")


def auto_sync_if_needed(
    repo_dir: Path,
    home_dir: Path | None = None,
    quiet: bool = False,
    force: bool = False,
) -> dict:
    repo = repo_dir.expanduser().resolve()
    home = (home_dir or Path.home()).expanduser().resolve()
    if not (repo / ".git").exists():
        return {"synced": False, "reason": "not_a_git_repo"}

    code, head_sha = run_git(["rev-parse", "HEAD"], repo)
    if code != 0 or not head_sha:
        return {"synced": False, "reason": f"head_unavailable: {head_sha}"}

    last_sha = _read_last_synced_commit(home)
    if not force and last_sha == head_sha:
        return {"synced": False, "reason": "already_synced", "commit": head_sha}

    bootstrap_script = repo / "scripts" / "bootstrap-repo.sh"
    bootstrap_rc = 0
    if bootstrap_script.is_file():
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["PSTACK_SKIP_BOOTSTRAP_SYNC"] = "1"
        proc = subprocess.run(
            ["bash", str(bootstrap_script), "--global"],
            cwd=repo,
            env=env,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.DEVNULL if quiet else None,
            check=False,
        )
        bootstrap_rc = proc.returncode

    sync_res = sync_all_coding_agents(repo, home_dir=home, quiet=quiet)
    if bootstrap_rc == 0 and not sync_res["errors"]:
        _write_last_synced_commit(home, head_sha)

    return {
        "synced": True,
        "commit": head_sha,
        "bootstrap_rc": bootstrap_rc,
        "sync_result": sync_res,
    }


def get_agents_sync_status(repo_dir: Path, home_dir: Path | None = None) -> dict:
    repo = repo_dir.expanduser().resolve()
    home = (home_dir or Path.home()).expanduser().resolve()
    mcp_bin = str(home / ".local" / "bin" / "pstack-mcp")

    directives: dict[str, str] = {}
    for rel_path, _, _ in DIRECTIVE_SPECS:
        path = home / rel_path
        if path.is_file():
            txt = path.read_text(encoding="utf-8", errors="replace")
            if "# Pstack Directives (v3.1" in txt and "pstack route/run --max-rework 2" in txt and "pstack hook/mcp" in txt:
                directives[rel_path] = "SYNCED_V3_1"
            elif "# Pstack Directives" in txt:
                directives[rel_path] = "OUTDATED"
            else:
                directives[rel_path] = "MISSING"
        elif path.parent.is_dir():
            directives[rel_path] = "MISSING"
        else:
            directives[rel_path] = "NOT_INSTALLED"

    mcp_configs: dict[str, str] = {}
    codex_toml = home / ".codex" / "config.toml"
    if codex_toml.is_file():
        if tomllib is not None:
            try:
                parsed = tomllib.loads(codex_toml.read_text(encoding="utf-8"))
                srv = parsed.get("mcp_servers", {}).get("pstack") if isinstance(parsed.get("mcp_servers"), dict) else None
                mcp_configs[".codex/config.toml"] = (
                    "REGISTERED" if isinstance(srv, dict) and srv.get("command") == mcp_bin else "MISSING"
                )
            except tomllib.TOMLDecodeError:
                mcp_configs[".codex/config.toml"] = "ERROR"
        else:
            mcp_configs[".codex/config.toml"] = "REGISTERED" if "[mcp_servers.pstack]" in codex_toml.read_text(encoding="utf-8") else "MISSING"
    else:
        mcp_configs[".codex/config.toml"] = "MISSING" if codex_toml.parent.is_dir() else "NOT_INSTALLED"

    json_checks = [
        (".config/opencode/opencode.json", home / ".config" / "opencode" / "opencode.json", "mcp", (home / ".config" / "opencode").is_dir()),
        (".claude.json", home / ".claude.json", "mcpServers", (home / ".claude").is_dir()),
        (".cursor/mcp.json", home / ".cursor" / "mcp.json", "mcpServers", (home / ".cursor").is_dir()),
    ]
    for label, cfg_path, parent_key, dir_installed in json_checks:
        if cfg_path.is_file():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
                srv = data.get(parent_key, {}).get("pstack") if isinstance(data, dict) and isinstance(data.get(parent_key), dict) else None
                mcp_configs[label] = "REGISTERED" if isinstance(srv, dict) else "MISSING"
            except json.JSONDecodeError:
                mcp_configs[label] = "ERROR"
        else:
            mcp_configs[label] = "MISSING" if dir_installed else "NOT_INSTALLED"

    code, head_sha = run_git(["rev-parse", "HEAD"], repo) if (repo / ".git").exists() else (1, "")
    last_sha = _read_last_synced_commit(home)
    return {
        "directives": directives,
        "mcp_configs": mcp_configs,
        "head_commit": head_sha if code == 0 else "",
        "last_synced_commit": last_sha,
    }


def print_agents_status(repo_dir: Path, home_dir: Path | None = None) -> None:
    status = get_agents_sync_status(repo_dir, home_dir=home_dir)
    for rel_path, st in status["directives"].items():
        if st == "NOT_INSTALLED":
            continue
        tag = "[SYNCED v3.1]" if st == "SYNCED_V3_1" else f"[{st}]"
        print(f"  {tag:<14} Directive {rel_path:<28} -> {st}")
    for rel_path, st in status["mcp_configs"].items():
        if st == "NOT_INSTALLED":
            continue
        tag = "[REGISTERED]" if st == "REGISTERED" else f"[{st}]"
        print(f"  {tag:<14} MCP Config {rel_path:<27} -> {st}")
    head_short = status["head_commit"][:7] if status["head_commit"] else "unknown"
    synced_short = status["last_synced_commit"][:7] if status["last_synced_commit"] else "never"
    sync_tag = "[SYNCED]" if status["head_commit"] and status["head_commit"] == status["last_synced_commit"] else "[STALE]"
    print(f"  {sync_tag:<14} Auto-Sync Commit Stamp              -> {synced_short} (HEAD: {head_short})")


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
    behind_count = 0
    if fetch_code == 0:
        _, count_out = run_git(["rev-list", "--count", f"HEAD..origin/{remote_branch}"], repo_dir)
        if count_out.isdigit():
            behind_count = int(count_out)
        if behind_count > 0:
            _, log_out = run_git(["log", f"HEAD..origin/{remote_branch}", "--oneline", "-n", "5"], repo_dir)
            if log_out:
                commit_list = [line.strip() for line in log_out.splitlines() if line.strip()]

    if behind_count == 0:
        return {
            "status": "up_to_date",
            "local_head": local_head[:7],
            "remote_head": remote_head[:7],
            "remote_branch": remote_branch,
            "message": f"Up to date with origin/{remote_branch} ({local_head[:7]})",
        }

    return {
        "status": "update_available",
        "local_head": local_head[:7],
        "remote_head": remote_head[:7],
        "remote_branch": remote_branch,
        "commits": commit_list,
        "message": f"Update available: {behind_count} new commits (local {local_head[:7]} -> remote {remote_head[:7]})",
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
        auto_sync_if_needed(repo_dir, force=True)
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

    auto_sync_if_needed(repo_dir, force=True)
    print(f"[OK] Successfully updated Pstack to {check['remote_head']} [实测 Measured]")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Pstack remote update checker and updater")
    parser.add_argument("--check", action="store_true", help="Check remote for updates without pulling")
    parser.add_argument("--status-line", action="store_true", help="Print single status line for pstack status")
    parser.add_argument("--status-agents", action="store_true", help="Print global directive and MCP sync status")
    parser.add_argument("--apply", action="store_true", help="Apply updates via git pull and re-bootstrap")
    parser.add_argument("--sync-agents", action="store_true", help="Sync global directives, MCP configs, and skills")
    parser.add_argument("--auto-sync", action="store_true", help="Auto-sync all coding agents when HEAD changed")
    parser.add_argument("--quiet", action="store_true", help="Suppress informational output")
    args = parser.parse_args()

    repo_dir = get_pstack_home()

    if args.sync_agents:
        sync_res = sync_all_coding_agents(repo_dir, quiet=args.quiet)
        if (repo_dir / ".git").exists() and not sync_res["errors"]:
            code, head_sha = run_git(["rev-parse", "HEAD"], repo_dir)
            if code == 0 and head_sha:
                _write_last_synced_commit(Path.home(), head_sha)
        return 1 if sync_res["errors"] else 0

    if args.status_agents:
        print_agents_status(repo_dir)
        return 0

    if args.auto_sync:
        res = auto_sync_if_needed(repo_dir, quiet=args.quiet)
        sync_res = res.get("sync_result", {})
        if isinstance(sync_res, dict) and sync_res.get("errors"):
            return 1
        return 0

    if not (repo_dir / ".git").exists():
        if not args.quiet:
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
