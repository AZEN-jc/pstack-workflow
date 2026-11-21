#!/usr/bin/env python3
"""
pstack Git Worktree Agent Scheduler
Supports WorktreeSandbox, allowed_paths Scope Lock, Swarm DAG, Arena Competition, and DAG Checkpoint Resume.
Usage:
  python3 scripts/pstack_scheduler.py swarm [--goal "<goal>" | --spec <dag.json>] [--dry-run]
  python3 scripts/pstack_scheduler.py arena [--runners codex,opencode] [--brief <brief_file>] [--dry-run]
  python3 scripts/pstack_scheduler.py resume [--state .agents/handoffs/dag-state.json] [--dry-run]
"""
import argparse
import concurrent.futures
import fnmatch
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from pstack_resolver import ensure_workspace_skeleton, get_pstack_home, get_workspace_root, resolve_asset

IGNORED_SYNC_PREFIXES = (".agents/worktrees/", ".git/", ".agents/handoffs/")
SNAPSHOT_MANIFEST_REL = ".agents/.snapshot-manifest.json"


def _matches_scope(rel_path: str, pattern: str) -> bool:
    if fnmatch.fnmatch(rel_path, pattern):
        return True
    clean_pat = pattern.rstrip("/*")
    if clean_pat and (rel_path == clean_pat or rel_path.startswith(clean_pat + "/")):
        return True
    return False


def _clean_git_path(raw: str) -> str:
    cleaned = raw.strip()
    if " -> " in cleaned:
        cleaned = cleaned.split(" -> ")[1].strip()
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    return cleaned


def _is_git_repo(path: Path) -> bool:
    if not path.exists():
        return False
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def log_scheduler_event(event_type: str, payload: dict, workspace_root: Path) -> None:
    events_file = workspace_root / ".agents" / "handoffs" / "events.jsonl"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    record = {"timestamp": ts, "event_type": event_type, **payload}
    with events_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def merge_worktree_to_workspace(
    worktree_path: Path,
    workspace_root: Path,
    allowed_paths: list[str],
    base_commit: str | None = None,
) -> list[str]:
    wt_resolved = worktree_path.resolve()
    ws_resolved = workspace_root.resolve()

    if (wt_resolved / ".git").exists() and _is_git_repo(wt_resolved) and _is_git_repo(ws_resolved):
        base_ref = base_commit or "HEAD"
        verify_ref = subprocess.run(
            ["git", "-C", str(wt_resolved), "rev-parse", "--verify", base_ref],
            capture_output=True,
            text=True,
            check=False,
        )
        if verify_ref.returncode == 0:
            changed_paths: set[str] = set()
            status_proc = subprocess.run(
                ["git", "-C", str(wt_resolved), "status", "--porcelain", "-uall"],
                capture_output=True,
                text=True,
                check=False,
            )
            if status_proc.returncode == 0:
                for line in status_proc.stdout.splitlines():
                    if len(line) < 4:
                        continue
                    raw_target = line[3:]
                    if " -> " in raw_target:
                        old_p, new_p = raw_target.split(" -> ", 1)
                        changed_paths.add(_clean_git_path(old_p))
                        changed_paths.add(_clean_git_path(new_p))
                    else:
                        changed_paths.add(_clean_git_path(raw_target))

            diff_proc = subprocess.run(
                ["git", "-C", str(wt_resolved), "diff", "--name-only", base_ref],
                capture_output=True,
                text=True,
                check=False,
            )
            if diff_proc.returncode == 0:
                for line in diff_proc.stdout.splitlines():
                    cleaned = _clean_git_path(line)
                    if cleaned:
                        changed_paths.add(cleaned)

            scoped_paths: list[str] = []
            for rel_p in sorted(changed_paths):
                if not rel_p or rel_p == SNAPSHOT_MANIFEST_REL or rel_p.startswith(IGNORED_SYNC_PREFIXES):
                    continue
                if allowed_paths and not any(_matches_scope(rel_p, pat) for pat in allowed_paths):
                    continue
                scoped_paths.append(rel_p)

            if not scoped_paths:
                return []

            add_proc = subprocess.run(
                ["git", "-C", str(wt_resolved), "add", "-A", "--", *scoped_paths],
                capture_output=True,
                text=True,
                check=False,
            )
            if add_proc.returncode != 0:
                raise RuntimeError(
                    f"[Merge Error] git add failed in {wt_resolved}: {add_proc.stderr.strip()}"
                )

            patch_proc = subprocess.run(
                ["git", "-C", str(wt_resolved), "diff", "--cached", "--binary", base_ref, "--", *scoped_paths],
                capture_output=True,
                check=False,
            )
            if patch_proc.returncode != 0:
                err_txt = patch_proc.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"[Merge Error] git diff failed in {wt_resolved}: {err_txt}")

            patch_bytes = patch_proc.stdout
            if not patch_bytes.strip():
                return []

            pre_bytes: dict[str, bytes | None] = {}
            for rel_p in scoped_paths:
                target_p = ws_resolved / rel_p
                pre_bytes[rel_p] = target_p.read_bytes() if target_p.is_file() else None

            apply_proc = subprocess.run(
                ["git", "-C", str(ws_resolved), "apply", "--3way"],
                input=patch_bytes,
                capture_output=True,
                check=False,
            )
            if apply_proc.returncode != 0:
                subprocess.run(
                    ["git", "-C", str(ws_resolved), "reset", "-q", "--", *scoped_paths],
                    capture_output=True,
                    check=False,
                )
                for rel_p, orig_bytes in pre_bytes.items():
                    target_p = ws_resolved / rel_p
                    if orig_bytes is None:
                        if target_p.is_file() or target_p.is_symlink():
                            target_p.unlink()
                    else:
                        target_p.parent.mkdir(parents=True, exist_ok=True)
                        target_p.write_bytes(orig_bytes)
                stderr_txt = apply_proc.stderr.decode("utf-8", errors="replace").strip()
                stdout_txt = apply_proc.stdout.decode("utf-8", errors="replace").strip()
                detail = stderr_txt or stdout_txt or f"exit={apply_proc.returncode}"
                raise RuntimeError(f"[Merge Conflict] 3-way git apply failed: {detail}")

            return scoped_paths

    merged_files: list[str] = []
    wt_files: set[str] = set()
    for root, _, files in os.walk(wt_resolved):
        for f in files:
            full_p = Path(root) / f
            rel_p = full_p.relative_to(wt_resolved).as_posix()
            if rel_p == SNAPSHOT_MANIFEST_REL or rel_p.startswith(IGNORED_SYNC_PREFIXES):
                continue
            if allowed_paths and not any(_matches_scope(rel_p, pat) for pat in allowed_paths):
                continue
            wt_files.add(rel_p)
            dest_p = ws_resolved / rel_p
            dest_p.parent.mkdir(parents=True, exist_ok=True)
            if not dest_p.exists() or dest_p.read_bytes() != full_p.read_bytes():
                shutil.copy2(full_p, dest_p)
                merged_files.append(rel_p)

    manifest_file = wt_resolved / SNAPSHOT_MANIFEST_REL
    baseline_files: set[str] | None = None
    if manifest_file.is_file():
        try:
            baseline_files = set(json.loads(manifest_file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, TypeError):
            baseline_files = None

    if baseline_files is None:
        baseline_files = set()
        for root, _, files in os.walk(ws_resolved):
            for f in files:
                full_p = Path(root) / f
                rel_p = full_p.relative_to(ws_resolved).as_posix()
                if rel_p == SNAPSHOT_MANIFEST_REL or rel_p.startswith(IGNORED_SYNC_PREFIXES):
                    continue
                if allowed_paths and not any(_matches_scope(rel_p, pat) for pat in allowed_paths):
                    continue
                baseline_files.add(rel_p)

    for rel_del in sorted(baseline_files - wt_files):
        if rel_del == SNAPSHOT_MANIFEST_REL or rel_del.startswith(IGNORED_SYNC_PREFIXES):
            continue
        if allowed_paths and not any(_matches_scope(rel_del, pat) for pat in allowed_paths):
            continue
        target_del = ws_resolved / rel_del
        if target_del.is_file():
            target_del.unlink()
            merged_files.append(rel_del)

    return merged_files


class WorktreeSandbox:
    def __init__(self, node_id: str, workspace_root: Path, base_ref: str = "HEAD"):
        self.node_id = node_id
        self.workspace_root = workspace_root.resolve()
        self.base_ref = base_ref
        self.base_commit = ""
        self.path = (self.workspace_root / ".agents" / "worktrees" / node_id).resolve()
        self.is_git_worktree = False

    def create(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cleanup()

        rev_proc = subprocess.run(
            ["git", "rev-parse", self.base_ref],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if rev_proc.returncode == 0 and rev_proc.stdout.strip():
            self.base_commit = rev_proc.stdout.strip()
        else:
            self.base_commit = self.base_ref

        proc = subprocess.run(
            ["git", "worktree", "add", "--detach", str(self.path), self.base_ref],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            self.is_git_worktree = True
            return self.path

        self._snapshot_copy()
        return self.path

    def _snapshot_copy(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        ignore_patterns = shutil.ignore_patterns(".git", ".agents/worktrees", "__pycache__", ".venv", "venv")
        for item in self.workspace_root.iterdir():
            if item.name in (".git", ".agents"):
                continue
            dest_item = self.path / item.name
            if item.is_dir():
                shutil.copytree(item, dest_item, ignore=ignore_patterns, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest_item)
        agents_src = self.workspace_root / ".agents"
        if agents_src.is_dir():
            dest_agents = self.path / ".agents"
            shutil.copytree(agents_src, dest_agents, ignore=shutil.ignore_patterns("worktrees"), dirs_exist_ok=True)

        copied_files: list[str] = []
        for root, _, files in os.walk(self.path):
            for f in files:
                full_p = Path(root) / f
                rel_p = full_p.relative_to(self.path).as_posix()
                if rel_p == SNAPSHOT_MANIFEST_REL or rel_p.startswith(IGNORED_SYNC_PREFIXES):
                    continue
                copied_files.append(rel_p)
        manifest_path = self.path / SNAPSHOT_MANIFEST_REL
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(sorted(copied_files)), encoding="utf-8")

    def check_scope(self, allowed_paths: list[str]) -> list[str]:
        if not allowed_paths:
            return []
        violations: list[str] = []
        changed_files: set[str] = set()

        if self.is_git_worktree:
            proc = subprocess.run(
                ["git", "status", "--porcelain", "-uall"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if len(line) < 4:
                        continue
                    raw_target = _clean_git_path(line[3:])
                    if raw_target:
                        changed_files.add(raw_target)

            diff_ref = self.base_commit or self.base_ref
            diff_proc = subprocess.run(
                ["git", "diff", "--name-only", diff_ref],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=False,
            )
            if diff_proc.returncode == 0:
                for line in diff_proc.stdout.splitlines():
                    raw = _clean_git_path(line)
                    if raw:
                        changed_files.add(raw)
        else:
            wt_files: set[str] = set()
            for root, _, files in os.walk(self.path):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(self.path).as_posix()
                    if rel_p == SNAPSHOT_MANIFEST_REL:
                        continue
                    wt_files.add(rel_p)
                    orig_p = self.workspace_root / rel_p
                    if not orig_p.exists() or orig_p.read_bytes() != full_p.read_bytes():
                        changed_files.add(rel_p)
            manifest_file = self.path / SNAPSHOT_MANIFEST_REL
            if manifest_file.is_file():
                try:
                    baseline = set(json.loads(manifest_file.read_text(encoding="utf-8")))
                    changed_files.update(baseline - wt_files)
                except (json.JSONDecodeError, OSError, TypeError):
                    pass

        for raw_target in sorted(changed_files):
            if raw_target == SNAPSHOT_MANIFEST_REL or raw_target.startswith(IGNORED_SYNC_PREFIXES):
                continue
            matched = any(_matches_scope(raw_target, p) for p in allowed_paths)
            if not matched:
                violations.append(raw_target)

        return violations

    def cleanup(self) -> None:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(self.path)],
            cwd=self.workspace_root,
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.workspace_root,
            capture_output=True,
            check=False,
        )
        self.is_git_worktree = False
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)

    def __enter__(self):
        return self.create()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def load_dag_state(workspace_root: Path, state_path: Path | None = None) -> dict:
    dest = state_path or (workspace_root / ".agents" / "handoffs" / "dag-state.json")
    if dest.is_file():
        try:
            return json.loads(dest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"version": "3.0", "updated_at": "", "task_id": "", "nodes": {}}


def save_dag_state(state: dict, workspace_root: Path, state_path: Path | None = None) -> None:
    dest = state_path or (workspace_root / ".agents" / "handoffs" / "dag-state.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    state["updated_at"] = ts
    dest.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_default_swarm_dag(goal: str, task_id: str) -> dict:
    return {
        "version": "3.0",
        "task_id": task_id,
        "status": "pending",
        "nodes": {
            "node-1": {
                "id": "node-1",
                "name": "core-architecture",
                "role": "architect",
                "tier": "deep_tier",
                "model": "gemini-2.5-pro",
                "goal": f"Design and implement domain model for: {goal}",
                "allowed_paths": ["scripts/*", ".agents/*"],
                "depends_on": [],
                "status": "PENDING",
                "artifact_sha256": None,
                "rework_count": 0,
                "error": None,
            },
            "node-2": {
                "id": "node-2",
                "name": "harness-verification",
                "role": "builder",
                "tier": "fast_tier",
                "model": "gemini-3.8-flash-high",
                "goal": f"Build unit test harness and gate verification for: {goal}",
                "allowed_paths": ["tests/*", ".agents/*"],
                "depends_on": ["node-1"],
                "status": "PENDING",
                "artifact_sha256": None,
                "rework_count": 0,
                "error": None,
            },
        },
    }


def topological_sort_nodes(nodes: dict) -> list[str]:
    visited: set[str] = set()
    order: list[str] = []

    def dfs(node_id: str, path: set[str]) -> None:
        if node_id in path:
            raise ValueError(f"Cyclic dependency detected involving node `{node_id}`")
        if node_id in visited:
            return
        path.add(node_id)
        for dep in nodes.get(node_id, {}).get("depends_on", []):
            if dep in nodes:
                dfs(dep, path)
        path.remove(node_id)
        visited.add(node_id)
        order.append(node_id)

    for nid in sorted(nodes.keys()):
        if nid not in visited:
            dfs(nid, set())
    return order


def topological_levels(nodes: dict) -> list[list[str]]:
    if not nodes:
        return []
    topo_order = topological_sort_nodes(nodes)
    node_depth: dict[str, int] = {}
    for nid in topo_order:
        deps = [d for d in nodes.get(nid, {}).get("depends_on", []) if d in nodes]
        if not deps:
            node_depth[nid] = 0
        else:
            node_depth[nid] = 1 + max(node_depth[d] for d in deps)

    max_depth = max(node_depth.values())
    levels: list[list[str]] = []
    for lvl in range(max_depth + 1):
        lvl_nodes = sorted(nid for nid, depth in node_depth.items() if depth == lvl)
        if lvl_nodes:
            levels.append(lvl_nodes)
    return levels


def _verify_worktree_node(wt_path: Path, node: dict, node_env: dict[str, str]) -> tuple[int, str]:
    custom_vcmd = node.get("verify_cmd")
    if custom_vcmd:
        proc = subprocess.run(
            str(custom_vcmd),
            shell=True,
            cwd=wt_path,
            env=node_env,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return proc.returncode, out

    if not node.get("cmd") and not node.get("runner"):
        return 0, ""

    slop_script = get_pstack_home() / "scripts" / "verify-code-slop.py"
    if slop_script.is_file():
        status_proc = subprocess.run(
            ["git", "-C", str(wt_path), "status", "--porcelain", "-uall"],
            capture_output=True,
            text=True,
            check=False,
        )
        code_targets: list[str] = []
        if status_proc.returncode == 0:
            for ln in status_proc.stdout.splitlines():
                if len(ln) < 4:
                    continue
                rel = _clean_git_path(ln[3:])
                cand = wt_path / rel
                if cand.is_file() and cand.suffix in {".py", ".sh", ".js", ".ts", ".tsx", ".go", ".rs"}:
                    code_targets.append(str(cand))
        if code_targets:
            slop_proc = subprocess.run(
                [sys.executable, str(slop_script), *code_targets],
                cwd=wt_path,
                env=node_env,
                capture_output=True,
                text=True,
                check=False,
            )
            if slop_proc.returncode != 0:
                out = (slop_proc.stdout or "") + ("\n" + slop_proc.stderr if slop_proc.stderr else "")
                return slop_proc.returncode, out

    if (wt_path / "tests").is_dir():
        test_proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=wt_path,
            env=node_env,
            capture_output=True,
            text=True,
            check=False,
        )
        if test_proc.returncode != 0:
            out = (test_proc.stdout or "") + ("\n" + test_proc.stderr if test_proc.stderr else "")
            return test_proc.returncode, out

    return 0, ""


def _sync_merged_base_to_worktree(
    workspace_root: Path,
    sandbox: WorktreeSandbox,
    merged_paths: list[str],
) -> None:
    if not sandbox.is_git_worktree or not merged_paths:
        return
    wt_path = sandbox.path
    changed = False
    for rel_p in merged_paths:
        src_p = workspace_root / rel_p
        dst_p = wt_path / rel_p
        if src_p.is_file():
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_p, dst_p)
            changed = True
        elif dst_p.is_file() or dst_p.is_symlink():
            dst_p.unlink()
            changed = True

    if not changed:
        return

    subprocess.run(
        ["git", "-C", str(wt_path), "add", "-A", "--", *merged_paths],
        capture_output=True,
        check=False,
    )
    diff_chk = subprocess.run(
        ["git", "-C", str(wt_path), "diff", "--cached", "--quiet"],
        capture_output=True,
        check=False,
    )
    if diff_chk.returncode != 0:
        c_proc = subprocess.run(
            [
                "git",
                "-C",
                str(wt_path),
                "-c",
                "user.name=pstack",
                "-c",
                "user.email=pstack@local",
                "commit",
                "--no-verify",
                "-q",
                "-m",
                "pstack-wave-base",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if c_proc.returncode == 0:
            rev = subprocess.run(
                ["git", "-C", str(wt_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            if rev.returncode == 0 and rev.stdout.strip():
                sandbox.base_commit = rev.stdout.strip()


def _execute_swarm_node(
    node_id: str,
    dag_data: dict,
    workspace_root: Path,
    state_file: Path,
    state_lock: threading.Lock,
    wave_merged_files: set[str],
    dry_run: bool,
    scripts_dir: Path,
    sha_prefix: str = "",
    wave_base_files: list[str] | None = None,
) -> tuple[bool, str | None]:
    nodes = dag_data["nodes"]
    node = nodes[node_id]
    allowed_paths = node.get("allowed_paths", [])
    with state_lock:
        node["status"] = "RUNNING"
        save_dag_state(dag_data, workspace_root, state_file)

    if dry_run:
        time.sleep(0.05)
        seed = f"{sha_prefix}{node_id}-{dag_data.get('task_id', '')}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
        with state_lock:
            node["status"] = "MERGED"
            node["artifact_sha256"] = digest
            save_dag_state(dag_data, workspace_root, state_file)
            log_scheduler_event(
                "SWARM_NODE_SUCCESS",
                {"node_id": node_id, "sha256": digest, "dry_run": True},
                workspace_root,
            )
        return True, f"    [OK] Node {node_id} simulated and verified (sha256={digest})"

    sandbox = WorktreeSandbox(node_id, workspace_root)
    with state_lock:
        wt_path = sandbox.create()
        prior_merged = list(wave_base_files) if wave_base_files is not None else sorted(wave_merged_files)
        if prior_merged:
            _sync_merged_base_to_worktree(workspace_root, sandbox, prior_merged)

    try:
        with state_lock:
            node["worktree_path"] = str(wt_path)
        node_env = os.environ.copy()
        node_env["PSTACK_WORKSPACE"] = str(wt_path)

        if node.get("cmd"):
            cmd_proc = subprocess.run(
                str(node["cmd"]),
                shell=True,
                cwd=wt_path,
                env=node_env,
                capture_output=True,
                text=True,
                check=False,
            )
            if cmd_proc.returncode != 0:
                err_msg = (cmd_proc.stderr or cmd_proc.stdout or f"exit={cmd_proc.returncode}").strip()
                with state_lock:
                    node["status"] = "FAILED"
                    node["error"] = f"Command Failed: {err_msg[:240]}"
                    node["rework_count"] = node.get("rework_count", 0) + 1
                    save_dag_state(dag_data, workspace_root, state_file)
                    log_scheduler_event(
                        "SWARM_NODE_FAILED",
                        {"node_id": node_id, "error": node["error"]},
                        workspace_root,
                    )
                return False, f"    [FAIL] Command failed in {node_id}: {node['error']}"
        elif node.get("runner"):
            ensure_workspace_skeleton(wt_path)
            brief_arg = str(node.get("brief_path") or (wt_path / ".agents" / "handoffs" / "active-brief.md"))
            spawn_sh = scripts_dir / "ag-spawn.sh"
            spawn_proc = subprocess.run(
                [str(spawn_sh), brief_arg, str(node["runner"])],
                cwd=wt_path,
                env=node_env,
                capture_output=True,
                text=True,
                check=False,
            )
            if spawn_proc.returncode != 0:
                err_msg = (spawn_proc.stderr or spawn_proc.stdout or f"exit={spawn_proc.returncode}").strip()
                with state_lock:
                    node["status"] = "FAILED"
                    node["error"] = f"Runner Failed: {err_msg[:240]}"
                    node["rework_count"] = node.get("rework_count", 0) + 1
                    save_dag_state(dag_data, workspace_root, state_file)
                    log_scheduler_event(
                        "SWARM_NODE_FAILED",
                        {"node_id": node_id, "error": node["error"]},
                        workspace_root,
                    )
                return False, f"    [FAIL] Runner failed in {node_id}: {node['error']}"

        violations = sandbox.check_scope(allowed_paths)
        if violations:
            with state_lock:
                node["status"] = "FAILED"
                node["error"] = f"Scope Violation: {violations}"
                node["rework_count"] = node.get("rework_count", 0) + 1
                save_dag_state(dag_data, workspace_root, state_file)
                log_scheduler_event(
                    "SWARM_NODE_FAILED",
                    {"node_id": node_id, "violations": violations},
                    workspace_root,
                )
            return False, f"    [FAIL] Scope violation detected in {node_id}: {violations}"

        v_rc, v_out = _verify_worktree_node(wt_path, node, node_env)
        if v_rc != 0:
            digest_err = extract_gate_failure_digest(v_out)
            with state_lock:
                node["status"] = "FAILED"
                node["error"] = f"Verification Failed: {digest_err}"
                node["rework_count"] = node.get("rework_count", 0) + 1
                save_dag_state(dag_data, workspace_root, state_file)
                log_scheduler_event(
                    "SWARM_NODE_FAILED",
                    {"node_id": node_id, "error": node["error"]},
                    workspace_root,
                )
            return False, f"    [FAIL] Verification failed in {node_id}: {digest_err}"

        with state_lock:
            try:
                merged = merge_worktree_to_workspace(
                    wt_path,
                    workspace_root,
                    allowed_paths,
                    base_commit=sandbox.base_commit,
                )
            except RuntimeError as exc:
                node["status"] = "FAILED"
                node["error"] = str(exc)
                node["rework_count"] = node.get("rework_count", 0) + 1
                save_dag_state(dag_data, workspace_root, state_file)
                log_scheduler_event(
                    "SWARM_NODE_FAILED",
                    {"node_id": node_id, "error": str(exc)},
                    workspace_root,
                )
                return False, f"    [FAIL] Merge error in {node_id}: {exc}"

            wave_merged_files.update(merged)
            digest = hashlib.sha256(f"{sha_prefix}{node_id}-{time.time()}".encode("utf-8")).hexdigest()[:12]
            node["status"] = "MERGED"
            node["artifact_sha256"] = digest
            node["merged_files"] = merged
            save_dag_state(dag_data, workspace_root, state_file)
            log_scheduler_event(
                "SWARM_NODE_SUCCESS",
                {"node_id": node_id, "sha256": digest, "merged_files": merged},
                workspace_root,
            )
        return True, f"    [OK] Node {node_id} completed and merged (sha256={digest})"
    finally:
        with state_lock:
            sandbox.cleanup()


def execute_swarm(
    workspace_root: Path,
    goal: str | None = None,
    spec_path: Path | None = None,
    dry_run: bool = False,
    state_override: Path | None = None,
) -> int:
    ensure_workspace_skeleton(workspace_root)
    state_file = state_override or (workspace_root / ".agents" / "handoffs" / "dag-state.json")

    if spec_path and spec_path.is_file():
        dag_data = json.loads(spec_path.read_text(encoding="utf-8"))
    else:
        task_id = f"swarm-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        dag_data = build_default_swarm_dag(goal or "Swarm DAG task", task_id)

    nodes = dag_data.get("nodes", {})
    try:
        topo_order = topological_sort_nodes(nodes)
        levels = topological_levels(nodes)
    except ValueError as exc:
        print(f"[FAIL] Invalid DAG: {exc}")
        return 1

    dag_data["status"] = "running"
    save_dag_state(dag_data, workspace_root, state_file)
    log_scheduler_event(
        "SWARM_START",
        {"task_id": dag_data["task_id"], "order": topo_order, "levels": levels, "dry_run": dry_run},
        workspace_root,
    )

    print("=" * 68)
    print(f"PSTACK v3.1 GIT WORKTREE SWARM SCHEDULER: {dag_data['task_id']}")
    print(f"Topological Execution Order: {' -> '.join(topo_order)}")
    print(f"Concurrent Waves           : {levels}")
    print("=" * 68)

    state_lock = threading.Lock()
    wave_merged_files: set[str] = set()
    scripts_dir = Path(__file__).resolve().parent

    for level_idx, level_nodes in enumerate(levels):
        ready_nodes: list[str] = []
        for node_id in level_nodes:
            node = nodes[node_id]
            if node.get("status") in ("VERIFIED", "MERGED"):
                wave_merged_files.update(node.get("merged_files", []))
                print(f"  [SKIP] Node {node_id} already {node.get('status')} (sha256={node.get('artifact_sha256')})")
                continue
            ready_nodes.append(node_id)
            print(f"\n>>> Wave {level_idx} Swarm Node: {node_id} ({node.get('name')})")
            print(f"    Role: {node.get('role')} | Tier: {node.get('tier')} | Model: {node.get('model')}")
            print(f"    Allowed Paths: {node.get('allowed_paths')}")

        if not ready_nodes:
            continue

        wave_base_files = sorted(wave_merged_files)
        wave_failed = False
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(ready_nodes))) as pool:
            futures = {
                pool.submit(
                    _execute_swarm_node,
                    nid,
                    dag_data,
                    workspace_root,
                    state_file,
                    state_lock,
                    wave_merged_files,
                    dry_run,
                    scripts_dir,
                    "",
                    wave_base_files,
                ): nid
                for nid in ready_nodes
            }
            for fut in concurrent.futures.as_completed(futures):
                ok, msg = fut.result()
                if msg:
                    print(msg)
                if not ok:
                    wave_failed = True

        if wave_failed:
            dag_data["status"] = "failed"
            save_dag_state(dag_data, workspace_root, state_file)
            return 1

    dag_data["status"] = "completed"
    save_dag_state(dag_data, workspace_root, state_file)
    log_scheduler_event("SWARM_ALL_MERGED", {"task_id": dag_data["task_id"]}, workspace_root)
    print("\n" + "=" * 68)
    print("STATUS : ALL SWARM NODES VERIFIED & MERGED GREEN")
    print("=" * 68)
    return 0


def execute_arena(
    workspace_root: Path,
    runners: list[str] | None = None,
    brief_path: Path | None = None,
    dry_run: bool = False,
    candidates: list[str] | None = None,
    state_override: Path | None = None,
) -> int:
    ensure_workspace_skeleton(workspace_root)
    active_runners = runners or candidates or ["codex", "opencode"]
    _ = brief_path or (workspace_root / ".agents" / "handoffs" / "active-brief.md")
    state_file = state_override or (workspace_root / ".agents" / "handoffs" / "dag-state.json")
    task_id = f"arena-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    print("=" * 68)
    print(f"PSTACK v3.1 MULTI-AGENT ARENA: {task_id}")
    print(f"Competitors: {', '.join(active_runners)}")
    print("Evaluation: 1) 4-Gate Count, 2) Scope Compliance, 3) Runtime Speed, 4) Minimal Diff")
    print("=" * 68)

    log_scheduler_event("ARENA_START", {"task_id": task_id, "competitors": active_runners, "dry_run": dry_run}, workspace_root)

    candidates_eval: list[dict] = []
    allowed_scope = [".agents/*", "scripts/*", "tests/*"]

    for idx, runner in enumerate(active_runners, 1):
        cand_id = f"cand-{runner}-{idx}"
        print(f"\n[Arena] Spawning Candidate in Isolated Worktree: {runner} ({cand_id})")

        t0 = time.perf_counter()
        if dry_run:
            time.sleep(0.04 * idx)
            elapsed = round(time.perf_counter() - t0, 3)
            gates_passed = 4
            scope_ok = True
            diff_lines = 15 + idx * 4
            score = (gates_passed * 1000) + (1000 if scope_ok else 0) + max(0, 500 - int(elapsed * 100)) - diff_lines
            sha12 = hashlib.sha256(f"{cand_id}-{runner}".encode("utf-8")).hexdigest()[:12]
            cand_res = {
                "runner": runner,
                "cand_id": cand_id,
                "gates_passed": gates_passed,
                "scope_ok": scope_ok,
                "diff_lines": diff_lines,
                "elapsed_sec": elapsed,
                "score": score,
                "sha256": sha12,
            }
            candidates_eval.append(cand_res)
            print(f"  Candidate {runner}: Gates={gates_passed}/4, Scope={'PASS' if scope_ok else 'FAIL'}, Diff={diff_lines} lines, Score={score}")
            continue

        sandbox = WorktreeSandbox(cand_id, workspace_root)
        wt_path = sandbox.create()
        violations = sandbox.check_scope(allowed_scope)
        elapsed = round(time.perf_counter() - t0, 3)
        scope_ok = len(violations) == 0

        gates_passed = 0
        if (wt_path / ".agents" / "handoffs" / "active-brief.md").exists():
            gates_passed += 1
        if (wt_path / ".agents" / "handoffs" / "output-draft.md").exists():
            gates_passed += 1
        slop_proc = subprocess.run(
            [sys.executable, "scripts/verify-code-slop.py", "scripts"],
            cwd=wt_path,
            capture_output=True,
            check=False,
        )
        if slop_proc.returncode == 0:
            gates_passed += 1
        test_proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=wt_path,
            capture_output=True,
            check=False,
        )
        if test_proc.returncode == 0:
            gates_passed += 1

        diff_stat_proc = subprocess.run(
            ["git", "diff", "--shortstat", "HEAD"],
            cwd=wt_path,
            capture_output=True,
            text=True,
            check=False,
        )
        diff_lines = 0
        if diff_stat_proc.returncode == 0 and diff_stat_proc.stdout:
            m_ins = re.search(r"(\d+) insertion", diff_stat_proc.stdout)
            m_del = re.search(r"(\d+) deletion", diff_stat_proc.stdout)
            diff_lines = (int(m_ins.group(1)) if m_ins else 0) + (int(m_del.group(1)) if m_del else 0)

        score = (gates_passed * 1000) + (1000 if scope_ok else 0) + max(0, 500 - int(elapsed * 100)) - diff_lines
        sha12 = hashlib.sha256(f"{cand_id}".encode("utf-8")).hexdigest()[:12]
        cand_res = {
            "runner": runner,
            "cand_id": cand_id,
            "gates_passed": gates_passed,
            "scope_ok": scope_ok,
            "diff_lines": diff_lines,
            "elapsed_sec": elapsed,
            "score": score,
            "sha256": sha12,
            "wt_path": wt_path,
            "sandbox": sandbox,
        }
        candidates_eval.append(cand_res)

    candidates_eval.sort(key=lambda x: x["score"], reverse=True)
    winner = candidates_eval[0]

    nodes_state: dict[str, dict] = {}
    for cand in candidates_eval:
        is_winner = cand["cand_id"] == winner["cand_id"]
        nodes_state[cand["cand_id"]] = {
            "id": cand["cand_id"],
            "name": f"arena-{cand['runner']}",
            "role": "builder",
            "tier": "fast_tier",
            "model": cand["runner"],
            "runner": cand["runner"],
            "status": "WINNER" if is_winner else "LOSER",
            "artifact_sha256": cand["sha256"],
            "rework_count": 0,
            "gates_passed": cand["gates_passed"],
            "scope_ok": cand["scope_ok"],
            "elapsed_sec": cand["elapsed_sec"],
            "diff_lines": cand["diff_lines"],
            "score": cand["score"],
            "allowed_paths": allowed_scope,
            "depends_on": [],
        }

    arena_dag = {
        "version": "3.0",
        "task_id": task_id,
        "mode": "arena",
        "status": "completed",
        "winner": winner["runner"],
        "winner_sha256": winner["sha256"],
        "nodes": nodes_state,
    }
    save_dag_state(arena_dag, workspace_root, state_file)

    if not dry_run:
        winner_wt = winner.get("wt_path")
        winner_sb = winner.get("sandbox")
        if winner_wt and Path(winner_wt).is_dir():
            base_c = winner_sb.base_commit if winner_sb else None
            merge_worktree_to_workspace(Path(winner_wt), workspace_root, allowed_scope, base_commit=base_c)
        for cand in candidates_eval:
            sb = cand.get("sandbox")
            if sb:
                sb.cleanup()

    eval_summary = [
        {k: v for k, v in c.items() if k not in ("wt_path", "sandbox")}
        for c in candidates_eval
    ]
    log_scheduler_event("ARENA_EVALUATION", {"task_id": task_id, "candidates": eval_summary, "winner": winner["runner"]}, workspace_root)

    print("\n" + "=" * 68)
    print(f"ARENA WINNER SELECTED: {winner['runner'].upper()} (Score: {winner['score']})")
    print(f"Winning Artifact SHA256: {winner['sha256']}")
    print("=" * 68)
    return 0


def execute_resume(
    workspace_root: Path,
    state_path: Path | None = None,
    dry_run: bool = False,
) -> int:
    state_file = state_path or (workspace_root / ".agents" / "handoffs" / "dag-state.json")
    if not state_file.is_file():
        print(f"[Resume] No existing dag-state.json found at {state_file}. Nothing to resume.")
        return 0

    state = load_dag_state(workspace_root, state_file)
    nodes = state.get("nodes", {})
    if not nodes:
        print("[Resume] State file contains 0 nodes.")
        return 0

    topo_order = topological_sort_nodes(nodes)
    levels = topological_levels(nodes)
    print("=" * 68)
    print(f"PSTACK v3.1 DAG CHECKPOINT RESUME: {state.get('task_id', 'unknown')}")
    print(f"Total Nodes: {len(nodes)} | Order: {' -> '.join(topo_order)}")
    print("=" * 68)

    state_lock = threading.Lock()
    wave_merged_files: set[str] = set()
    scripts_dir = Path(__file__).resolve().parent
    resumed_count = 0

    for level_nodes in levels:
        ready_nodes: list[str] = []
        for node_id in level_nodes:
            node = nodes[node_id]
            status = node.get("status")
            sha = node.get("artifact_sha256")
            if status in ("VERIFIED", "MERGED") and sha:
                wave_merged_files.update(node.get("merged_files", []))
                print(f"  [CHECKPOINT SKIP] Node `{node_id}` already {status} (sha256={sha})")
                continue
            print(f"  [RESUMING] Idempotent restart of node `{node_id}` (previous status: {status})")
            resumed_count += 1
            ready_nodes.append(node_id)

        if not ready_nodes:
            continue

        wave_base_files = sorted(wave_merged_files)
        wave_failed = False
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(ready_nodes))) as pool:
            futures = {
                pool.submit(
                    _execute_swarm_node,
                    nid,
                    state,
                    workspace_root,
                    state_file,
                    state_lock,
                    wave_merged_files,
                    dry_run,
                    scripts_dir,
                    "resumed-",
                    wave_base_files,
                ): nid
                for nid in ready_nodes
            }
            for fut in concurrent.futures.as_completed(futures):
                ok, msg = fut.result()
                if msg:
                    print(msg)
                if not ok:
                    wave_failed = True

        if wave_failed:
            state["status"] = "failed"
            save_dag_state(state, workspace_root, state_file)
            return 1

    state["status"] = "completed"
    save_dag_state(state, workspace_root, state_file)
    log_scheduler_event("RESUME_COMPLETED", {"resumed_count": resumed_count}, workspace_root)
    print("=" * 68)
    print(f"STATUS : RESUME FINISHED ({resumed_count} nodes executed)")
    print("=" * 68)
    return 0


def extract_gate_failure_digest(output: str, max_lines: int = 8) -> str:
    raw_lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    priority_markers = (
        "x ", "[FAIL]", "FAILED", "Error", "error:", "violation",
        "[Comment", "[Swallowed", "[Dash", "[Slop", "[Broken",
        "[Out-of-Bounds", "[Scope", "[Malformed", "[Dangling", "AssertionError",
    )
    selected: list[str] = []
    for ln in raw_lines:
        if any(marker in ln for marker in priority_markers):
            clean = ln[2:].strip() if ln.startswith("x ") else ln.strip()
            if clean not in selected:
                selected.append(clean)
        if len(selected) >= max_lines:
            break
    if not selected:
        selected = raw_lines[-max_lines:] if raw_lines else ["verification exited non-zero"]
    digest = " | ".join(selected[:max_lines])
    return digest[:320]


def inject_rework_directive(
    brief_path: Path,
    round_num: int,
    digest: str,
    workspace_root: Path,
) -> None:
    if not brief_path.is_file():
        ensure_workspace_skeleton(workspace_root)
    text = brief_path.read_text(encoding="utf-8")
    directive_line = f"- [Round {round_num} Auto-Rework] Fix gate failure: {digest}"

    sec2_header = "## 2. Consolidated Directives (History & Delta)"
    m = re.search(r"(## 2\. Consolidated Directives \(History & Delta\)\s*\n)([\s\S]*?)(?=\n## |\Z)", text)
    if m:
        sec_body = m.group(2).rstrip()
        new_sec = f"{m.group(1)}{sec_body}\n{directive_line}\n" if sec_body else f"{m.group(1)}{directive_line}\n"
        updated = text[:m.start()] + new_sec + text[m.end():]
    else:
        updated = text.rstrip() + f"\n\n{sec2_header}\n{directive_line}\n"

    brief_path.write_text(updated, encoding="utf-8")

    handoff_script = Path(__file__).resolve().parent / "verify-handoff.py"
    if handoff_script.is_file():
        env = os.environ.copy()
        env["PSTACK_WORKSPACE"] = str(workspace_root)
        subprocess.run(
            [sys.executable, str(handoff_script), str(brief_path), "--fix"],
            cwd=workspace_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )


def _normalize_step_result(res: object) -> tuple[int, str]:
    if isinstance(res, subprocess.CompletedProcess):
        out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
        return int(res.returncode), out
    if isinstance(res, tuple) and len(res) >= 2:
        return int(res[0]), str(res[1])
    if isinstance(res, bool):
        return (0 if res else 1), ""
    if isinstance(res, int):
        return res, ""
    return 0, str(res or "")


def run_with_auto_rework(
    workspace_root: Path,
    brief_path: Path | None = None,
    runner: str | Callable = "codex",
    max_rework: int = 2,
    verify_fn: Callable | None = None,
    verify_cmd: str | None = None,
) -> dict[str, object]:
    ws = workspace_root.resolve()
    ensure_workspace_skeleton(ws)
    target_brief = brief_path or (ws / ".agents" / "handoffs" / "active-brief.md")

    brief_text = target_brief.read_text(encoding="utf-8", errors="ignore") if target_brief.is_file() else ""
    tid_match = re.search(r'^task_id:\s*["\']?([^"\'\n]+)["\']?', brief_text, re.MULTILINE)
    task_id = tid_match.group(1).strip() if tid_match else "auto-rework-task"

    scripts_dir = Path(__file__).resolve().parent
    spawn_script = scripts_dir / "ag-spawn.sh"
    verify_script = scripts_dir / "pstack-verify.py"

    rework_count = 0
    round_num = 1
    last_digest = ""

    while True:
        if callable(runner):
            sig = inspect.signature(runner)
            param_count = len(sig.parameters)
            if param_count == 0:
                raw_run = runner()
            elif param_count == 1:
                raw_run = runner(round_num)
            else:
                raw_run = runner(round_num, target_brief)
            run_rc, run_out = _normalize_step_result(raw_run)
        else:
            spawn_env = os.environ.copy()
            spawn_env["PSTACK_WORKSPACE"] = str(ws)
            spawn_env["PSTACK_MAX_REWORK"] = "0"
            proc = subprocess.run(
                [str(spawn_script), str(target_brief), str(runner)],
                cwd=ws,
                env=spawn_env,
                capture_output=True,
                text=True,
                check=False,
            )
            run_rc = proc.returncode
            run_out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")

        if run_rc != 0:
            v_rc, v_out = run_rc, run_out
        elif verify_fn is not None:
            vsig = inspect.signature(verify_fn)
            raw_ver = verify_fn() if len(vsig.parameters) == 0 else verify_fn(ws)
            v_rc, v_out = _normalize_step_result(raw_ver)
        elif verify_cmd:
            v_env = os.environ.copy()
            v_env["PSTACK_WORKSPACE"] = str(ws)
            vproc = subprocess.run(
                verify_cmd,
                shell=True,
                cwd=ws,
                env=v_env,
                capture_output=True,
                text=True,
                check=False,
            )
            v_rc = vproc.returncode
            v_out = (vproc.stdout or "") + ("\n" + vproc.stderr if vproc.stderr else "")
        else:
            v_env = os.environ.copy()
            v_env["PSTACK_WORKSPACE"] = str(ws)
            vproc = subprocess.run(
                [sys.executable, str(verify_script), "all", str(target_brief)],
                cwd=ws,
                env=v_env,
                capture_output=True,
                text=True,
                check=False,
            )
            v_rc = vproc.returncode
            v_out = (vproc.stdout or "") + ("\n" + vproc.stderr if vproc.stderr else "")

        if v_rc == 0:
            if rework_count > 0:
                log_scheduler_event(
                    "AUTO_REWORK_RESOLVED",
                    {"task_id": task_id, "round": round_num, "rework_count": rework_count},
                    ws,
                )
            return {
                "exit_code": 0,
                "returncode": 0,
                "rework_count": rework_count,
                "rounds": round_num,
                "last_digest": last_digest,
            }

        last_digest = extract_gate_failure_digest(v_out)
        if round_num <= max_rework:
            next_round = round_num + 1
            rework_count += 1
            inject_rework_directive(target_brief, next_round, last_digest, ws)
            log_scheduler_event(
                "AUTO_REWORK_TRIGGERED",
                {
                    "task_id": task_id,
                    "round": next_round,
                    "rework_count": rework_count,
                    "brief_path": str(target_brief),
                    "digest": last_digest,
                },
                ws,
            )
            print(
                f"[pstack auto-rework] Round {round_num} gate failed; "
                f"triggering Round {next_round} ({rework_count}/{max_rework}): {last_digest}"
            )
            round_num = next_round
            continue

        log_scheduler_event(
            "AUTO_REWORK_EXHAUSTED",
            {
                "task_id": task_id,
                "round": round_num,
                "rework_count": rework_count,
                "digest": last_digest,
            },
            ws,
        )
        return {
            "exit_code": v_rc or 1,
            "returncode": v_rc or 1,
            "rework_count": rework_count,
            "rounds": round_num,
            "last_digest": last_digest,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack Git Worktree Agent Scheduler")
    subparsers = parser.add_subparsers(dest="command")

    swarm_p = subparsers.add_parser("swarm", help="Execute multi-node DAG in isolated worktrees")
    swarm_p.add_argument("--goal", type=str, default=None, help="High level task goal")
    swarm_p.add_argument("--spec", type=Path, default=None, help="Path to custom DAG JSON spec")
    swarm_p.add_argument("--dry-run", action="store_true", help="Simulate execution")

    arena_p = subparsers.add_parser("arena", help="Multi-agent competition in separate worktrees")
    arena_p.add_argument("--runners", default="codex,opencode", help="Comma-separated runners")
    arena_p.add_argument("--brief", type=Path, default=None, help="Handoff brief path")
    arena_p.add_argument("--dry-run", action="store_true", help="Simulate execution")

    resume_p = subparsers.add_parser("resume", help="Resume interrupted DAG execution")
    resume_p.add_argument("--state", type=Path, default=None, help="Path to dag-state.json")
    resume_p.add_argument("--dry-run", action="store_true", help="Simulate execution")

    rework_p = subparsers.add_parser("auto-rework", help="Run stateless subagent with bounded auto-rework loop")
    rework_p.add_argument("--brief", type=Path, default=None, help="Handoff brief path")
    rework_p.add_argument("--runner", default="codex", help="Target runner")
    rework_p.add_argument("--max-rework", type=int, default=2, help="Max rework rounds")
    rework_p.add_argument("--verify-cmd", type=str, default=None, help="Custom verification command")

    args = parser.parse_args()
    ws = get_workspace_root()

    if args.command == "swarm":
        return execute_swarm(ws, goal=args.goal, spec_path=args.spec, dry_run=args.dry_run)
    if args.command == "arena":
        runners = [r.strip() for r in args.runners.split(",") if r.strip()]
        return execute_arena(ws, runners=runners, brief_path=args.brief, dry_run=args.dry_run)
    if args.command == "resume":
        return execute_resume(ws, state_path=args.state, dry_run=args.dry_run)
    if args.command == "auto-rework":
        res = run_with_auto_rework(
            ws,
            brief_path=args.brief,
            runner=args.runner,
            max_rework=args.max_rework,
            verify_cmd=args.verify_cmd,
        )
        return int(res["exit_code"])

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
