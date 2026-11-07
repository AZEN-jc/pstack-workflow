#!/usr/bin/env python3
"""
Unit test suite for Pstack v2.1 Verifiable Engineering Harness.
Run via: python3 -m unittest discover -s tests -q
"""
import importlib.util
import io
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

from pstack_bench import measure_context_compression, run_adversarial_mutation_suite
from pstack_onboard import detect_verify_cmd
from pstack_resolver import ensure_workspace_skeleton, get_pstack_home, get_workspace_root, resolve_asset
from pstack_session import generate_snapshot


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

    def test_bench_suite_execution(self) -> None:
        comp = measure_context_compression(REPO_ROOT, REPO_ROOT)
        self.assertGreater(comp["pstack_tier0_plus_tier1_brief"]["token_reduction_pct"], 50.0)
        cases = run_adversarial_mutation_suite(REPO_ROOT)
        self.assertEqual(len(cases), 12)
        self.assertTrue(all(c["intercepted"] for c in cases))


if __name__ == "__main__":
    unittest.main()
