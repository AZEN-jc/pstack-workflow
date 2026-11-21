#!/usr/bin/env python3
"""
Unit test suite for Pstack v3.0 Verifiable Engineering Harness.
Run via: python3 -m unittest discover -s tests -q
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pstack_bench import (
    measure_context_compression,
    run_abcd_benchmark,
    run_adversarial_mutation_suite,
    run_live_ab_experiment,
    run_sandbox_ab_suite,
)
import pstack_hook
from pstack_onboard import detect_verify_cmd
from pstack_resolver import ensure_workspace_skeleton, get_pstack_home, get_workspace_root, resolve_asset
from pstack_router import (
    auto_discover_pointers_and_scope,
    classify_goal,
    generate_brief,
)
from pstack_scheduler import (
    WorktreeSandbox,
    execute_arena,
    execute_resume,
    execute_swarm,
    extract_gate_failure_digest,
    load_dag_state,
    merge_worktree_to_workspace,
    run_with_auto_rework,
    topological_levels,
)
from pstack_session import generate_snapshot
from pstack_tree import (
    load_tree_data,
    render_ascii_tree,
)


def _load_mod(name: str, filename: str):
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


verify_handoff = _load_mod("verify_handoff", "verify-handoff.py")
verify_prose = _load_mod("verify_prose", "verify-prose.py")
verify_code_slop = _load_mod("verify_code_slop", "verify-code-slop.py")
pstack_verify = _load_mod("pstack_verify", "pstack-verify.py")


class TestPstackHarness(unittest.TestCase):
    def test_resolver_overlay_and_workspace_discovery(self) -> None:
        home = get_pstack_home()
        self.assertTrue((home / ".agents" / "pstack" / "pstack-core.md").is_file())

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            ensure_workspace_skeleton(ws)
            self.assertTrue((ws / ".agents" / "decision.tsv").is_file())
            self.assertTrue((ws / ".agents" / "handoffs" / "active-brief.md").is_file())

            sub_dir = ws / "src" / "deep"
            sub_dir.mkdir(parents=True)
            discovered = get_workspace_root(sub_dir)
            self.assertEqual(discovered, ws)

            core_resolved = resolve_asset(".agents/pstack/pstack-core.md", ws)
            self.assertEqual(core_resolved, home / ".agents" / "pstack" / "pstack-core.md")

            local_brief = resolve_asset(".agents/handoffs/active-brief.md", ws)
            self.assertEqual(local_brief, ws / ".agents" / "handoffs" / "active-brief.md")

    def test_pointer_bounds_and_symbol_auto_heal(self) -> None:
        schema_path = REPO_ROOT / ".agents" / "handoffs" / "handoff-schema.json"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            ensure_workspace_skeleton(ws)

            mod_file = ws / "engine.py"
            mod_file.write_text(
                "import os\n\n\ndef alpha():\n    return 1\n\n\nclass Worker:\n    def execute(self):\n        return 42\n",
                encoding="utf-8",
            )
            sh_file = ws / "run.sh"
            sh_file.write_text(
                "#!/usr/bin/env bash\ndeploy_app() {\n  echo ok\n}\n",
                encoding="utf-8",
            )

            parsed = verify_handoff.parse_evidence_pointer("engine.py:4-5#alpha@a1b2c3d")
            self.assertIsNotNone(parsed)
            self.assertEqual(parsed["file_part"], "engine.py")
            self.assertEqual(parsed["start"], 4)
            self.assertEqual(parsed["end"], 5)
            self.assertEqual(parsed["symbol"], "alpha")
            self.assertEqual(parsed["commit"], "a1b2c3d")

            oob_res = verify_handoff.resolve_and_validate_pointer("engine.py:1-50", ws)
            self.assertFalse(oob_res["valid"])
            self.assertIn("[Out-of-Bounds Pointer]", str(oob_res["error"]))

            broken_sym = verify_handoff.resolve_and_validate_pointer("engine.py:1-5#non_existent", ws)
            self.assertFalse(broken_sym["valid"])
            self.assertIn("[Broken Symbol Pointer]", str(broken_sym["error"]))

            method_res = verify_handoff.resolve_and_validate_pointer("engine.py:1-2#Worker.execute", ws)
            self.assertTrue(method_res["valid"])
            self.assertEqual(method_res["healed_ptr"], "engine.py:9-10#Worker.execute")

            sh_res = verify_handoff.resolve_and_validate_pointer("run.sh#deploy_app", ws)
            self.assertTrue(sh_res["valid"])
            self.assertEqual(sh_res["healed_ptr"], "run.sh:2-4#deploy_app")

            nested_span = verify_handoff._find_python_symbol_span(
                "class Outer:\n    class Inner:\n        @overload\n        def run(self, x: int) -> int: ...\n        def run(self, x: object) -> int:\n            return 1\n",
                "Outer.Inner.run",
            )
            self.assertEqual(nested_span, (5, 6))

            ts_span = verify_handoff._find_regex_symbol_span(
                ["function parse() {", '  const brace = "}";', "  // comment }", "  return 1;", "}"],
                "parse",
                ".ts",
            )
            self.assertEqual(ts_span, (1, 5))

            zh_md = verify_handoff.resolve_and_validate_pointer(".agents/pstack/pstack-core.md#剧本原样挂载", ws)
            self.assertTrue(zh_md["valid"])
            self.assertEqual(zh_md["healed_ptr"], ".agents/pstack/pstack-core.md:10-21#剧本原样挂载")

            brief_path = ws / ".agents" / "handoffs" / "active-brief.md"
            brief_path.write_text(
                """---
task_id: "test-heal-01"
role: "implementer"
target_agent: "codex"
playbook: ".agents/pstack/playbooks/bug-fix.md"
required_principles:
  - ".agents/pstack/principles/prove-it-works.md"
verify_cmd: "python3 -V"
---

## 1. User Goal (Restated)
Test pointer auto healing.

## 2. Consolidated Directives (History & Delta)
- Validate symbol healing.

## 3. Evidence Pointers (Read-Only Context)
- `engine.py:1-2#alpha`
- `engine.py:1-3#Worker.execute`

## 4. Deliverable Contract
1. Auto-heal drifted pointers.
""",
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                errs = verify_handoff.verify_brief(brief_path, schema_path, ws, fix_drift=True)
            self.assertEqual(errs, [])
            updated = brief_path.read_text(encoding="utf-8")
            self.assertIn("`engine.py:4-5#alpha`", updated)
            self.assertIn("`engine.py:9-10#Worker.execute`", updated)

    def test_prose_restate_and_unslop_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            draft = ws / "output-draft.md"
            draft.write_text(
                "> [Builder Restate] 目标是验证复述头剥离与散文校验。\n"
                "> 前提是杜绝破折号与套话。\n\n"
                "# Clean Title\n\n"
                "单轮交接延迟下降 40% `[实测 Measured]`。\n",
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                rc_ok = verify_prose.verify_file(draft, require_restate=True)
            self.assertEqual(rc_ok, 0)

            stripped = verify_prose.strip_builder_restate(draft.read_text(encoding="utf-8"))
            self.assertNotIn("[Builder Restate]", stripped)
            self.assertTrue(stripped.startswith("# Clean Title"))

            bad_draft = ws / "output-draft.md"
            em_dash = "\u2014"
            bad_draft.write_text(
                f"# Missing Restate\n\n这句话包含破折号{em_dash}而且没有实测标签。\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc_bad = verify_prose.verify_file(bad_draft, require_restate=True)
            self.assertNotEqual(rc_bad, 0)
            out = buf.getvalue()
            self.assertIn("[Builder Restate Missing]", out)
            self.assertIn("[Dash Ban]", out)
            self.assertIn("[Epistemic Gate]", out)

    def test_code_slop_and_custom_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            clean_py = ws / "clean.py"
            clean_py.write_text(
                "# Why: Kernel pipe buffer caps atomic writes at 4096 bytes on macOS.\n"
                "def compute(val: int) -> int:\n"
                "    return val + 1\n",
                encoding="utf-8",
            )
            self.assertEqual(verify_code_slop.check_file(clean_py, []), [])

            slop_py = ws / "slop.py"
            comment_line = chr(35) + " initialize the variables\n"
            swallowed_block = "try:\n    x = 1\n" + "except Exception:\n    " + "pass\n"
            slop_py.write_text(comment_line + swallowed_block + "FORBIDDEN_CALL()\n", encoding="utf-8")

            custom_rules = [("ban-forbidden", r"FORBIDDEN_CALL\(", "Do not use FORBIDDEN_CALL")]
            errs = verify_code_slop.check_file(slop_py, custom_rules)
            joined = "\n".join(errs)
            self.assertIn("[Comment Sicko]", joined)
            self.assertIn("[Swallowed Exception]", joined)
            self.assertIn("[Custom Rule:ban-forbidden]", joined)

    def test_code_slop_collect_files_respects_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo with space"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "a@a"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "a"], cwd=repo, check=True)
            (repo / ".gitignore").write_text("ignored.py\nnode_modules/\n")
            (repo / "tracked.py").write_text("x = 1\n")
            (repo / "ignored.py").write_text("x = 2\n")
            (repo / "new file.py").write_text("x = 3\n")
            dep = repo / "node_modules" / "dep.py"
            dep.parent.mkdir()
            dep.write_text("x = 4\n")
            (repo / "later-ignored.py").write_text("x = 5\n")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
            with open(repo / ".gitignore", "a") as fh:
                fh.write("later-ignored.py\n")

            names = [f.name for f in verify_code_slop.collect_files([str(repo)])]
            self.assertIn("tracked.py", names)
            self.assertIn("new file.py", names)
            self.assertIn("later-ignored.py", names)
            self.assertNotIn("ignored.py", names)
            self.assertNotIn("dep.py", names)

            explicit = [f.name for f in verify_code_slop.collect_files([str(repo / "ignored.py")])]
            self.assertEqual(explicit, ["ignored.py"])

            plain = Path(tmp) / "plain"
            plain.mkdir()
            (plain / "b.py").write_text("x = 1\n")
            self.assertIn("b.py", [f.name for f in verify_code_slop.collect_files([str(plain)])])

    def test_session_snapshot_budget_and_crash_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            ensure_workspace_skeleton(ws)
            logs_dir = ws / ".agents" / "handoffs" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / "spawn-task1-codex.log").write_text(
                "Starting runner...\n[TIMEOUT] Subagent codex exceeded 10s limit.\n",
                encoding="utf-8",
            )
            snap_path = generate_snapshot(ws, "CRASH_RECOVERY: runner=codex exit=124")
            lines = snap_path.read_text(encoding="utf-8").splitlines()
            self.assertLessEqual(len(lines), 20)
            content = "\n".join(lines)
            self.assertIn("Last Spawn Status", content)
            self.assertIn("spawn-task1-codex.log", content)

    def test_onboard_toolchain_detection(self) -> None:
        pstack_cmd = detect_verify_cmd(REPO_ROOT, profile="strict")
        self.assertIn("python3 -m unittest discover -s tests -q", pstack_cmd)

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            (ws / "package.json").write_text(
                '{"scripts": {"test": "vitest run", "lint": "eslint .", "typecheck": "tsc --noEmit"}}',
                encoding="utf-8",
            )
            self.assertEqual(
                detect_verify_cmd(ws, profile="strict"),
                "npm test && npm run lint && npm run typecheck",
            )
            self.assertEqual(detect_verify_cmd(ws, profile="fast"), "npm test")

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            (ws / "Cargo.toml").write_text("[package]\nname = 'demo'\n", encoding="utf-8")
            self.assertEqual(
                detect_verify_cmd(ws, profile="strict"),
                "cargo test --quiet && cargo clippy --quiet",
            )

    def test_spawner_workbuddy_and_crash_trap(self) -> None:
        spawn_sh = SCRIPTS_DIR / "ag-spawn.sh"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            ensure_workspace_skeleton(ws)
            env = os.environ.copy()
            env["PSTACK_WORKSPACE"] = str(ws)

            proc_wb = subprocess.run(
                [str(spawn_sh), "workbuddy"],
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_wb.returncode, 0)
            self.assertTrue((ws / ".agents" / "handoffs" / "workbuddy-prompt.txt").is_file())

            env["PSTACK_SPAWN_TEST_CMD"] = "echo 'simulated failure'; exit 7"
            proc_fail = subprocess.run(
                [str(spawn_sh), "codex", "--timeout", "5"],
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_fail.returncode, 7)
            snap = ws / ".agents" / "handoffs" / "session-snapshot.md"
            self.assertTrue(snap.is_file())
            self.assertIn("CRASH_RECOVERY", snap.read_text(encoding="utf-8"))

            env["PSTACK_SPAWN_TEST_CMD"] = "echo start; sleep 4; echo done"
            proc_timeout = subprocess.run(
                [str(spawn_sh), "codex", "--timeout", "0.4"],
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_timeout.returncode, 124)

    def test_bench_suite_execution(self) -> None:
        comp = measure_context_compression(REPO_ROOT, REPO_ROOT)
        self.assertGreater(comp["pstack_tier0_plus_tier1_brief"]["token_reduction_pct"], 50.0)
        cases = run_adversarial_mutation_suite(REPO_ROOT)
        self.assertEqual(len(cases), 12)
        self.assertTrue(all(c["intercepted"] for c in cases))

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp).resolve()
            with redirect_stdout(io.StringIO()):
                rc_live = run_live_ab_experiment(REPO_ROOT, "workbuddy", out_dir=out_dir)
            self.assertEqual(rc_live, 0)
            tsv_text = (out_dir / "ab-experiments.tsv").read_text(encoding="utf-8")
            self.assertIn("workbuddy", tsv_text)
            self.assertIn("100.0%", tsv_text)

    def test_chaos_partial_write_quarantine_and_idempotent_retry(self) -> None:
        spawn_sh = SCRIPTS_DIR / "ag-spawn.sh"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            subprocess.run(["git", "init"], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=ws, capture_output=True, check=True)

            ensure_workspace_skeleton(ws)
            calc_py = ws / "calc.py"
            calc_py.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=ws, capture_output=True, check=True)

            env = os.environ.copy()
            env["PSTACK_WORKSPACE"] = str(ws)

            env["PSTACK_SPAWN_TEST_CMD"] = "echo 'def corrupt(:' >> calc.py && touch dirty_partial.tmp && exit 1"
            proc_crash = subprocess.run(
                [str(spawn_sh), "codex"],
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_crash.returncode, 1)

            calc_text = calc_py.read_text(encoding="utf-8")
            self.assertNotIn("def corrupt(:", calc_text)
            self.assertIn("def add", calc_text)
            self.assertFalse((ws / "dirty_partial.tmp").exists())

            patches = list((ws / ".agents" / "handoffs" / "logs").glob("crash-partial-*.patch"))
            self.assertEqual(len(patches), 1)
            patch_content = patches[0].read_text(encoding="utf-8")
            self.assertIn("def corrupt(:", patch_content)

            proc_apply = subprocess.run(
                ["git", "apply", "--check", str(patches[0])],
                cwd=ws,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_apply.returncode, 0, f"Corrupted patch generated: {proc_apply.stderr}")

            snap_file = ws / ".agents" / "handoffs" / "session-snapshot.md"
            self.assertTrue(snap_file.is_file())
            snap_lines = snap_file.read_text(encoding="utf-8").splitlines()
            self.assertLessEqual(len(snap_lines), 20)
            self.assertIn("Quarantined Patch", "\n".join(snap_lines))

            env["PSTACK_SPAWN_TEST_CMD"] = "echo 'def sub(a: int, b: int) -> int:\n    return a - b' >> calc.py && exit 0"
            proc_retry = subprocess.run(
                [str(spawn_sh), "codex"],
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_retry.returncode, 0)
            retry_calc_text = calc_py.read_text(encoding="utf-8")
            self.assertIn("def sub", retry_calc_text)
            self.assertNotIn("def corrupt(:", retry_calc_text)

    def test_chaos_preserves_pre_spawn_uncommitted_baseline(self) -> None:
        spawn_sh = SCRIPTS_DIR / "ag-spawn.sh"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            subprocess.run(["git", "init"], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=ws, capture_output=True, check=True)

            ensure_workspace_skeleton(ws)
            code_py = ws / "code.py"
            code_py.write_text("def base():\n    return 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=ws, capture_output=True, check=True)

            code_py.write_text("def base():\n    return 1\n\ndef user_work():\n    return 42\n", encoding="utf-8")

            env = os.environ.copy()
            env["PSTACK_WORKSPACE"] = str(ws)
            env["PSTACK_SPAWN_TEST_CMD"] = "echo 'syntax error :::' >> code.py && exit 1"

            proc = subprocess.run(
                [str(spawn_sh), "codex"],
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

            restored = code_py.read_text(encoding="utf-8")
            self.assertIn("user_work", restored)
            self.assertNotIn("syntax error", restored)

    def test_chaos_no_quarantine_flag(self) -> None:
        spawn_sh = SCRIPTS_DIR / "ag-spawn.sh"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            subprocess.run(["git", "init"], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=ws, capture_output=True, check=True)

            ensure_workspace_skeleton(ws)
            test_py = ws / "test.py"
            test_py.write_text("def ok(): pass\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=ws, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=ws, capture_output=True, check=True)

            env = os.environ.copy()
            env["PSTACK_WORKSPACE"] = str(ws)
            env["PSTACK_SPAWN_TEST_CMD"] = "echo 'def dirty(): pass' >> test.py && exit 1"

            proc = subprocess.run(
                [str(spawn_sh), "--no-quarantine", "codex"],
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

            self.assertIn("def dirty(): pass", test_py.read_text(encoding="utf-8"))
            patches = list((ws / ".agents" / "handoffs" / "logs").glob("crash-partial-*.patch"))
            self.assertEqual(len(patches), 1)

    def test_sandbox_ab_suite_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp).resolve()
            results = run_sandbox_ab_suite(REPO_ROOT, out_dir=out_dir)
            self.assertEqual(len(results), 3)
            self.assertTrue(all(t["treatment_verdict"] == "PASS" for t in results))
            tsv_path = out_dir / "ab-experiments.tsv"
            self.assertTrue(tsv_path.is_file())
            tsv_text = tsv_path.read_text(encoding="utf-8")
            self.assertIn("Task 1: bug-fix-state-machine", tsv_text)
            self.assertIn("Task 2: feature-cli-subcmd", tsv_text)
            self.assertIn("Task 3: refactor-slop-cleanup", tsv_text)

    def test_blind_verifier_and_epistemic_tiers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            ensure_workspace_skeleton(ws)

            doc = ws / "epistemic_tiers.md"
            doc.write_text(
                "> [Builder Restate] 目标是验证三级实证标签。\n\n"
                "离线指标达成预期 `[离线实测 Offline-Measured]`。\n"
                "沙箱模拟门禁拦截有效 `[沙箱模拟 Sim-Verified]`。\n"
                "真机执行全部绿灯 `[真机实测 Live-Agent]`。\n",
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                rc_doc = verify_prose.verify_file(doc, require_restate=True)
            self.assertEqual(rc_doc, 0)

            with redirect_stdout(io.StringIO()):
                rc_blind = pstack_verify.prep_verifier_digest(ws, blind=True)
            self.assertEqual(rc_blind, 0)
            blind_file = ws / ".agents" / "handoffs" / "blind-review-pack.md"
            self.assertTrue(blind_file.is_file())
            blind_lines = blind_file.read_text(encoding="utf-8").splitlines()
            self.assertLessEqual(len(blind_lines), 25)
            blind_content = "\n".join(blind_lines)
            self.assertIn("User Goal", blind_content)
            self.assertIn("Deliverable Contract", blind_content)
            self.assertNotIn("[Builder Restate]", blind_content)

    def test_router_goal_classification_and_brief_generation(self) -> None:
        c1 = classify_goal("修复登录超时 Bug")
        self.assertEqual(c1["intent"], "bug-fix")
        self.assertEqual(c1["role"], "builder")
        self.assertEqual(c1["model_tier"], "fast_tier")

        c2 = classify_goal("多阶段并行工作流协同调度")
        self.assertEqual(c2["intent"], "swarm")
        self.assertEqual(c2["role"], "coordinator")
        self.assertEqual(c2["model_tier"], "deep_tier")

        c3 = classify_goal("系统核心架构重组与跨模块深层设计")
        self.assertEqual(c3["intent"], "architecture-feature")
        self.assertEqual(c3["role"], "architect")
        self.assertEqual(c3["model_tier"], "deep_tier")

        c4 = classify_goal("发布推文总结最近提交")
        self.assertEqual(c4["intent"], "tech-thread")
        self.assertEqual(c4["role"], "builder")
        self.assertEqual(c4["model_tier"], "fast_tier")

        c5 = classify_goal("重构清理冗余代码")
        self.assertEqual(c5["intent"], "refactor")
        self.assertEqual(c5["role"], "builder")
        self.assertEqual(c5["model_tier"], "fast_tier")

        c6 = classify_goal("对代码进行独立安全审查")
        self.assertEqual(c6["intent"], "interrogate")
        self.assertEqual(c6["role"], "reviewer")
        self.assertEqual(c6["model_tier"], "deep_tier")

        c7 = classify_goal("新增用户导出报表功能")
        self.assertEqual(c7["intent"], "architecture-feature")
        self.assertEqual(c7["role"], "builder")
        self.assertEqual(c7["model_tier"], "fast_tier")

        c8 = classify_goal("调研 WebGPU 跨平台方案")
        self.assertEqual(c8["intent"], "figure-it-out")
        self.assertEqual(c8["role"], "architect")
        self.assertEqual(c8["model_tier"], "deep_tier")

        pointers1, allowed1 = auto_discover_pointers_and_scope("修复路由 Bug", REPO_ROOT)
        self.assertTrue(len(pointers1) > 0)
        self.assertIn("scripts/*", allowed1)

        pointers2, allowed2 = auto_discover_pointers_and_scope(REPO_ROOT, "修复路由 Bug")
        self.assertEqual(pointers1, pointers2)

        schema_path = REPO_ROOT / ".agents" / "handoffs" / "handoff-schema.json"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            ensure_workspace_skeleton(ws)
            brief_file = generate_brief("修复登录超时 Bug 并补充单元测试", ws)
            self.assertTrue(brief_file.is_file())
            with redirect_stdout(io.StringIO()):
                errs = verify_handoff.verify_brief(brief_file, schema_path, ws)
            self.assertEqual(errs, [])

    def test_worktree_sandbox_lifecycle_and_scope_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)

            sandbox = WorktreeSandbox("test-node-1", repo)
            worktree_dir = sandbox.create()
            self.assertTrue(worktree_dir.is_dir())

            (worktree_dir / "src" / "app.py").write_text("x = 2\n", encoding="utf-8")
            clean_violations = sandbox.check_scope(["src/*"])
            self.assertEqual(clean_violations, [])

            (worktree_dir / "bad_file.txt").write_text("leak\n", encoding="utf-8")
            dirty_violations = sandbox.check_scope(["src/*"])
            self.assertIn("bad_file.txt", dirty_violations)

            subprocess.run(["git", "add", "."], cwd=worktree_dir, check=True)
            subprocess.run(["git", "commit", "-qm", "committed leak"], cwd=worktree_dir, check=True)
            committed_violations = sandbox.check_scope(["src/*"])
            self.assertIn("bad_file.txt", committed_violations)

            sandbox.cleanup()
            self.assertFalse(worktree_dir.exists())

    def test_scheduler_swarm_and_resume_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
            ensure_workspace_skeleton(repo)
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("def run(): pass\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)

            from pstack_scheduler import topological_sort_nodes
            cyclic_dag = {
                "a": {"depends_on": ["b"]},
                "b": {"depends_on": ["a"]},
            }
            with self.assertRaises(ValueError):
                topological_sort_nodes(cyclic_dag)

            with redirect_stdout(io.StringIO()):
                rc_swarm = execute_swarm(repo, dry_run=True)
            self.assertEqual(rc_swarm, 0)

            state_file = repo / ".agents" / "handoffs" / "dag-state.json"
            self.assertTrue(state_file.is_file())
            state = load_dag_state(repo)
            self.assertEqual(state["status"], "completed")
            self.assertTrue(all(node["status"] == "MERGED" for node in state["nodes"].values()))

            state["nodes"]["node-1"]["status"] = "VERIFIED"
            state["nodes"]["node-1"]["artifact_sha256"] = None
            state_file.write_text(importlib.import_module("json").dumps(state), encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                rc_resume = execute_resume(repo, dry_run=True)
            self.assertEqual(rc_resume, 0)
            resumed_state = load_dag_state(repo)
            self.assertIsNotNone(resumed_state["nodes"]["node-1"]["artifact_sha256"])

    def test_scheduler_arena_and_event_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
            ensure_workspace_skeleton(repo)
            (repo / "src").mkdir()
            (repo / "src" / "main.py").write_text("x = 10\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)

            with redirect_stdout(io.StringIO()):
                rc_arena = execute_arena(repo, candidates=["codex", "opencode"], dry_run=True)
            self.assertEqual(rc_arena, 0)

            events_file = repo / ".agents" / "handoffs" / "events.jsonl"
            self.assertTrue(events_file.is_file())
            _, events = load_tree_data(repo)
            event_types = [e["event_type"] for e in events]
            self.assertIn("ARENA_START", event_types)
            self.assertIn("ARENA_EVALUATION", event_types)

            dag_state = load_dag_state(repo)
            self.assertEqual(dag_state.get("mode"), "arena")
            self.assertEqual(dag_state.get("status"), "completed")
            self.assertIn(dag_state.get("winner"), ["codex", "opencode"])
            self.assertTrue(any(n["status"] == "WINNER" for n in dag_state["nodes"].values()))

    def test_tree_ascii_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
            ensure_workspace_skeleton(repo)
            (repo / "src").mkdir()
            (repo / "src" / "entry.py").write_text("pass\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)

            with redirect_stdout(io.StringIO()):
                execute_swarm(repo, dry_run=True)
            dag_data, events = load_tree_data(repo)
            tree_text = render_ascii_tree(dag_data, events)
            self.assertIn("TASK DAG TREE", tree_text)
            self.assertIn("node-1", tree_text)
            self.assertIn("node-2", tree_text)

    def test_abcd_randomized_benchmark_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp).resolve()
            with redirect_stdout(io.StringIO()):
                results = run_abcd_benchmark(REPO_ROOT, out_dir=out_dir, seed=42)
            self.assertEqual(len(results), 16)
            group_names = {r["group"] for r in results}
            self.assertIn("Group A (Native Codex)", group_names)
            self.assertIn("Group B (PStack + Codex)", group_names)
            self.assertIn("Group C (Native OpenCode)", group_names)
            self.assertIn("Group D (PStack + OpenCode)", group_names)
            tsv_path = out_dir / "ab-experiments.tsv"
            self.assertTrue(tsv_path.is_file())
            self.assertIn("Task 4: multi-module-swarm", tsv_path.read_text(encoding="utf-8"))

    def test_bilingual_repomap_pointer_ranking(self) -> None:
        pointers, allowed = auto_discover_pointers_and_scope(
            "修复状态机在超时后的断点恢复异常",
            REPO_ROOT,
        )
        self.assertTrue(len(pointers) > 0)
        joined = "\n".join(pointers)
        self.assertNotIn("pstack_bench.py#_load_script_module", joined)
        self.assertTrue(
            any(
                name in joined
                for name in ("pstack_session.py", "ag-spawn.sh", "pstack_scheduler.py")
            ),
            f"Expected state/timeout/session modules in top pointers, got: {pointers}",
        )
        self.assertIn("scripts/*", allowed)
        for ptr in pointers:
            res = verify_handoff.resolve_and_validate_pointer(ptr, REPO_ROOT)
            self.assertTrue(res["valid"], f"Invalid discovered pointer {ptr}: {res}")

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            (ws / "src").mkdir()
            (ws / "scripts").mkdir()
            (ws / "pkg").mkdir()
            (ws / "src" / "session_state.ts").write_text(
                "export async function resumeTimeoutState(id: string) {\n"
                "  if (!id) { return false; }\n"
                "  return true;\n"
                "}\n"
                "export const trackTimeoutState = async (id: string): Promise<boolean> => {\n"
                "  return id.length > 0;\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "scripts" / "spawn_guard.sh").write_text(
                "#!/usr/bin/env bash\n"
                "handle_spawn_timeout() {\n"
                "  echo timeout\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "pkg" / "state_machine.go").write_text(
                "package pkg\n"
                "type StateMachine struct{}\n"
                "func (s *StateMachine) RecoverTimeout() bool {\n"
                "  return true\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "src" / "timeout_state.rs").write_text(
                "pub(crate) async fn handle_timeout<'a>(key: &'a str) -> &'a str {\n"
                "    if key.is_empty() {\n"
                "        return \"empty\";\n"
                "    }\n"
                "    key\n"
                "}\n"
                "pub const fn compute_timeout_ms(base: u64) -> u64 {\n"
                "    base * 2\n"
                "}\n",
                encoding="utf-8",
            )
            multi_ptrs, multi_scope = auto_discover_pointers_and_scope(
                "修复状态机超时恢复异常",
                ws,
            )
            multi_joined = "\n".join(multi_ptrs)
            self.assertIn("src/session_state.ts", multi_joined)
            self.assertIn("resumeTimeoutState", multi_joined)
            self.assertIn("scripts/spawn_guard.sh", multi_joined)
            self.assertIn("pkg/state_machine.go", multi_joined)
            self.assertIn("RecoverTimeout", multi_joined)
            self.assertIn("src/timeout_state.rs:1-6#handle_timeout", multi_joined)
            self.assertIn("src/timeout_state.rs:7-9#compute_timeout_ms", multi_joined)
            self.assertIn("src/*", multi_scope)
            self.assertIn("scripts/*", multi_scope)
            self.assertIn("pkg/*", multi_scope)
            for ptr in multi_ptrs:
                res = verify_handoff.resolve_and_validate_pointer(ptr, ws)
                self.assertTrue(res["valid"], f"Invalid multi-lang pointer {ptr}: {res}")
                self.assertIsNone(res["drift_note"], f"Unexpected drift on {ptr}: {res}")

            hook_ptrs, _ = auto_discover_pointers_and_scope("修复预提交钩子权限", REPO_ROOT)
            self.assertTrue(
                any("pstack_hook.py" in p for p in hook_ptrs),
                f"Expected pstack_hook.py in top pointers for pre-commit hook query, got: {hook_ptrs}",
            )

    def test_parallel_swarm_and_3way_git_merge(self) -> None:
        levels = topological_levels(
            {
                "node-a": {"depends_on": []},
                "node-b": {"depends_on": []},
                "node-c": {"depends_on": ["node-a", "node-b"]},
            }
        )
        self.assertEqual(levels, [["node-a", "node-b"], ["node-c"]])

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
            ensure_workspace_skeleton(repo)

            (repo / "src").mkdir()
            shared_lines = [f"LINE_{i} = {i}" for i in range(1, 21)]
            (repo / "src" / "shared.py").write_text("\n".join(shared_lines) + "\n", encoding="utf-8")
            (repo / "src" / "obsolete.py").write_text("OLD = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)

            spec_path = repo / "swarm-spec.json"
            cmd_a = (
                "python3 -c 'from pathlib import Path; "
                "p = Path(\"src/shared.py\"); "
                "ls = p.read_text().splitlines(); "
                "ls[1] = \"LINE_2 = 200\"; "
                "p.write_text(\"\\n\".join(ls) + \"\\n\"); "
                "Path(\"src/obsolete.py\").unlink()'"
            )
            cmd_b = (
                "python3 -c 'from pathlib import Path; "
                "p = Path(\"src/shared.py\"); "
                "ls = p.read_text().splitlines(); "
                "ls[18] = \"LINE_19 = 1900\"; "
                "p.write_text(\"\\n\".join(ls) + \"\\n\"); "
                "Path(\"src/worker_b.py\").write_text(\"B = 2\\n\")'"
            )
            dag_spec = {
                "version": "3.1",
                "task_id": "parallel-3way-test",
                "nodes": {
                    "node-a": {
                        "id": "node-a",
                        "name": "wave0-a",
                        "role": "builder",
                        "tier": "fast_tier",
                        "model": "fast",
                        "allowed_paths": ["src/*"],
                        "depends_on": [],
                        "cmd": cmd_a,
                    },
                    "node-b": {
                        "id": "node-b",
                        "name": "wave0-b",
                        "role": "builder",
                        "tier": "fast_tier",
                        "model": "fast",
                        "allowed_paths": ["src/*"],
                        "depends_on": [],
                        "cmd": cmd_b,
                    },
                    "node-c": {
                        "id": "node-c",
                        "name": "wave1-verify",
                        "role": "verifier",
                        "tier": "fast_tier",
                        "model": "fast",
                        "allowed_paths": ["src/*"],
                        "depends_on": ["node-a", "node-b"],
                        "cmd": (
                            "python3 -c 'import sys; sys.path.insert(0, \"src\"); import worker_b; "
                            "from pathlib import Path; "
                            "assert \"LINE_2 = 200\" in Path(\"src/shared.py\").read_text(); "
                            "assert not Path(\"src/obsolete.py\").exists(); "
                            "Path(\"src/final.py\").write_text(f\"FINAL = {worker_b.B}\\n\")'"
                        ),
                    },
                },
            }
            spec_path.write_text(json.dumps(dag_spec), encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                rc = execute_swarm(repo, spec_path=spec_path, dry_run=False)
            self.assertEqual(rc, 0)

            merged_shared = (repo / "src" / "shared.py").read_text(encoding="utf-8")
            self.assertIn("LINE_2 = 200", merged_shared)
            self.assertIn("LINE_19 = 1900", merged_shared)
            self.assertFalse((repo / "src" / "obsolete.py").exists())
            self.assertTrue((repo / "src" / "worker_b.py").is_file())
            self.assertEqual((repo / "src" / "final.py").read_text(encoding="utf-8"), "FINAL = 2\n")

            state = load_dag_state(repo)
            state["nodes"]["node-c"]["status"] = "FAILED"
            state["nodes"]["node-c"]["artifact_sha256"] = None
            (repo / "src" / "final.py").unlink()
            (repo / ".agents" / "handoffs" / "dag-state.json").write_text(json.dumps(state), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                rc_res = execute_resume(repo, dry_run=False)
            self.assertEqual(rc_res, 0)
            self.assertEqual((repo / "src" / "final.py").read_text(encoding="utf-8"), "FINAL = 2\n")

            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "post-swarm"], cwd=repo, check=True)

            sb1 = WorktreeSandbox("conflict-1", repo)
            sb2 = WorktreeSandbox("conflict-2", repo)
            wt1 = sb1.create()
            wt2 = sb2.create()
            try:
                (wt1 / "src" / "shared.py").write_text("CONFLICT = 1\n", encoding="utf-8")
                (wt2 / "src" / "shared.py").write_text("CONFLICT = 2\n", encoding="utf-8")
                merge_worktree_to_workspace(wt1, repo, ["src/*"], base_commit=sb1.base_commit)
                with self.assertRaises(RuntimeError) as ctx:
                    merge_worktree_to_workspace(wt2, repo, ["src/*"], base_commit=sb2.base_commit)
                self.assertIn("[Merge Conflict]", str(ctx.exception))
                self.assertEqual((repo / "src" / "shared.py").read_text(encoding="utf-8"), "CONFLICT = 1\n")
                st_out = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True).stdout
                self.assertNotIn("UU ", st_out)
            finally:
                sb1.cleanup()
                sb2.cleanup()

        with tempfile.TemporaryDirectory() as tmp:
            nongit_ws = Path(tmp).resolve()
            (nongit_ws / "src").mkdir()
            (nongit_ws / "src" / "keep.py").write_text("KEEP = 1\n", encoding="utf-8")
            (nongit_ws / "src" / "drop.py").write_text("DROP = 1\n", encoding="utf-8")
            sb_ng = WorktreeSandbox("nongit-del", nongit_ws)
            wt_ng = sb_ng.create()
            try:
                (wt_ng / "src" / "drop.py").unlink()
                (nongit_ws / "src" / "concurrent_new.py").write_text("NEW = 1\n", encoding="utf-8")
                merge_worktree_to_workspace(wt_ng, nongit_ws, ["src/*"])
                self.assertFalse((nongit_ws / "src" / "drop.py").exists())
                self.assertTrue((nongit_ws / "src" / "keep.py").is_file())
                self.assertTrue((nongit_ws / "src" / "concurrent_new.py").is_file())
            finally:
                sb_ng.cleanup()

    def test_auto_rework_self_healing_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            ensure_workspace_skeleton(ws)
            target_py = ws / "worker.py"
            brief_path = ws / ".agents" / "handoffs" / "active-brief.md"

            def stateless_runner(round_num: int, brief: Path) -> int:
                brief_txt = brief.read_text(encoding="utf-8")
                if round_num == 1:
                    slop_comment = chr(35) + " initialize the variables\n"
                    target_py.write_text(slop_comment + "def run():\n    return 1\n", encoding="utf-8")
                    return 0
                if "[Round 2 Auto-Rework]" in brief_txt:
                    target_py.write_text("def run():\n    return 1\n", encoding="utf-8")
                    return 0
                return 1

            def gate_check(workspace: Path) -> tuple[int, str]:
                errs = verify_code_slop.check_file(workspace / "worker.py", [])
                if errs:
                    return 1, "\n".join(errs)
                return 0, "ALL CHECKS GREEN"

            with redirect_stdout(io.StringIO()):
                res = run_with_auto_rework(
                    ws,
                    brief_path=brief_path,
                    runner=stateless_runner,
                    max_rework=2,
                    verify_fn=gate_check,
                )

            self.assertEqual(res["exit_code"], 0)
            self.assertEqual(res["rework_count"], 1)
            self.assertEqual(res["rounds"], 2)
            brief_after = brief_path.read_text(encoding="utf-8")
            self.assertIn("[Round 2 Auto-Rework]", brief_after)
            self.assertIn("[Comment Sicko]", brief_after)

            _, events = load_tree_data(ws)
            event_types = [e["event_type"] for e in events]
            self.assertIn("AUTO_REWORK_TRIGGERED", event_types)

            spawn_sh = SCRIPTS_DIR / "ag-spawn.sh"
            marker = ws / ".rework_round_marker"
            env = os.environ.copy()
            env["PSTACK_WORKSPACE"] = str(ws)
            env["PSTACK_SPAWN_TEST_CMD"] = (
                f"if [ ! -f '{marker}' ]; then touch '{marker}'; echo '[FAIL] simulated round 1 failure'; exit 1; "
                "else echo '[OK] round 2 healed'; exit 0; fi"
            )
            proc = subprocess.run(
                [str(spawn_sh), "codex", "--max-rework", "1"],
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("[Round 2 Auto-Rework]", brief_path.read_text(encoding="utf-8"))

    def test_git_pre_commit_hook_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
            ensure_workspace_skeleton(repo)
            (repo / "app.py").write_text("def ok() -> int:\n    return 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)

            hooks_dir = repo / ".git" / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)
            existing_hook = hooks_dir / "pre-commit"
            existing_hook.write_text("#!/usr/bin/env bash\necho 'custom-existing-hook'\n", encoding="utf-8")
            existing_hook.chmod(0o755)

            with redirect_stdout(io.StringIO()):
                self.assertEqual(pstack_hook.install_hook(repo), 0)
                self.assertEqual(pstack_hook.status_hook(repo), 0)

            self.assertTrue((hooks_dir / "pre-commit.pstack-backup").is_file())
            self.assertIn(pstack_hook.MANAGED_MARKER, existing_hook.read_text(encoding="utf-8"))

            slop_comment = chr(35) + " initialize the variables\n"
            (repo / "bad.py").write_text(slop_comment + "x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "bad.py"], cwd=repo, check=True)
            commit_bad = subprocess.run(
                ["git", "commit", "-m", "bad commit"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(commit_bad.returncode, 0)
            self.assertIn("[Comment Sicko]", commit_bad.stdout + commit_bad.stderr)

            (repo / "bad.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "bad.py"], cwd=repo, check=True)
            commit_good = subprocess.run(
                ["git", "commit", "-m", "clean commit"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(commit_good.returncode, 0, commit_good.stdout + commit_good.stderr)
            self.assertIn("custom-existing-hook", commit_good.stdout + commit_good.stderr)

            with redirect_stdout(io.StringIO()):
                self.assertEqual(pstack_hook.uninstall_hook(repo), 0)
                self.assertNotEqual(pstack_hook.status_hook(repo), 0)
            self.assertTrue(existing_hook.is_file())
            self.assertIn("custom-existing-hook", existing_hook.read_text(encoding="utf-8"))

    def test_mcp_server_jsonrpc_protocol(self) -> None:
        mcp_script = SCRIPTS_DIR / "pstack_mcp.py"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp).resolve()
            ensure_workspace_skeleton(ws)

            requests = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "pstack_route",
                        "arguments": {"goal": "修复状态机超时异常", "workspace": str(ws)},
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "pstack_tree",
                        "arguments": {"json": True, "workspace": str(ws)},
                    },
                },
            ]
            stdin_payload = "\n".join(json.dumps(r) for r in requests) + "\n"
            proc = subprocess.run(
                [sys.executable, str(mcp_script)],
                input=stdin_payload,
                cwd=ws,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            resp_lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
            self.assertEqual(len(resp_lines), 4, f"Expected 4 responses (no response for notification): {resp_lines}")

            responses = [json.loads(ln) for ln in resp_lines]
            self.assertEqual(responses[0]["id"], 1)
            self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "pstack-mcp")

            tools = responses[1]["result"]["tools"]
            tool_names = [t["name"] for t in tools]
            self.assertEqual(
                tool_names,
                ["pstack_route", "pstack_verify", "pstack_swarm", "pstack_arena", "pstack_tree"],
            )

            route_data = json.loads(responses[2]["result"]["content"][0]["text"])
            self.assertEqual(route_data["status"], "ROUTED")
            self.assertTrue((ws / ".agents" / "handoffs" / "active-brief.md").is_file())

            tree_data = json.loads(responses[3]["result"]["content"][0]["text"])
            self.assertIn("dag_state", tree_data)
            self.assertIn("events", tree_data)

            framed_reqs = [
                {"jsonrpc": "2.0", "id": 10, "method": "initialize", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 11,
                    "method": "tools/call",
                    "params": {
                        "name": "pstack_route",
                        "arguments": {"goal": "修复状态机超时恢复异常", "workspace": str(ws)},
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 12,
                    "method": "tools/call",
                    "params": {
                        "name": "pstack_swarm",
                        "arguments": {"goal": "Parallel DAG check", "dry_run": True, "workspace": str(ws)},
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 13,
                    "method": "tools/call",
                    "params": {
                        "name": "pstack_arena",
                        "arguments": {"runners": ["codex", "opencode"], "dry_run": True, "workspace": str(ws)},
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 14,
                    "method": "tools/call",
                    "params": {
                        "name": "pstack_verify",
                        "arguments": {"mode": "handoff", "workspace": str(ws)},
                    },
                },
            ]
            framed_bytes = b""
            for req in framed_reqs:
                body = json.dumps(req, ensure_ascii=False).encode("utf-8")
                framed_bytes += f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body

            proc_framed = subprocess.run(
                [sys.executable, str(mcp_script)],
                input=framed_bytes,
                cwd=ws,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc_framed.returncode, 0, proc_framed.stderr.decode("utf-8", errors="replace"))
            raw_out = proc_framed.stdout
            parsed_framed: list[dict] = []
            offset = 0
            while offset < len(raw_out):
                hdr_end = raw_out.find(b"\r\n\r\n", offset)
                self.assertNotEqual(hdr_end, -1, f"Missing Content-Length header at offset {offset}")
                hdr_txt = raw_out[offset:hdr_end].decode("ascii")
                clen = int(hdr_txt.split(":", 1)[1].strip())
                body_start = hdr_end + 4
                body_slice = raw_out[body_start:body_start + clen]
                self.assertEqual(len(body_slice), clen)
                parsed_framed.append(json.loads(body_slice.decode("utf-8")))
                offset = body_start + clen

            self.assertEqual([r["id"] for r in parsed_framed], [10, 11, 12, 13, 14])
            swarm_payload = json.loads(parsed_framed[2]["result"]["content"][0]["text"])
            self.assertTrue(swarm_payload["passed"])
            arena_payload = json.loads(parsed_framed[3]["result"]["content"][0]["text"])
            self.assertIn(arena_payload["winner"], ["codex", "opencode"])
            verify_payload = json.loads(parsed_framed[4]["result"]["content"][0]["text"])
            self.assertTrue(verify_payload["passed"])

            digest_sample = extract_gate_failure_digest("xml_parser error: bad tag\nx [Comment Sicko]: slop")
            self.assertIn("xml_parser error: bad tag", digest_sample)
            self.assertIn("[Comment Sicko]: slop", digest_sample)

            ct_body = json.dumps({"jsonrpc": "2.0", "id": 20, "method": "ping", "params": {}}, ensure_ascii=False).encode("utf-8")
            bad_params_body = json.dumps({"jsonrpc": "2.0", "id": 21, "method": "tools/call", "params": "bad"}, ensure_ascii=False).encode("utf-8")
            ct_payload = (
                f"Content-Type: application/vscode-jsonrpc; charset=utf-8\r\nContent-Length: {len(ct_body)}\r\n\r\n".encode("ascii")
                + ct_body
                + f"Content-Length: {len(bad_params_body)}\r\n\r\n".encode("ascii")
                + bad_params_body
            )
            proc_ct = subprocess.run(
                [sys.executable, str(mcp_script)],
                input=ct_payload,
                cwd=ws,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc_ct.returncode, 0, proc_ct.stderr.decode("utf-8", errors="replace"))
            ct_out = proc_ct.stdout
            ct_resps: list[dict] = []
            ct_off = 0
            while ct_off < len(ct_out):
                hdr_end = ct_out.find(b"\r\n\r\n", ct_off)
                self.assertNotEqual(hdr_end, -1)
                clen = int(ct_out[ct_off:hdr_end].decode("ascii").split(":", 1)[1].strip())
                bstart = hdr_end + 4
                ct_resps.append(json.loads(ct_out[bstart:bstart + clen].decode("utf-8")))
                ct_off = bstart + clen
            self.assertEqual(ct_resps[0]["id"], 20)
            self.assertEqual(ct_resps[0]["result"], {})
            self.assertEqual(ct_resps[1]["id"], 21)
            self.assertEqual(ct_resps[1]["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
