#!/usr/bin/env python3
"""
pstack Handoff Brief & Decision Ledger Verification Harness
Usage: python3 scripts/verify-handoff.py [brief_file] [--ledger .agents/decision.tsv]
"""
import json
import re
import sys
from pathlib import Path

from pstack_resolver import get_workspace_root, resolve_asset

VALID_VERDICTS = {"KEEP", "REVERT", "ROOT_CAUSE", "PERF_WIN"}
EXPECTED_TSV_COLS = [
    "timestamp", "task_id", "verdict", "hypothesis",
    "evidence_pointer", "metric_before", "metric_after", "lesson_learned"
]


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
            else:
                current_list_key = None
                meta[key] = val_clean
    return meta, body


def verify_brief(brief_path: Path, schema_path: Path, workspace_root: Path) -> list[str]:
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
        r"## 3\. Evidence Pointers \(Read-Only Context\)([\s\S]*?)(?=\n## |\Z)", body
    )
    pointer_scope = evidence_sec_match.group(1) if evidence_sec_match else body
    pointers = re.findall(r"`([A-Za-z0-9_./-]+(?::\d+(?:-\d+)?)?)`", pointer_scope)
    valid_pointer_count = 0
    for ptr in pointers:
        file_part = ptr.split(":")[0]
        if "/" in file_part or file_part.endswith((".md", ".py", ".tsv", ".sh", ".json")):
            valid_pointer_count += 1
            if not resolve_asset(file_part, workspace_root).exists():
                errors.append(f"[Dangling Evidence Pointer]: 指针引用的文件不存在 `{ptr}`。")

    if valid_pointer_count == 0:
        errors.append("[No File Pointers]: Evidence Pointers 章节中未检测到任何有效文件路径指针。")

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
    arg_brief = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
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
    ledger_path = resolve_asset(".agents/decision.tsv", workspace_root)

    errors = verify_brief(brief_path, schema_path, workspace_root) + verify_ledger(ledger_path)

    print("=" * 68)
    print(f"PSTACK HANDOFF & LEDGER HARNESS: {brief_path.name} + decision.tsv")
    print("=" * 68)
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
