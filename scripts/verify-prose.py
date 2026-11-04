#!/usr/bin/env python3
"""
pstack Unslop & Prose Verification Harness
Usage: python3 scripts/verify-prose.py <markdown_file> [--max-zh-chars 45] [--max-en-words 28]
"""
import argparse
import re
import sys
from pathlib import Path

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


def load_custom_banned(workspace_root: Path) -> list[str]:
    custom_file = workspace_root / ".agents" / "pstack" / "custom-banned-phrases.txt"
    if not custom_file.exists():
        return []
    phrases = []
    for line in custom_file.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if item and not item.startswith("#"):
            phrases.append(item)
    return phrases


def strip_code_blocks_preserve_lines(text: str) -> str:
    def replacer(match: re.Match) -> str:
        return "\n" * match.group(0).count("\n")
    return re.sub(r"```[\s\S]*?```", replacer, text)


def strip_inline_markup(line: str) -> str:
    cleaned = re.sub(r"`[^`]+`", "", line)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"\[(?:实测|推导|猜测|Measured|Inferred|Guess)[^\]]*\]", "", cleaned)
    return cleaned


def count_zh_chars(s: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", s))


def count_en_words(s: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_'-]+", s))


def verify_file(filepath: Path, max_zh_chars: int = 45, max_en_words: int = 28) -> int:
    if not filepath.exists():
        print(f"[FAIL] File not found: {filepath}")
        return 1

    raw_text = filepath.read_text(encoding="utf-8")
    prose = strip_code_blocks_preserve_lines(raw_text)
    lines = prose.splitlines()
    workspace_root = Path(__file__).resolve().parent.parent
    custom_banned = load_custom_banned(workspace_root)

    errors: list[str] = []

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

    has_epistemic_tag = re.search(
        r"\[(?:实测|推导|猜测|Measured|Inferred|Guess)(?:\s+(?:Measured|Inferred|Guess))?\]",
        raw_text,
    )
    if not has_epistemic_tag:
        errors.append(
            "[Epistemic Gate]: 全文缺少证据等级标签（如 [实测 Measured] / [推导 Inferred]），请为关键论断绑定证据。"
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
    args = parser.parse_args()
    return verify_file(args.markdown_file, args.max_zh_chars, args.max_en_words)


if __name__ == "__main__":
    sys.exit(main())
