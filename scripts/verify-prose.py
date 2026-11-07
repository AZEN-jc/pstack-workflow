#!/usr/bin/env python3
"""
pstack Unslop & Prose Verification Harness
Usage:
  python3 scripts/verify-prose.py <markdown_file> [--max-zh-chars 45] [--max-en-words 28] [--require-restate]
  python3 scripts/verify-prose.py <markdown_file> --export-clean <output_path>
"""
import argparse
import re
import sys
from pathlib import Path

from pstack_resolver import get_pstack_home, get_workspace_root

BANNED_ZH = [
    "值得注意的是", "总而言之", "综上所述", "不难发现", "显而易见",
    "毋庸置疑", "在当今", "让我们深入", "不仅仅", "更是", "擦出怎样的火花",
    "赋能", "抓手", "颗粒度", "底层逻辑"
]

BANNED_EN = [
    r"\bdelve\b", r"\btapestry\b", r"\btestament\b", r"\bunderscore[ds]?\b",
    r"\bmoreover\b", r"\bfurthermore\b", r"\bit is worth noting\b",
    r"\bit's worth noting\b", r"\bcrucial\b", r"\bpivotal\b", r"\blandscape\b"
]


EPISTEMIC_MARKERS = [
    "[离线实测 Offline-Measured]",
    "[沙箱模拟 Sim-Verified]",
    "[真机实测 Live-Agent]",
    "[Offline-Measured]",
    "[Sim-Verified]",
    "[Live-Agent]",
    "[实测 Measured]",
    "[推导 Inferred]",
    "[Measured]",
    "[Inferred]",
    "[实测]",
    "[推导]",
    "[猜测]",
    "[Guess]",
]

EPISTEMIC_TAG_REGEX = re.compile(
    r"\[(?:离线实测\s+Offline-Measured|沙箱模拟\s+Sim-Verified|真机实测\s+Live-Agent|Offline-Measured|Sim-Verified|Live-Agent|实测\s+Measured|推导\s+Inferred|实测|推导|猜测|Measured|Inferred|Guess)[^\]]*\]",
    re.IGNORECASE,
)


def load_custom_banned(workspace_root: Path) -> list[str]:
    roots = [get_pstack_home()]
    if workspace_root not in roots:
        roots.append(workspace_root)

    phrases: list[str] = []
    seen: set[str] = set()
    for root in roots:
        custom_file = root / ".agents" / "pstack" / "custom-banned-phrases.txt"
        if not custom_file.exists():
            continue
        for line in custom_file.read_text(encoding="utf-8").splitlines():
            item = line.strip()
            if item and not item.startswith("#") and item not in seen:
                seen.add(item)
                phrases.append(item)
    return phrases


def strip_code_blocks_preserve_lines(text: str) -> str:
    def replacer(match: re.Match) -> str:
        return "\n" * match.group(0).count("\n")
    return re.sub(r"```[\s\S]*?```", replacer, text)


def strip_inline_markup(line: str) -> str:
    cleaned = re.sub(r"`[^`]+`", "", line)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = EPISTEMIC_TAG_REGEX.sub("", cleaned)
    return cleaned


def strip_builder_restate(text: str) -> str:
    lines = text.splitlines()
    out_lines: list[str] = []
    in_restate = False
    skip_next_blank = False

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if idx < 10 and not in_restate and stripped.startswith(">") and "[Builder Restate]" in stripped:
            in_restate = True
            continue
        if in_restate:
            if stripped.startswith(">"):
                continue
            in_restate = False
            skip_next_blank = True
        if skip_next_blank and not stripped:
            skip_next_blank = False
            continue
        skip_next_blank = False
        out_lines.append(line)

    return "\n".join(out_lines).lstrip("\n") + "\n"


def check_builder_restate(raw_lines: list[str]) -> list[str]:
    errors: list[str] = []
    head = raw_lines[:6]
    restate_start = -1
    for idx, line in enumerate(head):
        if line.strip().startswith(">") and "[Builder Restate]" in line:
            restate_start = idx
            break

    if restate_start == -1:
        errors.append(
            "[Builder Restate Missing]: output-draft.md 前 6 行必须包含 `> [Builder Restate]` 三句话复述头。"
        )
        return errors

    restate_len = 0
    for line in raw_lines[restate_start:]:
        if line.strip().startswith(">"):
            restate_len += 1
        else:
            break

    if restate_len > 4:
        errors.append(
            f"[Builder Restate Bloat]: `[Builder Restate]` 块占用了 {restate_len} 行(上限 4 行)，请精简。"
        )
    return errors


def count_zh_chars(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def count_en_words(s: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_'-]+", s))


def verify_file(
    filepath: Path,
    max_zh_chars: int = 45,
    max_en_words: int = 28,
    require_restate: bool = False,
) -> int:
    if not filepath.exists():
        print(f"[FAIL] File not found: {filepath}")
        return 1

    raw_text = filepath.read_text(encoding="utf-8")
    raw_lines = raw_text.splitlines()
    prose = strip_code_blocks_preserve_lines(raw_text)
    lines = prose.splitlines()
    workspace_root = get_workspace_root(filepath)
    custom_banned = load_custom_banned(workspace_root)

    errors: list[str] = []

    if require_restate or filepath.name == "output-draft.md":
        errors.extend(check_builder_restate(raw_lines))

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("|") or set(stripped) <= {"-", ":", "|", " "}:
            continue
        if "—" in line or "——" in line or " -- " in line:
            errors.append(
                f"Line {idx} [Dash Ban]: 检测到破折号，请拆分为短句或用括号 -> {stripped[:42]}..."
            )
        inline_clean = strip_inline_markup(stripped)
        if re.search(r"[:：]\s*\S+", inline_clean) and not stripped.startswith(("#", "-", "*", ">")):
            if not re.search(r"https?://|\d{1,2}:\d{2}", inline_clean):
                errors.append(
                    f"Line {idx} [Mid-Sentence Colon Ban]: 禁用句中解释性冒号，请直接陈述 -> {stripped[:42]}..."
                )

    for phrase in BANNED_ZH + custom_banned:
        if phrase in prose:
            errors.append(f"[Slop Phrase ZH]: 检测到禁用套话「{phrase}」，请直接陈述事实。")

    for pattern in BANNED_EN:
        if re.search(pattern, prose, re.IGNORECASE):
            errors.append(f"[Slop Phrase EN]: 检测到英文 AI 腔词汇 /{pattern}/。")

    for idx, line in enumerate(lines, 1):
        clean_line = line.strip()
        if not clean_line or clean_line.startswith(("#", ">", "|", "-", "*", "`")):
            continue
        measured_line = strip_inline_markup(clean_line)
        sentences = re.split(r"[。！？.!?]", measured_line)
        for s in sentences:
            seg = s.strip()
            if not seg:
                continue
            zh_count = count_zh_chars(seg)
            en_count = count_en_words(seg)
            if zh_count > max_zh_chars:
                errors.append(
                    f"Line {idx} [Sentence Too Long ZH]: 中文单句含 {zh_count} 汉字(上限 {max_zh_chars}) -> {seg[:35]}..."
                )
            elif zh_count == 0 and en_count > max_en_words:
                errors.append(
                    f"Line {idx} [Sentence Too Long EN]: 英文单句含 {en_count} 词(上限 {max_en_words}) -> {seg[:45]}..."
                )
            elif len(seg) > 65:
                errors.append(
                    f"Line {idx} [Sentence Too Long]: 单句超过65字符({len(seg)}字) -> {seg[:35]}..."
                )

    has_epistemic_tag = any(marker in raw_text for marker in EPISTEMIC_MARKERS) or bool(
        EPISTEMIC_TAG_REGEX.search(raw_text)
    )
    if not has_epistemic_tag:
        errors.append(
            "[Epistemic Gate]: 全文缺少证据等级标签（如 [离线实测 Offline-Measured] / [沙箱模拟 Sim-Verified] / [真机实测 Live-Agent] / [实测 Measured] / [推导 Inferred]），请为关键论断绑定证据。"
        )

    print("=" * 68)
    print(f"PSTACK PROSE VERIFICATION HARNESS: {filepath.name}")
    print("=" * 68)
    if not errors:
        print("STATUS : ALL CHECKS GREEN (0 violations)")
        print("=" * 68)
        return 0

    print(f"STATUS : FAILED ({len(errors)} violations found)")
    print("-" * 68)
    for err in errors:
        print(f"  x {err}")
    print("=" * 68)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="pstack Unslop & Prose Verification Harness")
    parser.add_argument("markdown_file", type=Path, help="Path to the markdown file to verify")
    parser.add_argument("--max-zh-chars", type=int, default=45, help="Max Chinese characters per sentence")
    parser.add_argument("--max-en-words", type=int, default=28, help="Max English words per sentence")
    parser.add_argument("--require-restate", action="store_true", help="Enforce > [Builder Restate] header")
    parser.add_argument("--export-clean", type=Path, help="Strip > [Builder Restate] and write clean output")
    args = parser.parse_args()

    rc = verify_file(args.markdown_file, args.max_zh_chars, args.max_en_words, args.require_restate)
    if rc == 0 and args.export_clean is not None:
        cleaned = strip_builder_restate(args.markdown_file.read_text(encoding="utf-8"))
        args.export_clean.parent.mkdir(parents=True, exist_ok=True)
        args.export_clean.write_text(cleaned, encoding="utf-8")
        print(f"[OK] Exported clean final document -> {args.export_clean}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
