#!/usr/bin/env python3
"""
pstack Comment Sicko & Code Anti-Slop Verification Harness
Usage: python3 scripts/verify-code-slop.py <file_or_dir ...>
"""
import re
import sys
from pathlib import Path

CODE_EXTENSIONS = {".py", ".sh", ".js", ".ts", ".tsx", ".go", ".rs"}

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build", "coverage",
    "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "site-packages", ".next",
}

SLOP_COMMENT_PATTERNS = [
    r"^\s*(?:#|//)\s*(?:validate|check|verify)\s+(?:the\s+)?(?:input|args|arguments|parameters)\b",
    r"^\s*(?:#|//)\s*(?:initialize|init|set\s+up|define)\s+(?:the\s+)?(?:variables?|state|config|logger)\b",
    r"^\s*(?:#|//)\s*(?:loop|iterate)\s+(?:through|over)\b",
    r"^\s*(?:#|//)\s*return\s+(?:the\s+)?(?:result|output|value|response)\b",
    r"^\s*(?:#|//)\s*here\s+we\b",
    r"^\s*(?:#|//)\s*this\s+(?:function|method|class|script)\s+(?:is\s+used\s+to|handles|does)\b",
    r"^\s*(?:#|//)\s*(?:辅助函数|初始化变量|遍历列表|返回结果|检查输入参数)\b",
    r"^\s*(?:#|//)\s*TODO:\s*(?:implement|fix\s+later|add\s+logic)\b",
]

SWALLOWED_EXCEPTION_PATTERNS = [
    (r"except\s*(?:Exception|BaseException)?\s*:\s*\n\s*pass\b", "检测到空 `except: pass` 静默吞异常"),
    (r"catch\s*\([^)]*\)\s*\{\s*\}", "检测到空 `catch {}` 静默吞异常"),
]


def collect_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in targets:
        p = Path(raw)
        if p.is_file() and p.suffix in CODE_EXTENSIONS:
            files.append(p)
        elif p.is_dir():
            for sub in sorted(p.rglob("*")):
                if sub.is_file() and sub.suffix in CODE_EXTENSIONS and not SKIP_DIRS.intersection(sub.parts):
                    files.append(sub)
    return files


def check_file(filepath: Path) -> list[str]:
    errors: list[str] = []
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines()

    consecutive_comments = 0
    block_has_why_tag = False

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if idx == 1 and stripped.startswith("#!"):
            continue

        for pat in SLOP_COMMENT_PATTERNS:
            if re.search(pat, line, re.IGNORECASE):
                errors.append(
                    f"{filepath.name}:{idx} [Comment Sicko]: 检测到复述代码行为的 AI 废话注释 -> `{stripped[:50]}`"
                )

        is_comment = stripped.startswith("#") or stripped.startswith("//")
        if is_comment:
            consecutive_comments += 1
            if re.search(r"\b(?:Why|Constraint|Ref|https?://):", stripped):
                block_has_why_tag = True
            if consecutive_comments > 4 and not block_has_why_tag:
                errors.append(
                    f"{filepath.name}:{idx} [Comment Bloat]: 连续超过 4 行注释且未标注 `Why:` 或 `Constraint:`，请改为代码断言或提取函数。"
                )
        else:
            consecutive_comments = 0
            block_has_why_tag = False

    for pat, msg in SWALLOWED_EXCEPTION_PATTERNS:
        if re.search(pat, text):
            errors.append(f"{filepath.name} [Swallowed Exception]: {msg}")

    return errors


def main() -> int:
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["scripts"]
    files = collect_files(targets)
    if not files:
        print("[FAIL] No matching code files found to check.")
        return 1

    all_errors: list[str] = []
    for f in files:
        all_errors.extend(check_file(f))

    print("=" * 68)
    print(f"PSTACK COMMENT SICKO & CODE SLOP HARNESS ({len(files)} files scanned)")
    print("=" * 68)
    if not all_errors:
        print("STATUS : ALL CHECKS GREEN (0 redundant comments or swallowed exceptions)")
        print("=" * 68)
        return 0

    print(f"STATUS : FAILED ({len(all_errors)} violations found)")
    print("-" * 68)
    for err in all_errors:
        print(f"  x {err}")
    print("=" * 68)
    return 1


if __name__ == "__main__":
    sys.exit(main())
