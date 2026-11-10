#!/usr/bin/env python3
"""
pstack Handoff Brief & Decision Ledger Verification Harness
Usage: python3 scripts/verify-handoff.py [brief_file] [--fix] [--ledger .agents/decision.tsv]
"""
import ast
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

from pstack_resolver import get_workspace_root, resolve_asset

VALID_VERDICTS = {"KEEP", "REVERT", "ROOT_CAUSE", "PERF_WIN"}
EXPECTED_TSV_COLS = [
    "timestamp", "task_id", "verdict", "hypothesis",
    "evidence_pointer", "metric_before", "metric_after", "lesson_learned"
]

POINTER_TOKEN_RE = re.compile(
    r"`([A-Za-z0-9_./-]+(?::\d+(?:-\d+)?)?(?:#[^\s`@]+)?(?:@[0-9a-fA-F]{4,40})?)`"
)
POINTER_PARSE_RE = re.compile(
    r"^([A-Za-z0-9_./-]+?)(?::(\d+)(?:-(\d+))?)?(?:#([^\s`@]+))?(?:@([0-9a-fA-F]{4,40}))?$"
)
SUPPORTED_POINTER_SUFFIXES = (
    ".md", ".py", ".tsv", ".sh", ".json", ".js", ".ts", ".tsx", ".go", ".rs", ".txt", ".yml", ".yaml", ".toml"
)


def parse_simple_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return {}, text
    raw_yaml = text[4:end_idx]
    body = text[end_idx + 5:]
    meta: dict = {}
    current_list_key: str | None = None
    for line in raw_yaml.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_list_key:
            val = stripped[2:].split("#")[0].strip().strip('"').strip("'")
            meta.setdefault(current_list_key, []).append(val)
            continue
        if ":" in stripped:
            key, val_part = stripped.split(":", 1)
            key = key.strip()
            val_clean = val_part.split("#")[0].strip().strip('"').strip("'")
            if not val_clean:
                current_list_key = key
                meta[key] = []
            elif val_clean.startswith("[") and val_clean.endswith("]"):
                current_list_key = None
                try:
                    meta[key] = json.loads(val_clean)
                except json.JSONDecodeError:
                    meta[key] = [x.strip().strip('"').strip("'") for x in val_clean[1:-1].split(",") if x.strip()]
            else:
                current_list_key = None
                meta[key] = val_clean
    return meta, body


def _matches_scope(rel_path: str, pattern: str) -> bool:
    if fnmatch.fnmatch(rel_path, pattern):
        return True
    clean_pat = pattern.rstrip("/*")
    if clean_pat and (rel_path == clean_pat or rel_path.startswith(clean_pat + "/")):
        return True
    return False


def verify_allowed_paths(brief_path: Path, workspace_root: Path) -> list[str]:
    if not brief_path.exists():
        return []
    meta, _ = parse_simple_frontmatter(brief_path.read_text(encoding="utf-8"))
    allowed = meta.get("allowed_paths")
    if not allowed or not isinstance(allowed, list):
        return []

    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    diff_proc = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )

    changed_files: set[str] = set()
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            raw_target = line[3:].strip()
            if " -> " in raw_target:
                raw_target = raw_target.split(" -> ")[1].strip()
            if raw_target.startswith('"') and raw_target.endswith('"'):
                raw_target = raw_target[1:-1]
            changed_files.add(raw_target)

    if diff_proc.returncode == 0:
        for line in diff_proc.stdout.splitlines():
            raw = line.strip()
            if raw.startswith('"') and raw.endswith('"'):
                raw = raw[1:-1]
            if raw:
                changed_files.add(raw)

    errors: list[str] = []
    ignored_prefixes = (
        ".agents/worktrees/",
        ".agents/handoffs/",
        ".git/",
    )
    for raw_target in sorted(changed_files):
        if any(raw_target.startswith(ign) for ign in ignored_prefixes):
            continue

        matched = any(_matches_scope(raw_target, pat) for pat in allowed)
        if not matched:
            errors.append(
                f"[Scope Violation]: 文件 `{raw_target}` 超出 allowed_paths 白名单范围 {allowed}"
            )
    return errors


def parse_evidence_pointer(ptr: str) -> dict[str, object] | None:
    m = POINTER_PARSE_RE.match(ptr.strip())
    if not m:
        return None
    file_part, start_s, end_s, symbol, commit = m.groups()
    start = int(start_s) if start_s is not None else None
    end = int(end_s) if end_s is not None else start
    return {
        "raw": ptr.strip(),
        "file_part": file_part,
        "start": start,
        "end": end,
        "symbol": symbol,
        "commit": commit,
    }


def _is_overload_decorated(node: ast.AST) -> bool:
    for dec in getattr(node, "decorator_list", []):
        if isinstance(dec, ast.Name) and dec.id == "overload":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "overload":
            return True
    return False


def _select_best_symbol_node(candidates: list[ast.AST]) -> tuple[int, int] | None:
    if not candidates:
        return None
    non_overload = [n for n in candidates if not _is_overload_decorated(n)]
    chosen = non_overload[0] if non_overload else candidates[-1]
    start_line = getattr(chosen, "lineno", 1)
    end_line = getattr(chosen, "end_lineno", start_line)
    return int(start_line), int(end_line)


def _find_python_symbol_span(text: str, symbol_name: str) -> tuple[int, int] | None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None

    sym_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    if "." in symbol_name:
        parts = [p for p in symbol_name.split(".") if p]
        if not parts:
            return None
        current_scopes: list[ast.AST] = [
            n for n in ast.walk(tree) if isinstance(n, sym_types) and n.name == parts[0]
        ]
        for part in parts[1:]:
            next_scopes: list[ast.AST] = []
            for scope in current_scopes:
                for child in getattr(scope, "body", []):
                    if isinstance(child, sym_types) and child.name == part:
                        next_scopes.append(child)
            current_scopes = next_scopes
        return _select_best_symbol_node(current_scopes)

    matches = [n for n in ast.walk(tree) if isinstance(n, sym_types) and n.name == symbol_name]
    return _select_best_symbol_node(matches)


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


def _find_regex_symbol_span(lines: list[str], symbol_name: str, suffix: str) -> tuple[int, int] | None:
    esc = re.escape(symbol_name)
    if suffix == ".md":
        heading_re = re.compile(rf"^\s*(#+)\s+.*?(?:(?<![A-Za-z0-9_]){esc}(?![A-Za-z0-9_]))")
        for idx, line in enumerate(lines, 1):
            m = heading_re.match(line)
            if m:
                level = len(m.group(1))
                end_idx = len(lines)
                for sub_idx in range(idx + 1, len(lines) + 1):
                    sub_m = re.match(r"^\s*(#+)\s+", lines[sub_idx - 1])
                    if sub_m and len(sub_m.group(1)) <= level:
                        end_idx = sub_idx - 1
                        break
                return idx, max(idx, end_idx)
        return None

    patterns = [
        re.compile(rf"^\s*(?:async\s+)?(?:def|class)\s+{esc}\b"),
        re.compile(rf"^\s*(?:function\s+)?{esc}\s*\(\s*\)"),
        re.compile(
            rf"^\s*(?:pub\s+)?(?:export\s+)?(?:default\s+)?(?:async\s+)?"
            rf"(?:function|class|interface|type|const|let|fn|func|struct|enum)\s+(?:\([^)]*\)\s*)?{esc}\b"
        ),
    ]
    start_line = None
    for idx, line in enumerate(lines, 1):
        if any(p.search(line) for p in patterns):
            start_line = idx
            break

    if start_line is None:
        return None

    brace_end = _count_code_braces(lines, start_line, suffix)
    if brace_end is not None:
        return start_line, brace_end

    end_line = min(len(lines), start_line + 25)
    for idx in range(start_line + 1, len(lines) + 1):
        if not lines[idx - 1].strip():
            end_line = idx - 1
            break
    return start_line, max(start_line, end_line)


def find_symbol_span(file_path: Path, symbol_name: str) -> tuple[int, int] | None:
    if not file_path.exists() or not file_path.is_file():
        return None
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    if file_path.suffix == ".py":
        span = _find_python_symbol_span(text, symbol_name)
        if span is not None:
            return span
    lines = text.splitlines()
    return _find_regex_symbol_span(lines, symbol_name, file_path.suffix)


def resolve_and_validate_pointer(ptr: str, workspace_root: Path) -> dict[str, object]:
    parsed = parse_evidence_pointer(ptr)
    if not parsed:
        return {
            "valid": False,
            "error": f"[Malformed Pointer]: 无法解析证据指针格式 `{ptr}`。",
            "drift_note": None,
            "healed_ptr": None,
        }

    file_part = str(parsed["file_part"])
    start = parsed["start"]
    end = parsed["end"]
    symbol = parsed["symbol"]
    commit = parsed["commit"]

    resolved_file = resolve_asset(file_part, workspace_root)
    if not resolved_file.exists() or not resolved_file.is_file():
        return {
            "valid": False,
            "error": f"[Dangling Evidence Pointer]: 指针引用的文件不存在 `{ptr}`。",
            "drift_note": None,
            "healed_ptr": None,
        }

    lines = resolved_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    total_lines = len(lines)

    if symbol:
        span = find_symbol_span(resolved_file, str(symbol))
        if span is None:
            return {
                "valid": False,
                "error": f"[Broken Symbol Pointer]: 指针锚定的符号不存在 `{ptr}` (未找到 #{symbol})。",
                "drift_note": None,
                "healed_ptr": None,
            }
        actual_start, actual_end = span
        commit_suffix = f"@{commit}" if commit else ""
        canonical_ptr = f"{file_part}:{actual_start}-{actual_end}#{symbol}{commit_suffix}"
        if start is None or (int(start), int(end)) != (actual_start, actual_end):
            return {
                "valid": True,
                "error": None,
                "drift_note": f"[DRIFT_AUTO_RESOLVED] {ptr} -> {canonical_ptr}",
                "healed_ptr": canonical_ptr,
            }
        return {
            "valid": True,
            "error": None,
            "drift_note": None,
            "healed_ptr": None,
        }

    if start is not None:
        s_val = int(start)
        e_val = int(end) if end is not None else s_val
        if total_lines == 0 or s_val < 1 or e_val < s_val or e_val > total_lines:
            return {
                "valid": False,
                "error": f"[Out-of-Bounds Pointer]: 指针行号越界 `{ptr}` (文件共 {total_lines} 行)。",
                "drift_note": None,
                "healed_ptr": None,
            }

    return {
        "valid": True,
        "error": None,
        "drift_note": None,
        "healed_ptr": None,
    }


def verify_brief(
    brief_path: Path,
    schema_path: Path,
    workspace_root: Path,
    fix_drift: bool = False,
) -> list[str]:
    errors: list[str] = []
    if not brief_path.exists():
        return [f"[Brief Missing]: 找不到交接简报 {brief_path}"]
    if not schema_path.exists():
        return [f"[Schema Missing]: 找不到协议定义 {schema_path}"]

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    raw = brief_path.read_text(encoding="utf-8")
    meta, body = parse_simple_frontmatter(raw)
    if not meta:
        errors.append("[Frontmatter Missing]: active-brief.md 缺少顶部 YAML Frontmatter (--- ... ---)。")
        return errors

    for req_key in schema.get("required", []):
        if req_key not in meta or not meta[req_key]:
            errors.append(f"[Frontmatter Field]: 缺少必选字段 `{req_key}`。")

    props = schema.get("properties", {})
    for enum_key in ("role", "target_agent"):
        allowed = props.get(enum_key, {}).get("enum", [])
        if enum_key in meta and meta[enum_key] not in allowed:
            errors.append(f"[Invalid {enum_key}]: `{meta[enum_key]}` 不在允许列表 {allowed} 中。")

    if "playbook" in meta:
        pb_path = resolve_asset(str(meta["playbook"]), workspace_root)
        if not pb_path.exists():
            errors.append(f"[Playbook Pointer Broken]: 找不到剧本文件 `{meta['playbook']}`。")

    for p_rel in meta.get("required_principles", []):
        if not resolve_asset(p_rel, workspace_root).exists():
            errors.append(f"[Principle Pointer Broken]: 找不到原则文件 `{p_rel}`。")

    for sec in schema.get("requiredSections", []):
        if sec not in body:
            errors.append(f"[Missing Section]: 缺少必选章节 `{sec}`。")

    max_fence = schema.get("maxInlineCodeFenceLines", 15)
    for match in re.finditer(r"```[^\n]*\n([\s\S]*?)```", body):
        fence_lines = match.group(1).splitlines()
        if len(fence_lines) > max_fence:
            errors.append(
                f"[Anti-Context-Stuffing]: 检测到 {len(fence_lines)} 行内联代码块(上限 {max_fence} 行)，严禁塞原文，请改为 file:start-end 指针！"
            )

    evidence_sec_match = re.search(
        r"(## 3\. Evidence Pointers \(Read-Only Context\))([\s\S]*?)(?=\n## |\Z)", raw
    )
    pointer_scope = evidence_sec_match.group(2) if evidence_sec_match else body
    pointers = POINTER_TOKEN_RE.findall(pointer_scope)
    valid_pointer_count = 0
    replacements: list[tuple[str, str]] = []

    for ptr in pointers:
        parsed = parse_evidence_pointer(ptr)
        if not parsed:
            continue
        file_part = str(parsed["file_part"])
        if "/" in file_part or file_part.endswith(SUPPORTED_POINTER_SUFFIXES):
            valid_pointer_count += 1
            res = resolve_and_validate_pointer(ptr, workspace_root)
            if not res["valid"] and res["error"]:
                errors.append(str(res["error"]))
            elif res["drift_note"]:
                print(f"  ~ {res['drift_note']}")
                if fix_drift and res["healed_ptr"]:
                    replacements.append((ptr, str(res["healed_ptr"])))

    if valid_pointer_count == 0:
        errors.append("[No File Pointers]: Evidence Pointers 章节中未检测到任何有效文件路径指针。")

    if fix_drift and replacements and evidence_sec_match:
        sec_header = evidence_sec_match.group(1)
        sec_body = evidence_sec_match.group(2)
        for old_ptr, new_ptr in replacements:
            sec_body = sec_body.replace(f"`{old_ptr}`", f"`{new_ptr}`")
        updated_raw = (
            raw[:evidence_sec_match.start()]
            + sec_header
            + sec_body
            + raw[evidence_sec_match.end():]
        )
        brief_path.write_text(updated_raw, encoding="utf-8")
        print(f"  + [AUTO-HEALED] Updated {len(replacements)} drifted pointer(s) in {brief_path.name}")

    return errors


def verify_ledger(ledger_path: Path) -> list[str]:
    errors: list[str] = []
    if not ledger_path.exists():
        return [f"[Ledger Missing]: 找不到实证审计表 {ledger_path}"]

    lines = [ln for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return ["[Ledger Empty]: decision.tsv 为空，缺少表头。"]

    header = lines[0].split("\t")
    if header != EXPECTED_TSV_COLS:
        errors.append(f"[Ledger Header Mismatch]: 期望列 {EXPECTED_TSV_COLS}，实际为 {header}")

    for idx, line in enumerate(lines[1:], 2):
        cols = line.split("\t")
        if len(cols) != len(EXPECTED_TSV_COLS):
            errors.append(f"decision.tsv Line {idx} [Column Count]: 期望 8 列(Tab分隔)，实际为 {len(cols)} 列。")
            continue
        verdict = cols[2].strip()
        if verdict not in VALID_VERDICTS:
            errors.append(
                f"decision.tsv Line {idx} [Invalid Verdict]: `{verdict}` 不在 {sorted(VALID_VERDICTS)} 中。"
            )
    return errors


def main() -> int:
    args = sys.argv[1:]
    fix_drift = "--fix" in args
    check_scope = "--check-scope" in args
    ledger_override: Path | None = None
    positional: list[str] = []
    idx = 0
    while idx < len(args):
        tok = args[idx]
        if tok == "--fix":
            idx += 1
            continue
        if tok == "--check-scope":
            idx += 1
            continue
        if tok == "--ledger" and idx + 1 < len(args):
            ledger_override = Path(args[idx + 1])
            idx += 2
            continue
        if not tok.startswith("--"):
            positional.append(tok)
        idx += 1

    arg_brief = Path(positional[0]) if positional else None
    workspace_root = get_workspace_root(arg_brief)
    if arg_brief is None:
        brief_path = resolve_asset(".agents/handoffs/active-brief.md", workspace_root)
    elif arg_brief.is_absolute():
        brief_path = arg_brief
    elif (Path.cwd() / arg_brief).exists():
        brief_path = (Path.cwd() / arg_brief).resolve()
    else:
        brief_path = resolve_asset(arg_brief, workspace_root)

    schema_path = resolve_asset(".agents/handoffs/handoff-schema.json", workspace_root)
    ledger_path = ledger_override or resolve_asset(".agents/decision.tsv", workspace_root)

    print("=" * 68)
    print(f"PSTACK HANDOFF & LEDGER HARNESS: {brief_path.name} + decision.tsv")
    print("=" * 68)
    errors = verify_brief(brief_path, schema_path, workspace_root, fix_drift=fix_drift) + verify_ledger(ledger_path)
    if check_scope:
        errors += verify_allowed_paths(brief_path, workspace_root)

    if not errors:
        print("STATUS : ALL CHECKS GREEN (Schema, Pointers & Ledger valid)")
        print("=" * 68)
        return 0

    print(f"STATUS : FAILED ({len(errors)} violations found)")
    print("-" * 68)
    for err in errors:
        print(f"  x {err}")
    print("=" * 68)
    return 1


if __name__ == "__main__":
    sys.exit(main())
