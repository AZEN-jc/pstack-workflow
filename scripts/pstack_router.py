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


FUZZY_MARKERS = (
    "我想做", "想搞个", "能不能做", "类似", "不知道怎么叫", "概念", "想法", "优化一下体验",
    "觉得不好用", "感觉", "方向", "怎么做比较好", "有什么方案", "模糊", "不太确定",
    "something like", "not sure what it's called", "vague", "idea", "brainstorm", "how should i",
)
TRIVIAL_MARKERS = (
    "typo", "拼写", "改文案", "改个名", "重命名", "rename", "格式", "format", "bump", "版本号",
    "注释", "log", "打印", "小修", "一行", "错别字",
)
DEEP_MARKERS = (
    "架构", "重构", "状态机", "并行", "调度", "协议", "安全", "性能", "跨模块", "自动化", "工作流",
    "引擎", "门禁", "迁移", "系统", "architecture", "refactor", "scheduler", "protocol", "distributed",
    "migration", "pipeline", "automation", "workflow", "engine",
)


def assess_clarity(goal: str, pointers: list[str] | None = None, models_cfg: dict | None = None) -> dict:
    raw = goal.strip()
    text = raw.lower()
    classification = classify_goal(raw, models_cfg)

    has_explicit_code_ref = bool(re.search(r"[A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|go|rs|sh|md|json|yaml|yml)\b", raw))
    has_symbol_ref = bool(re.search(r"(?:#[A-Za-z_][A-Za-z0-9_]*|`[^`]+`|[a-z]+_[a-z0-9_]+)", raw))
    has_fuzzy_marker = any(m in text for m in FUZZY_MARKERS)
    has_trivial_marker = any(m in text for m in TRIVIAL_MARKERS)
    has_deep_marker = any(m in text for m in DEEP_MARKERS)

    reasons: list[str] = []
    if has_fuzzy_marker and not (has_explicit_code_ref and has_symbol_ref):
        level = "L2_FUZZY"
        reasons.append("matched fuzzy/exploratory phrasing without concrete code+symbol anchor")
        pipeline = ["reframe", "sharpen", "decision_gate", "route_from_sharpen"]
        requires_decision = True
    elif len(raw) <= 28 and not has_explicit_code_ref and not has_symbol_ref and not has_trivial_marker:
        level = "L2_FUZZY"
        reasons.append("short underspecified request lacking concrete file/symbol anchors")
        pipeline = ["reframe", "sharpen", "decision_gate", "route_from_sharpen"]
        requires_decision = True
    elif has_trivial_marker and not has_deep_marker and classification["complexity"] == "simple":
        level = "L0_TRIVIAL"
        reasons.append("matched trivial/localized edit pattern with simple complexity")
        pipeline = ["route_and_execute"]
        requires_decision = False
    elif (
        has_deep_marker
        or classification["complexity"] == "complex"
        or classification["intent"] in ("architecture-feature", "refactor", "swarm", "figure-it-out")
    ):
        level = "L1_CLEAR_DEEP"
        reasons.append(f"clear goal with deep scope (intent={classification['intent']}, complexity={classification['complexity']})")
        pipeline = ["sharpen", "decision_gate", "route_from_sharpen"]
        requires_decision = True
    else:
        level = "L0_TRIVIAL"
        reasons.append("concrete simple task eligible for direct execution")
        pipeline = ["route_and_execute"]
        requires_decision = False

    return {
        "level": level,
        "requires_decision": requires_decision,
        "recommended_pipeline": pipeline,
        "reasons": reasons,
        "has_code_anchor": has_explicit_code_ref or has_symbol_ref,
        "discovered_pointers_count": len(pointers) if pointers is not None else 0,
    }


BILINGUAL_LEXICON: dict[str, tuple[str, ...]] = {
    "状态机": ("state", "dag", "session", "snapshot"),
    "状态": ("state", "dag", "session", "snapshot", "status"),
    "超时": ("timeout", "spawn"),
    "恢复": ("resume", "pickup", "pause", "session", "quarantine"),
    "断点": ("resume", "pickup", "pause", "session", "quarantine", "snapshot"),
    "续传": ("resume", "pickup", "pause", "session", "quarantine"),
    "路由": ("route", "router", "classify", "model"),
    "意图": ("route", "router", "classify", "model", "intent"),
    "门禁": ("verify", "gate", "handoff", "prose", "slop"),
    "校验": ("verify", "gate", "handoff", "prose", "slop"),
    "检查": ("verify", "gate", "handoff", "prose", "slop"),
    "工作树": ("worktree", "sandbox", "swarm", "arena", "scheduler"),
    "沙箱": ("worktree", "sandbox", "swarm", "arena", "scheduler"),
    "并行": ("worktree", "sandbox", "swarm", "arena", "scheduler", "parallel"),
    "竞技": ("worktree", "sandbox", "swarm", "arena", "scheduler"),
    "基准": ("bench", "benchmark", "ab", "abcd"),
    "实验": ("bench", "benchmark", "ab", "abcd"),
    "跑分": ("bench", "benchmark", "ab", "abcd"),
    "更新": ("update", "remote", "bootstrap"),
    "同步": ("update", "remote", "bootstrap"),
    "树": ("tree", "event", "ascii"),
    "事件": ("tree", "event", "ascii"),
    "可视化": ("tree", "event", "ascii"),
    "钩子": ("hook", "pre-commit"),
    "预提交": ("hook", "pre-commit"),
    "提交前": ("hook", "pre-commit"),
    "协议": ("mcp", "jsonrpc", "stdio"),
    "异常": ("error", "fail", "crash", "recovery", "quarantine"),
    "崩溃": ("crash", "quarantine", "recovery", "spawn"),
    "返工": ("rework", "heal", "retry"),
    "自愈": ("rework", "heal", "fix"),
    "合并": ("merge", "apply", "conflict", "worktree"),
    "冲突": ("merge", "conflict", "worktree"),
    "权限": ("scope", "allowed", "violation"),
    "白名单": ("scope", "allowed", "violation"),
    "越权": ("scope", "allowed", "violation"),
}

SUPPORTED_CODE_EXTENSIONS = (".py", ".ts", ".tsx", ".js", ".go", ".rs", ".sh")
REPOMAP_SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build", ".agents",
}
SHELL_CONTROL_KEYWORDS = {"if", "for", "while", "until", "case", "select", "else", "elif"}


def _split_identifier_tokens(identifier: str) -> set[str]:
    tokens: set[str] = set()
    for seg in re.split(r"[^A-Za-z0-9]+", identifier):
        if not seg:
            continue
        tokens.add(seg.lower())
        camel_parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", seg).split()
        for part in camel_parts:
            if part:
                tokens.add(part.lower())
    return tokens


def _extract_bilingual_terms(goal_text: str) -> tuple[set[str], set[str]]:
    ascii_keywords = _split_identifier_tokens(goal_text)
    cjk_terms: set[str] = set()

    for zh_key, en_terms in BILINGUAL_LEXICON.items():
        if zh_key in goal_text:
            cjk_terms.add(zh_key)
            ascii_keywords.update(en_terms)

    for run in re.findall(r"[\u4e00-\u9fff]+", goal_text):
        if len(run) >= 2:
            cjk_terms.add(run)
            for idx in range(len(run) - 1):
                cjk_terms.add(run[idx:idx + 2])

    return ascii_keywords, cjk_terms


def _extract_ast_symbols(file_path: Path, content: str | None = None) -> list[tuple[int, int, str]]:
    symbols: list[tuple[int, int, str]] = []
    try:
        raw = content if content is not None else file_path.read_text(encoding="utf-8")
        tree = ast.parse(raw, filename=str(file_path))
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


def _is_rust_char_literal(line: str, idx: int) -> bool:
    n = len(line)
    if idx + 2 >= n:
        return False
    nxt = line[idx + 1]
    if nxt == "\\":
        j = idx + 2
        while j < n:
            if line[j] == "\\":
                j += 2
                continue
            if line[j] == "'":
                return True
            if line[j].isspace() or line[j] in ";,)>}":
                return False
            j += 1
        return False
    return nxt != "'" and line[idx + 2] == "'"


def _count_code_braces(lines: list[str], start_line: int, suffix: str) -> int | None:
    brace_depth = 0
    saw_open_brace = False
    in_block_comment = False
    quote_char: str | None = None

    for idx in range(start_line, len(lines) + 1):
        line = lines[idx - 1]
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            nxt = line[i + 1] if i + 1 < n else ""

            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if quote_char is not None:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote_char:
                    quote_char = None
                i += 1
                continue

            if suffix != ".sh" and ch == "/" and nxt == "/":
                break
            if suffix != ".sh" and ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if suffix == ".sh" and ch == "#" and (i == 0 or line[i - 1].isspace()):
                break

            if ch == "'" and suffix == ".rs" and not _is_rust_char_literal(line, i):
                i += 1
                continue

            if ch in ("'", '"', "`"):
                quote_char = ch
                i += 1
                continue

            if ch == "{":
                saw_open_brace = True
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if saw_open_brace and brace_depth <= 0:
                    return idx
            i += 1

    return None


def _extract_multilang_symbols(file_path: Path, content: str) -> list[tuple[int, int, str]]:
    suffix = file_path.suffix.lower()
    lines = content.splitlines()
    symbols: list[tuple[int, int, str]] = []
    seen_names: set[str] = set()

    if suffix == ".sh":
        pat_sh_paren = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*\{?")
        pat_sh_kw = re.compile(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\b")
        for idx, line in enumerate(lines, 1):
            m = pat_sh_paren.match(line) or pat_sh_kw.match(line)
            if not m:
                continue
            name = m.group(1)
            if name in SHELL_CONTROL_KEYWORDS or name in seen_names:
                continue
            end_line = _count_code_braces(lines, idx, suffix) or idx
            seen_names.add(name)
            symbols.append((idx, end_line, name))
        return symbols

    if suffix in (".ts", ".tsx", ".js"):
        pat_ts_decl = re.compile(
            r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function|class|interface|type|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\b"
        )
        pat_ts_var = re.compile(
            r"^\s*(?:export\s+)?(?:const|let)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=\s*(?:async\s+)?(?:<[^>]+>\s*)?(?:function\b|\([^)]*\)\s*(?::[^=>{]+)?=>|[A-Za-z_][A-Za-z0-9_]*\s*=>)"
        )
        for idx, line in enumerate(lines, 1):
            m = pat_ts_decl.match(line) or pat_ts_var.match(line)
            if not m:
                continue
            name = m.group(1)
            if name in seen_names:
                continue
            end_line = _count_code_braces(lines, idx, suffix)
            if end_line is None:
                end_line = idx
            seen_names.add(name)
            symbols.append((idx, end_line, name))
        return symbols

    if suffix == ".go":
        pat_go = re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\b")
        pat_go_type = re.compile(r"^\s*type\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)\b")
        for idx, line in enumerate(lines, 1):
            m = pat_go.match(line) or pat_go_type.match(line)
            if not m:
                continue
            name = m.group(1)
            if name in seen_names:
                continue
            end_line = _count_code_braces(lines, idx, suffix) or idx
            seen_names.add(name)
            symbols.append((idx, end_line, name))
        return symbols

    if suffix == ".rs":
        pat_rs = re.compile(
            r"^\s*(?:pub(?:\s*\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?(?:const\s+)?(?:fn|struct|enum|trait|impl)\s+([A-Za-z_][A-Za-z0-9_]*)\b"
        )
        for idx, line in enumerate(lines, 1):
            m = pat_rs.match(line)
            if not m:
                continue
            name = m.group(1)
            if name in seen_names:
                continue
            end_line = _count_code_braces(lines, idx, suffix) or idx
            seen_names.add(name)
            symbols.append((idx, end_line, name))
        return symbols

    return symbols


def _extract_file_symbols(file_path: Path, content: str) -> list[tuple[int, int, str]]:
    if file_path.suffix.lower() == ".py":
        return _extract_ast_symbols(file_path, content)
    return _extract_multilang_symbols(file_path, content)


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

    ascii_keywords, cjk_terms = _extract_bilingual_terms(goal_text)
    candidate_files: list[Path] = []
    seen_files: set[Path] = set()
    git_modified_files: set[Path] = set()

    def add_candidate(p: Path) -> None:
        if not p.is_file() or p.suffix.lower() not in SUPPORTED_CODE_EXTENSIONS:
            return
        resolved = p.resolve()
        if resolved not in seen_files:
            seen_files.add(resolved)
            candidate_files.append(p)

    proc = subprocess.run(
        ["git", "-c", "core.quotePath=false", "status", "--porcelain"],
        cwd=ws_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            if len(line) < 4:
                continue
            line_clean = line[3:].strip()
            if " -> " in line_clean:
                line_clean = line_clean.split(" -> ")[1].strip()
            if line_clean.startswith('"') and line_clean.endswith('"'):
                line_clean = line_clean[1:-1]
            p = ws_root / line_clean
            if p.is_file() and p.suffix.lower() in SUPPORTED_CODE_EXTENSIONS:
                git_modified_files.add(p.resolve())
                add_candidate(p)

    for top_file in sorted(ws_root.glob("*")):
        add_candidate(top_file)

    for sdir_name in ("src", "scripts", "tests", "lib", "app", "pkg", "cmd", "internal", "packages"):
        sdir = ws_root / sdir_name
        if not sdir.is_dir():
            continue
        for root_str, dirs, files in os.walk(sdir):
            dirs[:] = sorted(d for d in dirs if d not in REPOMAP_SKIP_DIRS)
            for fname in sorted(files):
                add_candidate(Path(root_str) / fname)

    file_texts: dict[Path, str] = {}
    file_lines: dict[Path, list[str]] = {}
    file_header_tokens: dict[Path, set[str]] = {}
    for cand in candidate_files:
        try:
            raw = cand.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = raw.splitlines()
        file_texts[cand] = raw
        file_lines[cand] = lines
        header_text = "\n".join(lines[:20])
        file_header_tokens[cand] = _split_identifier_tokens(header_text)

    ranked_candidates: list[tuple[int, int, int, str, int, int, str]] = []
    for cand in candidate_files:
        if cand not in file_texts:
            continue
        raw = file_texts[cand]
        lines = file_lines[cand]
        header_tokens = file_header_tokens[cand]
        header_text = "\n".join(lines[:20])
        try:
            rel = cand.relative_to(ws_root).as_posix()
        except ValueError:
            rel = cand.name

        symbols = _extract_file_symbols(cand, raw)
        if not symbols:
            continue

        stem_lower = cand.stem.lower()
        name_lower = cand.name.lower()
        ref_count = 0
        if len(stem_lower) >= 3:
            stem_re = re.compile(rf"\b{re.escape(stem_lower)}\b")
            for other_cand, other_text in file_texts.items():
                if other_cand == cand:
                    continue
                other_lower = other_text.lower()
                if name_lower in other_lower or stem_re.search(other_lower):
                    ref_count += 1

        git_bonus = 1 if cand.resolve() in git_modified_files else 0
        stem_tokens = _split_identifier_tokens(cand.stem)

        for s_start, s_end, s_name in symbols:
            sym_tokens = _split_identifier_tokens(s_name) | stem_tokens
            sym_hits = sum(1 for kw in ascii_keywords if kw in sym_tokens)
            sym_hits += sum(1 for term in cjk_terms if term in s_name)

            span_end = min(len(lines), s_end, s_start + 80)
            span_text = "\n".join(lines[max(0, s_start - 1):span_end])
            span_tokens = _split_identifier_tokens(span_text) | header_tokens
            combined_span_raw = span_text + "\n" + header_text
            content_hits = sum(1 for kw in ascii_keywords if kw in span_tokens)
            content_hits += sum(1 for term in cjk_terms if term in combined_span_raw)

            ref_bonus = min(ref_count, 4) if (sym_hits + content_hits) > 0 else 0
            effective_git_bonus = (2 if sym_hits > 0 else 1) if (git_bonus and (sym_hits + content_hits) > 0) else 0
            score = (sym_hits * 5) + (content_hits * 2) + ref_bonus + effective_git_bonus
            ranked_candidates.append((score, sym_hits, ref_count, rel, s_start, s_end, s_name))

    ranked_candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3], item[4]))

    discovered_pointers: list[str] = []
    touched_dirs: set[str] = set()
    per_file_counts: dict[str, int] = {}

    for score, sym_hits, ref_count, rel, s_start, s_end, s_name in ranked_candidates:
        if per_file_counts.get(rel, 0) >= 2:
            continue
        per_file_counts[rel] = per_file_counts.get(rel, 0) + 1
        discovered_pointers.append(f"{rel}:{s_start}-{s_end}#{s_name}")
        parts = rel.split("/")
        if len(parts) > 1:
            touched_dirs.add(f"{parts[0]}/*")
        if len(discovered_pointers) >= 6:
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


def run_cli(goal: str, runner: str, dry_run: bool, max_rework: int = 0) -> int:
    ws = get_workspace_root()
    brief_path = generate_brief(goal, ws)
    print(f"[Pstack Run] Successfully routed and created brief: {brief_path}")

    if dry_run:
        print(f"[Pstack Run] DRY-RUN mode active (runner={runner}). Skipping subagent dispatch.")
        log_event("RUN_SIMULATED", {"goal": goal, "runner": runner, "brief": str(brief_path)}, ws)
        return 0

    log_event("RUN_START", {"goal": goal, "runner": runner, "brief": str(brief_path), "max_rework": max_rework}, ws)
    if max_rework > 0:
        from pstack_scheduler import run_with_auto_rework

        res = run_with_auto_rework(ws, brief_path=brief_path, runner=runner, max_rework=max_rework)
        return int(res["exit_code"])

    spawn_script = Path(__file__).resolve().parent / "ag-spawn.sh"
    if spawn_script.is_file() and os.access(spawn_script, os.X_OK):
        proc = subprocess.run([str(spawn_script), str(brief_path), runner], cwd=ws, check=False)
        return proc.returncode

    verify_script = Path(__file__).resolve().parent / "pstack-verify.py"
    proc = subprocess.run([sys.executable, str(verify_script), "all"], cwd=ws, check=False)
    return proc.returncode


def load_sharpened_prompt(workspace_root: Path | None = None) -> str:
    ws = (workspace_root or get_workspace_root()).resolve()
    staged_path = ws / ".agents" / "handoffs" / "sharpened-prompt.md"
    if not staged_path.is_file():
        raise FileNotFoundError(f"Staged prompt not found: {staged_path} (run /sharpen first)")
    content = staged_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Staged prompt is empty: {staged_path}")
    return content


def _resolve_cli_goal(raw_goal: str, from_sharpen: bool) -> str:
    if from_sharpen:
        return load_sharpened_prompt(get_workspace_root())
    goal_text = raw_goal.strip()
    if not goal_text:
        raise ValueError("Missing goal text. Provide a goal argument or pass --from-sharpen.")
    return goal_text


def auto_cli(
    goal: str,
    runner: str,
    dry_run: bool,
    approved: bool,
    json_mode: bool,
    max_rework: int = 2,
) -> int:
    ws = get_workspace_root()
    staged_path = ws / ".agents" / "handoffs" / "sharpened-prompt.md"
    has_staged = staged_path.is_file() and bool(staged_path.read_text(encoding="utf-8").strip())

    if approved and has_staged:
        staged_goal = load_sharpened_prompt(ws)
        if json_mode:
            brief_file = generate_brief(staged_goal, ws)
            payload = {
                "status": "APPROVED_ROUTED" if dry_run else "APPROVED_EXECUTING",
                "source": "sharpened-prompt.md",
                "brief_path": str(brief_file),
                "runner": runner,
                "max_rework": max_rework,
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        return run_cli(staged_goal, runner, dry_run, max_rework=max_rework)

    goal_text = goal.strip()
    if not goal_text:
        raise ValueError("Missing goal text. Provide a goal argument or stage .agents/handoffs/sharpened-prompt.md with --approved.")

    cfg = load_models_config(ws)
    classification = classify_goal(goal_text, cfg)
    pointers, allowed_paths = auto_discover_pointers_and_scope(goal_text, ws)
    clarity = assess_clarity(goal_text, pointers=pointers, models_cfg=cfg)

    if clarity["level"] == "L0_TRIVIAL" and approved:
        return run_cli(goal_text, runner, dry_run, max_rework=max_rework)

    payload = {
        "status": "READY_DIRECT_EXECUTION" if clarity["level"] == "L0_TRIVIAL" else "AWAITING_DECISION",
        "goal": goal_text,
        "clarity": clarity,
        "classification": classification,
        "allowed_paths": allowed_paths,
        "pointers": pointers,
        "has_staged_prompt": has_staged,
        "staged_prompt_path": str(staged_path),
    }

    if json_mode:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print("=" * 68)
    print("PSTACK v3.3 AUTONOMOUS PRE-FLIGHT FUNNEL (HUMAN-ONLY-DECIDES)")
    print("=" * 68)
    print(f"GOAL        : {goal_text}")
    print(f"CLARITY     : {clarity['level']} (decision_gate={clarity['requires_decision']})")
    print(f"PIPELINE    : {' -> '.join(clarity['recommended_pipeline'])}")
    print(f"INTENT      : {classification['intent']} ({classification['complexity']})")
    print(f"POINTERS    : {len(pointers)} AST symbols anchored")
    print(f"STAGED FILE : {staged_path} ({'present' if has_staged else 'not yet staged'})")
    print("=" * 68)
    if clarity["level"] == "L0_TRIVIAL":
        print("[NEXT] Trivial clear task. Re-run with `--approved` or `pstack run` to execute directly.")
    else:
        print("[NEXT] Read-only triage complete (no code modified). Run pre-flight skills, approve Decision Gate, then execute `pstack auto --approved --max-rework 2`.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack Zero-Token Task Router & 5-Role Model Matrix")
    subparsers = parser.add_subparsers(dest="command")

    route_p = subparsers.add_parser("route", help="Route goal, discover AST pointers, write active-brief.md")
    route_p.add_argument("goal", type=str, nargs="?", default="", help="Natural language goal or task prompt")
    route_p.add_argument(
        "--from-sharpen",
        action="store_true",
        help="Load goal from .agents/handoffs/sharpened-prompt.md",
    )
    route_p.add_argument("--output", type=Path, default=None, help="Custom output brief path")
    route_p.add_argument("--json", action="store_true", help="Output routing decision as JSON")

    run_p = subparsers.add_parser("run", help="Route goal and trigger execution loop")
    run_p.add_argument("goal", type=str, nargs="?", default="", help="Natural language goal or task prompt")
    run_p.add_argument(
        "--from-sharpen",
        action="store_true",
        help="Load goal from .agents/handoffs/sharpened-prompt.md",
    )
    run_p.add_argument("--runner", default="antigravity", help="Target agent runner")
    run_p.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying files")
    run_p.add_argument(
        "--max-rework",
        type=int,
        default=int(os.environ.get("PSTACK_MAX_REWORK", "0") or "0"),
        help="Bounded auto-rework rounds on gate failure",
    )

    auto_p = subparsers.add_parser("auto", help="Run L0/L1/L2 clarity triage and execute once Decision Gate is approved")
    auto_p.add_argument("goal", type=str, nargs="?", default="", help="Natural language goal or task prompt")
    auto_p.add_argument("--runner", default="antigravity", help="Target agent runner")
    auto_p.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying files")
    auto_p.add_argument("--approved", action="store_true", help="Decision Gate approved; execute staged or L0 goal")
    auto_p.add_argument("--json", action="store_true", help="Output triage payload as JSON")
    auto_p.add_argument(
        "--max-rework",
        type=int,
        default=int(os.environ.get("PSTACK_MAX_REWORK", "2") or "2"),
        help="Bounded auto-rework rounds on gate failure (default: 2)",
    )

    args = parser.parse_args()
    if args.command == "route":
        try:
            goal_text = _resolve_cli_goal(args.goal, args.from_sharpen)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        return route_cli(goal_text, args.output, args.json)
    if args.command == "run":
        try:
            goal_text = _resolve_cli_goal(args.goal, args.from_sharpen)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        return run_cli(goal_text, args.runner, args.dry_run, max_rework=args.max_rework)
    if args.command == "auto":
        try:
            return auto_cli(
                args.goal,
                args.runner,
                args.dry_run,
                approved=args.approved,
                json_mode=args.json,
                max_rework=args.max_rework,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
