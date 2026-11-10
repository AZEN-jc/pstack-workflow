#!/usr/bin/env python3
"""
pstack Zero-Token Task Router & 5-Role Model Matrix
Usage:
  python3 scripts/pstack_router.py route "<goal>" [--output <path>] [--json]
  python3 scripts/pstack_router.py run "<goal>" [--runner <runner>] [--dry-run]
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pstack_onboard import detect_verify_cmd
from pstack_resolver import ensure_workspace_skeleton, get_pstack_home, get_workspace_root, resolve_asset

DEFAULT_MODELS = {
    "version": "3.0",
    "tiers": {
        "fast_tier": {
            "description": "Fast low-token tier for simple tasks, auto-routing, and unit fixes",
            "default_model": "gemini-3.8-flash-high",
            "providers": {
                "gemini": "gemini-3.8-flash-high",
                "openai": "codex-mini",
                "anthropic": "claude-3-5-haiku",
            },
        },
        "deep_tier": {
            "description": "Deep reasoning tier for complex architecture, reviews, and root-cause analysis",
            "default_model": "gemini-2.5-pro",
            "providers": {
                "gemini": "gemini-2.5-pro",
                "openai": "codex-max",
                "anthropic": "claude-3-7-sonnet",
            },
        },
    },
    "roles": {
        "coordinator": {
            "default_tier": "fast_tier",
            "playbook": ".agents/pstack/playbooks/architecture-feature.md",
        },
        "architect": {
            "default_tier": "deep_tier",
            "playbook": ".agents/pstack/playbooks/architecture-feature.md",
        },
        "builder": {
            "default_tier": "fast_tier",
            "playbook": ".agents/pstack/playbooks/architecture-feature.md",
        },
        "reviewer": {
            "default_tier": "deep_tier",
            "playbook": ".agents/pstack/playbooks/interrogate.md",
        },
        "verifier": {
            "default_tier": "deep_tier",
            "playbook": ".agents/pstack/playbooks/interrogate.md",
        },
    },
}

INTENT_PLAYBOOKS = {
    "bug-fix": ".agents/pstack/playbooks/bug-fix.md",
    "architecture-feature": ".agents/pstack/playbooks/architecture-feature.md",
    "refactor": ".agents/pstack/playbooks/architecture-feature.md",
    "figure-it-out": ".agents/pstack/playbooks/figure-it-out.md",
    "interrogate": ".agents/pstack/playbooks/interrogate.md",
    "tech-thread": ".agents/pstack/playbooks/tech-thread.md",
    "build-in-public": ".agents/pstack/playbooks/build-in-public.md",
    "swarm": ".agents/pstack/playbooks/architecture-feature.md",
}


def load_models_config(workspace_root: Path | None = None) -> dict:
    resolved = resolve_asset(".agents/pstack/models.json", workspace_root)
    if resolved.is_file():
        try:
            return json.loads(resolved.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return DEFAULT_MODELS
    return DEFAULT_MODELS


def log_event(event_type: str, payload: dict, workspace_root: Path) -> None:
    events_file = workspace_root / ".agents" / "handoffs" / "events.jsonl"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    record = {"timestamp": ts, "event_type": event_type, **payload}
    with events_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def classify_goal(goal: str, models_cfg: dict | None = None) -> dict:
    cfg = models_cfg or DEFAULT_MODELS
    text = goal.strip().lower()

    if any(k in text for k in ("swarm", "multi-node", "dag", "parallel", "多阶段", "复合", "并行工作流")):
        intent = "swarm"
    elif any(k in text for k in ("fix", "bug", "issue", "error", "fail", "crash", "timeout", "修复", "报错", "崩溃", "超时", "缺陷")):
        intent = "bug-fix"
    elif any(k in text for k in ("refactor", "cleanup", "clean", "slop", "重构", "清理", "精简")):
        intent = "refactor"
    elif any(k in text for k in ("review", "audit", "interrogate", "security", "审查", "审计", "挑刺", "对抗")):
        intent = "interrogate"
    elif any(k in text for k in ("why", "how", "explore", "investigate", "trace", "调研", "排查", "追踪", "逆向")):
        intent = "figure-it-out"
    elif any(k in text for k in ("thread", "tweet", "推文", "串推", "连发")):
        intent = "tech-thread"
    elif any(k in text for k in ("build-in-public", "retro", "postmortem", "复盘", "公开构建", "演进")):
        intent = "build-in-public"
    else:
        intent = "architecture-feature"

    complex_markers = (
        "swarm", "distributed", "security", "architecture", "multi", "deep",
        "分布式", "架构", "多模块", "跨模块", "全量", "安全", "深入",
    )
    is_complex = len(goal) > 65 or any(m in text for m in complex_markers) or intent in ("swarm", "figure-it-out", "interrogate")
    complexity = "complex" if is_complex else "simple"

    if intent == "swarm":
        role = "coordinator"
        tier = "deep_tier" if complexity == "complex" else "fast_tier"
    elif intent == "interrogate":
        role = "reviewer"
        tier = "deep_tier"
    elif intent == "figure-it-out":
        role = "architect"
        tier = "deep_tier"
    elif intent == "architecture-feature":
        role = "architect" if complexity == "complex" else "builder"
        tier = "deep_tier" if complexity == "complex" else "fast_tier"
    else:
        role = "builder"
        tier = "deep_tier" if complexity == "complex" else "fast_tier"

    playbook = INTENT_PLAYBOOKS.get(intent, ".agents/pstack/playbooks/architecture-feature.md")
    tiers_info = cfg.get("tiers", {})
    tier_info = tiers_info.get(tier, {})
    model_name = tier_info.get("default_model", "gemini-3.8-flash-high" if tier == "fast_tier" else "gemini-2.5-pro")

    return {
        "intent": intent,
        "complexity": complexity,
        "role": role,
        "tier": tier,
        "model_tier": tier,
        "model": model_name,
        "playbook": playbook,
    }


def _extract_ast_symbols(file_path: Path) -> list[tuple[int, int, str]]:
    symbols: list[tuple[int, int, str]] = []
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return symbols

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append((node.lineno, getattr(node, "end_lineno", node.lineno), node.name))
        elif isinstance(node, ast.ClassDef):
            symbols.append((node.lineno, getattr(node, "end_lineno", node.lineno), node.name))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append((item.lineno, getattr(item, "end_lineno", item.lineno), f"{node.name}.{item.name}"))
    return symbols


def auto_discover_pointers_and_scope(
    goal: str | Path,
    workspace_root: Path | str | None = None,
) -> tuple[list[str], list[str]]:
    if isinstance(goal, Path) and isinstance(workspace_root, (str, Path)):
        goal_text = str(workspace_root)
        ws_root = goal
    elif isinstance(goal, Path) and workspace_root is None:
        goal_text = ""
        ws_root = goal
    elif isinstance(workspace_root, (str, Path)):
        goal_text = str(goal)
        ws_root = Path(workspace_root)
    else:
        goal_text = str(goal)
        ws_root = get_workspace_root()

    keywords = set(re.findall(r"[A-Za-z0-9_]+", goal_text.lower()))
    candidate_files: list[Path] = []

    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ws_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            line_clean = line[3:].strip()
            if " -> " in line_clean:
                line_clean = line_clean.split(" -> ")[1].strip()
            if line_clean.endswith(".py"):
                p = ws_root / line_clean
                if p.is_file():
                    candidate_files.append(p)

    search_dirs = [ws_root / "src", ws_root / "scripts", ws_root / "tests", ws_root / "lib"]
    for py_file in sorted(ws_root.glob("*.py")):
        if py_file not in candidate_files:
            candidate_files.append(py_file)
    for sdir in search_dirs:
        if sdir.is_dir():
            for py_file in sorted(sdir.glob("*.py")):
                if py_file not in candidate_files:
                    candidate_files.append(py_file)

    discovered_pointers: list[str] = []
    touched_dirs: set[str] = set()

    for cand in candidate_files:
        try:
            rel = cand.relative_to(ws_root).as_posix()
        except ValueError:
            rel = cand.name

        symbols = _extract_ast_symbols(cand)
        matched_symbols: list[tuple[int, int, str]] = []
        for s_start, s_end, s_name in symbols:
            name_parts = set(re.findall(r"[A-Za-z0-9_]+", s_name.lower()))
            if keywords.intersection(name_parts):
                matched_symbols.append((s_start, s_end, s_name))

        selected = matched_symbols if matched_symbols else symbols[:2]
        for s_start, s_end, s_name in selected[:2]:
            ptr = f"{rel}:{s_start}-{s_end}#{s_name}"
            discovered_pointers.append(ptr)
            parts = rel.split("/")
            if len(parts) > 1:
                touched_dirs.add(f"{parts[0]}/*")

        if len(discovered_pointers) >= 4:
            break

    if not discovered_pointers:
        if (ws_root / "scripts" / "pstack_resolver.py").is_file():
            discovered_pointers.append("scripts/pstack_resolver.py:69-84#get_pstack_home")
            discovered_pointers.append("scripts/pstack_resolver.py:87-101#get_workspace_root")
            touched_dirs.add("scripts/*")
        elif (ws_root / ".agents" / "decision.tsv").is_file():
            dec_lines = (ws_root / ".agents" / "decision.tsv").read_text(encoding="utf-8").splitlines()
            line_count = max(1, len(dec_lines))
            span = "1" if line_count == 1 else f"1-{min(line_count, 10)}"
            discovered_pointers.append(f".agents/decision.tsv:{span}")
            touched_dirs.add(".agents/*")
        else:
            discovered_pointers.append(".agents/pstack/pstack-core.md:1-10#剧本原样挂载")
            touched_dirs.add(".agents/*")

    allowed_paths = sorted(touched_dirs.union({".agents/*", "scripts/*", "tests/*"}))
    return discovered_pointers, allowed_paths


def generate_brief(
    goal: str | Path,
    workspace_root: Path | str | None = None,
    output_path: Path | None = None,
    models_cfg: dict | None = None,
) -> Path:
    if isinstance(goal, Path) and isinstance(workspace_root, (str, Path)):
        goal_text = str(workspace_root)
        ws_root = goal
    elif isinstance(goal, Path) and workspace_root is None:
        goal_text = ""
        ws_root = goal
    elif isinstance(workspace_root, (str, Path)):
        goal_text = str(goal)
        ws_root = Path(workspace_root)
    else:
        goal_text = str(goal)
        ws_root = get_workspace_root()

    ensure_workspace_skeleton(ws_root)
    cfg = models_cfg or load_models_config(ws_root)
    classification = classify_goal(goal_text, cfg)
    pointers, allowed_paths = auto_discover_pointers_and_scope(goal_text, ws_root)

    ts_slug = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    clean_goal_slug = re.sub(r"[^a-z0-9]+", "-", goal_text.lower().strip())[:24].strip("-")
    task_id = f"task-{clean_goal_slug}-{ts_slug}" if clean_goal_slug else f"task-{ts_slug}"

    verify_cmd = detect_verify_cmd(ws_root)
    if "pstack verify all" in verify_cmd:
        verify_cmd = "python3 -m unittest discover -s tests -q"

    paths_yaml = "\n".join(f'  - "{p}"' for p in allowed_paths)
    pointers_text = "\n".join(f"- `{p}`" for p in pointers)

    brief_content = f"""---
task_id: "{task_id}"
role: "{classification['role']}"
target_agent: "antigravity"
playbook: "{classification['playbook']}"
required_principles:
  - ".agents/pstack/principles/prove-it-works.md"
  - ".agents/pstack/principles/no-comments.md"
  - ".agents/pstack/principles/unslop-zh-en.md"
verify_cmd: "{verify_cmd}"
allowed_paths:
{paths_yaml}
model_tier: "{classification['tier']}"
---

## 1. User Goal (Restated)
{goal_text.strip()}

## 2. Consolidated Directives (History & Delta)
- [Auto-Routed] Intent classified as `{classification['intent']}` ({classification['complexity']}).
- [Model Matrix] Assigned role `{classification['role']}` routed to `{classification['tier']}` (`{classification['model']}`).
- [Scope Guard] Restricted to allowed paths whitelist.

## 3. Evidence Pointers (Read-Only Context)
{pointers_text}

## 4. Deliverable Contract
1. Complete implementation meeting the restated user goal.
2. Comply strictly with `allowed_paths` whitelist.
3. Pass deterministic verification command: `{verify_cmd}`.
"""
    dest = output_path or (ws_root / ".agents" / "handoffs" / "active-brief.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(brief_content, encoding="utf-8")

    log_event(
        "ROUTE_DECISION",
        {
            "task_id": task_id,
            "goal": goal_text.strip(),
            "classification": classification,
            "pointers_count": len(pointers),
            "allowed_paths": allowed_paths,
            "brief_path": str(dest),
        },
        ws_root,
    )
    return dest


def route_cli(goal: str, output: Path | None, json_mode: bool) -> int:
    ws = get_workspace_root()
    cfg = load_models_config(ws)
    classification = classify_goal(goal, cfg)
    brief_file = generate_brief(goal, ws, output_path=output, models_cfg=cfg)
    pointers, allowed_paths = auto_discover_pointers_and_scope(goal, ws)

    result = {
        "status": "ROUTED",
        "goal": goal,
        "classification": classification,
        "allowed_paths": allowed_paths,
        "pointers": pointers,
        "brief_path": str(brief_file),
    }

    if json_mode:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print("=" * 68)
    print("PSTACK v3.0 ZERO-TOKEN TASK ROUTER")
    print("=" * 68)
    print(f"GOAL        : {goal}")
    print(f"INTENT      : {classification['intent']} ({classification['complexity']})")
    print(f"ROLE & TIER : {classification['role']} -> {classification['tier']} ({classification['model']})")
    print(f"PLAYBOOK    : {classification['playbook']}")
    print(f"SCOPE LOCK  : {', '.join(allowed_paths)}")
    print(f"POINTERS    : {len(pointers)} valid AST symbols discovered")
    print(f"HANDOFF DOC : {brief_file}")
    print("=" * 68)
    print(f"[OK] Generated schema-compliant brief -> {brief_file}")
    return 0


def run_cli(goal: str, runner: str, dry_run: bool) -> int:
    ws = get_workspace_root()
    brief_path = generate_brief(goal, ws)
    print(f"[Pstack Run] Successfully routed and created brief: {brief_path}")

    if dry_run:
        print(f"[Pstack Run] DRY-RUN mode active (runner={runner}). Skipping subagent dispatch.")
        log_event("RUN_SIMULATED", {"goal": goal, "runner": runner, "brief": str(brief_path)}, ws)
        return 0

    log_event("RUN_START", {"goal": goal, "runner": runner, "brief": str(brief_path)}, ws)
    spawn_script = ws / "scripts" / "ag-spawn.sh"
    if spawn_script.is_file() and os.access(spawn_script, os.X_OK):
        proc = subprocess.run([str(spawn_script), str(brief_path), runner], cwd=ws, check=False)
        return proc.returncode

    verify_script = ws / "scripts" / "pstack-verify.py"
    proc = subprocess.run([sys.executable, str(verify_script), "all"], cwd=ws, check=False)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack Zero-Token Task Router & 5-Role Model Matrix")
    subparsers = parser.add_subparsers(dest="command")

    route_p = subparsers.add_parser("route", help="Route goal, discover AST pointers, write active-brief.md")
    route_p.add_argument("goal", type=str, help="Natural language goal or task prompt")
    route_p.add_argument("--output", type=Path, default=None, help="Custom output brief path")
    route_p.add_argument("--json", action="store_true", help="Output routing decision as JSON")

    run_p = subparsers.add_parser("run", help="Route goal and trigger execution loop")
    run_p.add_argument("goal", type=str, help="Natural language goal or task prompt")
    run_p.add_argument("--runner", default="antigravity", help="Target agent runner")
    run_p.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying files")

    args = parser.parse_args()
    if args.command == "route":
        return route_cli(args.goal, args.output, args.json)
    if args.command == "run":
        return run_cli(args.goal, args.runner, args.dry_run)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
