#!/usr/bin/env python3
"""
pstack Unified 4-Gate Verification, Independent Verifier Verdict & Ban CLI
Usage:
  python3 scripts/pstack-verify.py all
  python3 scripts/pstack-verify.py prose [file]
  python3 scripts/pstack-verify.py handoff [brief_file]
  python3 scripts/pstack-verify.py code [file_or_dir]
  python3 scripts/pstack-verify.py cmd [brief_file]
  python3 scripts/pstack-verify.py prep-verifier
  python3 scripts/pstack-verify.py verdict [verdict_file]
  python3 scripts/pstack-verify.py export [draft_file] [final_file]
  python3 scripts/pstack-verify.py ban "<phrase>"
"""
import hashlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from pstack_onboard import detect_verify_cmd
from pstack_resolver import ensure_workspace_skeleton, get_pstack_home, get_workspace_root, resolve_asset

RECURSIVE_VERIFY_PATTERNS = (
    "pstack verify all",
    "pstack-verify.py all",
    "pstack-verify all",
)

REQUIRED_VERDICT_TIERS = ("ACT_ON", "CONSIDER", "NOTED", "DISMISSED")


def run_step(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def extract_verify_cmd(brief_path: Path, workspace_root: Path) -> str:
    if not brief_path.exists():
        return detect_verify_cmd(workspace_root)
    raw = brief_path.read_text(encoding="utf-8")
    match = re.search(r"^verify_cmd:\s*(.+)$", raw, re.MULTILINE)
    if not match:
        return detect_verify_cmd(workspace_root)
    cmd = match.group(1).strip()
    if (cmd.startswith('"') and cmd.endswith('"')) or (cmd.startswith("'") and cmd.endswith("'")):
        cmd = cmd[1:-1].strip()
    if not cmd or any(pat in cmd for pat in RECURSIVE_VERIFY_PATTERNS):
        return detect_verify_cmd(workspace_root)
    return cmd


def update_evidence_runtime_digest(evidence_path: Path, digest_block: str) -> None:
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    if not evidence_path.exists():
        evidence_path.write_text(f"# Pstack Evidence Pack\n\n{digest_block.strip()}\n", encoding="utf-8")
        return

    existing = evidence_path.read_text(encoding="utf-8")
    pattern = r"\n*## Runtime Verification Digest[\s\S]*$"
    if re.search(pattern, existing):
        updated = re.sub(pattern, "\n\n" + digest_block.strip() + "\n", existing)
    else:
        updated = existing.rstrip() + "\n\n" + digest_block.strip() + "\n"
    evidence_path.write_text(updated, encoding="utf-8")


def execute_verify_cmd(brief_path: Path, workspace_root: Path) -> int:
    cmd = extract_verify_cmd(brief_path, workspace_root)
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        rc = proc.returncode
        combined_out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    except subprocess.TimeoutExpired:
        print(f"[FAIL] Runtime verify_cmd timed out after 120s: `{cmd}`")
        return 1

    sha12 = hashlib.sha256(combined_out.encode("utf-8")).hexdigest()[:12]
    diff_proc = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    diff_lines = [ln.strip() for ln in diff_proc.stdout.splitlines() if ln.strip()]
    diff_summary = diff_lines[-1] if diff_lines else "clean working tree (0 uncommitted diffs)"

    out_lines = [ln.rstrip() for ln in combined_out.splitlines() if ln.strip()]
    tail_lines = out_lines[-6:] if out_lines else ["(0 stdout lines)"]
    tail_formatted = "\n".join(f"  {ln[:88]}" for ln in tail_lines)

    digest_block = (
        "## Runtime Verification Digest\n"
        f"- **Command**: `{cmd}` (`[实测 Measured]` at `{ts}`)\n"
        f"- **Exit Code & Digest**: `exit={rc}` | `sha256={sha12}`\n"
        f"- **Git Diff Summary**: `{diff_summary}`\n"
        "- **Output Tail**:\n"
        "```text\n"
        f"{tail_formatted}\n"
        "```"
    )
    evidence_path = workspace_root / ".agents" / "handoffs" / "evidence-pack.md"
    update_evidence_runtime_digest(evidence_path, digest_block)

    print("=" * 68)
    print(f"PSTACK GATE 4 RUNTIME VERIFICATION: {cmd}")
    print("=" * 68)
    if rc == 0:
        print(f"STATUS : ALL CHECKS GREEN (exit=0, sha256={sha12} -> evidence-pack.md)")
        print("=" * 68)
        return 0
    print(f"STATUS : FAILED (exit={rc}, sha256={sha12})")
    print(tail_formatted)
    print("=" * 68)
    return 1


def export_clean_final(workspace_root: Path, scripts_dir: Path, draft_arg: str | None = None, final_arg: str | None = None) -> int:
    draft_path = Path(draft_arg) if draft_arg else resolve_asset(".agents/handoffs/output-draft.md", workspace_root)
    final_path = Path(final_arg) if final_arg else (workspace_root / ".agents" / "handoffs" / "output-final.md")
    return run_step(
        [sys.executable, str(scripts_dir / "verify-prose.py"), str(draft_path), "--export-clean", str(final_path)]
    )


def safe_truncate(text: str, max_len: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    truncated = cleaned[:max_len].rstrip()
    if truncated.count("`") % 2 != 0:
        truncated += "`"
    return truncated + "..."


def prep_verifier_digest(workspace_root: Path, blind: bool = False) -> int:
    brief_path = resolve_asset(".agents/handoffs/active-brief.md", workspace_root)
    draft_path = resolve_asset(".agents/handoffs/output-draft.md", workspace_root)
    evidence_path = resolve_asset(".agents/handoffs/evidence-pack.md", workspace_root)

    goal_line = "(active-brief.md missing)"
    contract_lines: list[str] = []
    if brief_path.exists():
        raw_brief = brief_path.read_text(encoding="utf-8")
        m_goal = re.search(r"## 1\. User Goal \(Restated\)\s*\n+([^\n]+)", raw_brief)
        if m_goal:
            goal_line = safe_truncate(m_goal.group(1), 95)
        m_contract = re.search(r"## 4\. Deliverable Contract\s*\n([\s\S]*?)(?:\n##|\Z)", raw_brief)
        if m_contract:
            contract_lines = [
                safe_truncate(ln, 85)
                for ln in m_contract.group(1).splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]

    exit_val = ""
    cmd_val = ""
    gdiff_val = ""
    tail_lines: list[str] = []
    if evidence_path.exists():
        raw_ev = evidence_path.read_text(encoding="utf-8")
        m_ev = re.search(r"## Runtime Verification Digest([\s\S]*)$", raw_ev)
        if m_ev:
            body = m_ev.group(1).strip()
            m_exit = re.search(r"- \*\*Exit Code & Digest\*\*:\s*([^\n]+)", body)
            if m_exit:
                exit_val = m_exit.group(1).strip()
            m_cmd = re.search(r"- \*\*Command\*\*:\s*`([^`]+)`", body)
            if m_cmd:
                cmd_val = m_cmd.group(1).strip()
            m_gdiff = re.search(r"- \*\*Git Diff Summary\*\*:\s*`?([^`\n]+)`?", body)
            if m_gdiff:
                gdiff_val = m_gdiff.group(1).strip()
            m_tail = re.search(r"```(?:text)?\s*([\s\S]*?)```", body)
            if m_tail:
                tail_lines = [ln.strip() for ln in m_tail.group(1).strip().splitlines() if ln.strip()]

    if blind:
        diff_stat: list[str] = []
        changed_files: list[str] = []
        try:
            p_files = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=workspace_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if p_files.returncode == 0 and p_files.stdout.strip():
                changed_files = [f.strip() for f in p_files.stdout.splitlines() if f.strip()]
            p_stat = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=workspace_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if p_stat.returncode == 0 and p_stat.stdout.strip():
                diff_stat = [s.strip() for s in p_stat.stdout.splitlines() if s.strip()]
        except Exception as exc:
            print(f"[prep] git diff --stat unavailable, skipped: {exc}")

        files_str = ", ".join(changed_files[:5]) if changed_files else "(no uncommitted git diff)"
        stat_summary = diff_stat[-1] if diff_stat else "(clean tree)"

        blind_pack: list[str] = [
            "# Pstack Blind Review Pack (Strict Tab 2 Isolation)",
            f"- **Workspace**: `{workspace_root.name}`",
            f"- **User Goal**: {goal_line}",
            "- **Deliverable Contract**:",
            *(f"  {c}" for c in (contract_lines[:3] or ["  (none specified)"])),
            "- **Git Diff & Changed Files**:",
            f"  - Files: `{files_str}`",
            f"  - Stat : `{stat_summary}`",
            "- **Runtime Verification Digest (Gate 4 Evidence)**:",
        ]
        if exit_val:
            blind_pack.append(f"  - Exit & SHA256: {exit_val}")
        if cmd_val:
            blind_pack.append(f"  - Command: `{safe_truncate(cmd_val, 80)}`")
        if tail_lines:
            blind_pack.append("  - Output Tail:")
            blind_pack.append("    ```text")
            for tln in tail_lines[-3:]:
                blind_pack.append(f"    {safe_truncate(tln, 75)}")
            blind_pack.append("    ```")
        elif not exit_val:
            blind_pack.append("  (run `pstack verify all` first)")
        blind_pack.append(
            "- **Verifier Next Action**: Audit evidence, write 4 tiers to verifier-verdict.md, run `pstack verify verdict`."
        )
        bounded_blind = "\n".join(blind_pack[:25]) + "\n"
        blind_file = workspace_root / ".agents" / "handoffs" / "blind-review-pack.md"
        blind_file.parent.mkdir(parents=True, exist_ok=True)
        blind_file.write_text(bounded_blind, encoding="utf-8")
        print(bounded_blind.rstrip())
        return 0

    restate_lines: list[str] = []
    if draft_path.exists():
        for ln in draft_path.read_text(encoding="utf-8").splitlines()[:6]:
            if ln.strip().startswith(">"):
                restate_lines.append(safe_truncate(ln, 90))

    runtime_summary: list[str] = []
    if exit_val:
        runtime_summary.append(f"  {exit_val}")
    if cmd_val:
        runtime_summary.append(f"  cmd: `{safe_truncate(cmd_val, 70)}`")
    for tln in tail_lines[-2:]:
        runtime_summary.append(f"  tail: {safe_truncate(tln, 70)}")

    out: list[str] = [
        "=== PSTACK INDEPENDENT VERIFIER DIGEST (READ-ONLY) ===",
        f"WORKSPACE : {workspace_root}",
        f"USER GOAL : {goal_line}",
        "BUILDER RESTATE:",
        *(restate_lines[:3] or ["  (none)"]),
        "RUNTIME EVIDENCE:",
        *(runtime_summary[:4] or ["  (run `pstack verify all` first)"]),
        "NEXT STEP : Write 4-tier review to .agents/handoffs/verifier-verdict.md & run `pstack verify verdict`",
    ]
    print("\n".join(out[:20]))
    return 0


def verify_verdict_file(workspace_root: Path, scripts_dir: Path, verdict_arg: str | None = None) -> int:
    verdict_path = (
        Path(verdict_arg)
        if verdict_arg
        else resolve_asset(".agents/handoffs/verifier-verdict.md", workspace_root)
    )
    if not verdict_path.exists():
        print(f"[FAIL] Verifier verdict file not found: {verdict_path}")
        return 1

    text = verdict_path.read_text(encoding="utf-8")
    errors: list[str] = []
    for tier in REQUIRED_VERDICT_TIERS:
        if tier not in text:
            errors.append(f"[Missing Tier]: 缺少四级审查分类项 `{tier}`。")

    verdict_match = re.search(r"^VERDICT:\s*(PASS|REJECT)\b", text, re.MULTILINE)
    if not verdict_match:
        errors.append("[Missing Final Verdict]: 缺少 `VERDICT: PASS` 或 `VERDICT: REJECT` 终审结论。")
    elif verdict_match.group(1) == "REJECT":
        errors.append("[Verifier Rejected]: 独立审查结论为 `VERDICT: REJECT`，请将 ACT_ON 缺陷合并回 active-brief.md。")

    print("=" * 68)
    print(f"PSTACK INDEPENDENT VERIFIER VERDICT GATE: {verdict_path.name}")
    print("=" * 68)
    if errors:
        print(f"STATUS : FAILED ({len(errors)} violations found)")
        print("-" * 68)
        for err in errors:
            print(f"  x {err}")
        print("=" * 68)
        return 1

    print("STATUS : ALL CHECKS GREEN (4-Tier Verdict PASS)")
    print("=" * 68)
    draft_path = resolve_asset(".agents/handoffs/output-draft.md", workspace_root)
    if draft_path.exists():
        return export_clean_final(workspace_root, scripts_dir, str(draft_path))
    return 0


def add_banned_phrase(workspace_root: Path, phrase: str) -> int:
    clean = phrase.strip()
    if not clean:
        print("[FAIL] Empty phrase cannot be banned.")
        return 1
    ban_file = workspace_root / ".agents" / "pstack" / "custom-banned-phrases.txt"
    ban_file.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if ban_file.exists():
        existing = {
            ln.strip()
            for ln in ban_file.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        }
    if clean in existing:
        print(f"[OK] Phrase already in blacklist: 「{clean}」 ({ban_file})")
        return 0
    with ban_file.open("a", encoding="utf-8") as f:
        f.write(f"{clean}\n")
    print(f"[OK] Added 「{clean}」 to permanent Pstack blacklist ({ban_file}).")
    return 0


def main() -> int:
    pstack_home = get_pstack_home()
    workspace_root = get_workspace_root()
    scripts_dir = pstack_home / "scripts"
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "ban":
        if len(sys.argv) < 3:
            print("Usage: python3 scripts/pstack-verify.py ban \"<phrase>\"")
            return 2
        return add_banned_phrase(workspace_root, sys.argv[2])

    if mode == "prose":
        target = (
            sys.argv[2]
            if len(sys.argv) > 2
            else str(resolve_asset(".agents/handoffs/output-draft.md", workspace_root))
        )
        extra = sys.argv[3:] if len(sys.argv) > 3 else []
        return run_step([sys.executable, str(scripts_dir / "verify-prose.py"), target, *extra])

    if mode == "handoff":
        raw_args = sys.argv[2:]
        if raw_args and not raw_args[0].startswith("--"):
            target = raw_args[0]
            extra = raw_args[1:]
        else:
            target = str(resolve_asset(".agents/handoffs/active-brief.md", workspace_root))
            extra = raw_args
        return run_step([sys.executable, str(scripts_dir / "verify-handoff.py"), target, *extra])

    tests_dir = pstack_home / "tests"
    default_home_targets = [str(scripts_dir), str(tests_dir)] if tests_dir.is_dir() else [str(scripts_dir)]

    if mode == "code":
        if len(sys.argv) > 2:
            targets = sys.argv[2:]
        elif workspace_root != pstack_home:
            targets = [str(workspace_root), *default_home_targets]
        else:
            targets = default_home_targets
        return run_step([sys.executable, str(scripts_dir / "verify-code-slop.py"), *targets])

    if mode == "cmd":
        brief_target = (
            Path(sys.argv[2])
            if len(sys.argv) > 2
            else resolve_asset(".agents/handoffs/active-brief.md", workspace_root)
        )
        return execute_verify_cmd(brief_target, workspace_root)

    if mode == "prep-verifier":
        blind = "--blind" in sys.argv[2:]
        return prep_verifier_digest(workspace_root, blind=blind)

    if mode == "verdict":
        verdict_arg = sys.argv[2] if len(sys.argv) > 2 else None
        return verify_verdict_file(workspace_root, scripts_dir, verdict_arg)

    if mode == "export":
        draft_arg = sys.argv[2] if len(sys.argv) > 2 else None
        final_arg = sys.argv[3] if len(sys.argv) > 3 else None
        return export_clean_final(workspace_root, scripts_dir, draft_arg, final_arg)

    if mode == "all":
        ensure_workspace_skeleton(workspace_root)
        brief_target = resolve_asset(".agents/handoffs/active-brief.md", workspace_root)
        draft_target = resolve_asset(".agents/handoffs/output-draft.md", workspace_root)
        code_targets = (
            [str(workspace_root), *default_home_targets]
            if workspace_root != pstack_home
            else default_home_targets
        )
        rc1 = run_step([sys.executable, str(scripts_dir / "verify-handoff.py"), str(brief_target), "--fix"])
        rc2 = run_step([sys.executable, str(scripts_dir / "verify-prose.py"), str(draft_target)])
        rc3 = run_step([sys.executable, str(scripts_dir / "verify-code-slop.py"), *code_targets])
        rc4 = execute_verify_cmd(brief_target, workspace_root)
        if rc1 == 0 and rc2 == 0 and rc3 == 0 and rc4 == 0:
            print("\n>>> [PSTACK SUITE] ALL 4 HARNESS GATES GREEN <<<")
            return 0
        print("\n>>> [PSTACK SUITE] GATE FAILURE DETECTED <<<")
        return 1

    print(
        f"Unknown mode: {mode}. Use one of: all | prose | handoff | code | cmd | prep-verifier | verdict | export | ban"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
