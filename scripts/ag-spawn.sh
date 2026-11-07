#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(python3 -c 'import os,sys; print(os.path.dirname(os.path.realpath(sys.argv[1])))' "${BASH_SOURCE[0]}")"
WORKSPACE_ROOT="$(python3 "$SCRIPT_DIR/pstack_resolver.py" --workspace-root)"

SPAWN_TIMEOUT="${PSTACK_SPAWN_TIMEOUT:-600}"
PSTACK_CODEX_FLAGS="${PSTACK_CODEX_FLAGS:---full-auto}"
ARG1=""
ARG2=""

DO_QUARANTINE=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout)
      SPAWN_TIMEOUT="${2:-600}"
      shift 2
      ;;
    --timeout=*)
      SPAWN_TIMEOUT="${1#*=}"
      shift
      ;;
    --no-quarantine)
      DO_QUARANTINE=0
      shift
      ;;
    *)
      if [[ -z "$ARG1" ]]; then
        ARG1="$1"
      elif [[ -z "$ARG2" ]]; then
        ARG2="$1"
      fi
      shift
      ;;
  esac
done

case "$ARG1" in
  opencode|codex|codex-review|workbuddy|pi|claude|antigravity|agy|dry-run)
    BRIEF_INPUT="$WORKSPACE_ROOT/.agents/handoffs/active-brief.md"
    RUNNER="$ARG1"
    ;;
  "")
    BRIEF_INPUT="$WORKSPACE_ROOT/.agents/handoffs/active-brief.md"
    RUNNER="opencode"
    ;;
  *)
    BRIEF_INPUT="$ARG1"
    RUNNER="${ARG2:-opencode}"
    ;;
esac

if [[ "$BRIEF_INPUT" = /* ]]; then
  BRIEF_FILE="$BRIEF_INPUT"
elif [[ -f "$(pwd)/$BRIEF_INPUT" ]]; then
  BRIEF_FILE="$(cd "$(dirname "$(pwd)/$BRIEF_INPUT")" && pwd)/$(basename "$BRIEF_INPUT")"
else
  BRIEF_FILE="$WORKSPACE_ROOT/$BRIEF_INPUT"
fi

if [[ ! -f "$BRIEF_FILE" ]]; then
  echo "[Error] Handoff brief not found: $BRIEF_FILE"
  exit 1
fi

WORKSPACE_ROOT="$(python3 -c 'import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from pstack_resolver import get_workspace_root; print(get_workspace_root(Path(sys.argv[2])))' "$SCRIPT_DIR" "$BRIEF_FILE")"
export PSTACK_WORKSPACE="$WORKSPACE_ROOT"

echo ">>> [pstack gate] Validating handoff brief & ledger before spawning subagent..."
python3 "$SCRIPT_DIR/verify-handoff.py" "$BRIEF_FILE" --fix

TASK_ID="$(python3 -c '
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
m = re.search(r"^task_id:\s*[\"\x27]?([^\"\x27\n]+)[\"\x27]?", text, re.MULTILINE)
raw = m.group(1).strip() if m else "task"
print(re.sub(r"[^A-Za-z0-9_.-]+", "-", raw))
' "$BRIEF_FILE")"

LOG_DIR="$WORKSPACE_ROOT/.agents/handoffs/logs"
mkdir -p "$LOG_DIR"
LOG_REL=".agents/handoffs/logs/spawn-${TASK_ID}-${RUNNER}.log"
LOG_FILE="$WORKSPACE_ROOT/$LOG_REL"
STATUS_FILE="$LOG_DIR/last-spawn-status.json"

SPAWN_ACTIVE=0
on_spawn_exit() {
  local rc=$?
  if [[ "$SPAWN_ACTIVE" -eq 1 && "$rc" -ne 0 ]]; then
    PATCH_REL="$(python3 - "$WORKSPACE_ROOT" "$TASK_ID" "$RUNNER" "$rc" "$LOG_REL" "$LOG_FILE" "$STATUS_FILE" "$DO_QUARANTINE" <<'PY'
import json, os, subprocess, sys
from pathlib import Path

ws = Path(sys.argv[1]).resolve()
task_id = sys.argv[2]
runner = sys.argv[3]
rc = int(sys.argv[4])
log_rel = sys.argv[5]
log_file = Path(sys.argv[6])
status_path = Path(sys.argv[7])
do_quarantine = int(sys.argv[8]) == 1

snap_file = ws / ".agents" / "handoffs" / "logs" / f".pre-spawn-{task_id}.json"
pre_state = {"is_git": False, "untracked": [], "modified": {}}
if snap_file.exists():
    try:
        pre_state = json.loads(snap_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[pre-spawn] snapshot unreadable, using defaults: {exc}", file=sys.stderr)

def run_git(args):
    try:
        p = subprocess.run(["git"] + args, cwd=ws, capture_output=True, text=True, check=False)
        return p.stdout
    except Exception:
        return ""

patch_rel = ""
if pre_state.get("is_git"):
    current_untracked = [ln.strip() for ln in run_git(["ls-files", "--others", "--exclude-standard"]).splitlines() if ln.strip()]
    current_untracked = [u for u in current_untracked if not u.startswith(".agents/handoffs/logs/")]
    pre_untracked = set(pre_state.get("untracked", []))
    new_untracked = [u for u in current_untracked if u not in pre_untracked]

    current_modified = [ln.strip() for ln in run_git(["diff", "--name-only"]).splitlines() if ln.strip()]
    pre_modified = pre_state.get("modified", {})

    dirty_tracked = []
    for mf in current_modified:
        cur_diff = run_git(["diff", "--", mf])
        if mf not in pre_modified or cur_diff != pre_modified.get(mf):
            dirty_tracked.append(mf)

    if dirty_tracked or new_untracked:
        patch_path = ws / ".agents" / "handoffs" / "logs" / f"crash-partial-{task_id}.patch"
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        patch_chunks = []
        if dirty_tracked:
            d_out = run_git(["diff", "--"] + dirty_tracked)
            if d_out.strip():
                patch_chunks.append(d_out.strip())
        for nu in new_untracked:
            nu_path = ws / nu
            if nu_path.is_file():
                nu_text = nu_path.read_text(encoding="utf-8", errors="ignore")
                patch_chunks.append(f"diff --git a/{nu} b/{nu}\nnew file mode 100644\n--- /dev/null\n+++ b/{nu}\n@@ -0,0 +1 @@\n" + nu_text)
        if patch_chunks:
            patch_path.write_text("\n\n".join(patch_chunks) + "\n", encoding="utf-8")
            patch_rel = f".agents/handoffs/logs/crash-partial-{task_id}.patch"

        if do_quarantine:
            for dt in dirty_tracked:
                subprocess.run(["git", "checkout", "HEAD", "--", dt], cwd=ws, check=False)
            for nu in new_untracked:
                nu_path = ws / nu
                if nu_path.is_file():
                    try:
                        nu_path.unlink()
                    except OSError:
                        pass

lines = [ln.strip() for ln in log_file.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()] if log_file.exists() else []
tail = lines[-1][:72] if lines else f"exit={rc}"
status_data = {
    "runner": runner,
    "exit_code": rc,
    "log_file": log_rel,
    "tail": tail,
}
if patch_rel:
    status_data["quarantined_patch"] = patch_rel

status_path.write_text(json.dumps(status_data, ensure_ascii=False), encoding="utf-8")
if patch_rel:
    sys.stdout.write(patch_rel)
PY
)"
    if [[ -n "$PATCH_REL" ]]; then
      echo "[pstack quarantine] Saved partial dirty-tree diff -> $PATCH_REL"
      if [[ "$DO_QUARANTINE" -eq 1 ]]; then
        echo "[pstack quarantine] Restored working tree to pre-spawn baseline (idempotent recovery)."
      fi
      python3 "$SCRIPT_DIR/pstack-session.py" pause "CRASH_RECOVERY: runner=$RUNNER exit=$rc log=$LOG_REL | Quarantined Patch: $PATCH_REL" || true
    else
      python3 "$SCRIPT_DIR/pstack-session.py" pause "CRASH_RECOVERY: runner=$RUNNER exit=$rc log=$LOG_REL" || true
    fi
  elif [[ "$SPAWN_ACTIVE" -eq 1 && "$rc" -eq 0 ]]; then
    rm -f "$LOG_DIR/.pre-spawn-${TASK_ID}.json" 2>/dev/null || true
  fi
}
trap on_spawn_exit EXIT

run_with_timeout_and_log() {
  python3 - "$WORKSPACE_ROOT" "$TASK_ID" "$LOG_DIR" <<'PY'
import json, os, subprocess, sys
from pathlib import Path

ws = Path(sys.argv[1]).resolve()
task_id = sys.argv[2]
log_dir = Path(sys.argv[3]).resolve()
log_dir.mkdir(parents=True, exist_ok=True)
snap_file = log_dir / f".pre-spawn-{task_id}.json"

def run_git(args):
    try:
        p = subprocess.run(["git"] + args, cwd=ws, capture_output=True, text=True, check=False)
        return p.stdout
    except Exception:
        return ""

is_git = run_git(["rev-parse", "--is-inside-work-tree"]).strip() == "true"
snapshot = {"is_git": is_git, "untracked": [], "modified": {}}
if is_git:
    untracked = [ln.strip() for ln in run_git(["ls-files", "--others", "--exclude-standard"]).splitlines() if ln.strip()]
    snapshot["untracked"] = [u for u in untracked if not u.startswith(".agents/handoffs/logs/")]
    modified_files = [ln.strip() for ln in run_git(["diff", "--name-only"]).splitlines() if ln.strip()]
    for mf in modified_files:
        snapshot["modified"][mf] = run_git(["diff", "--", mf])
snap_file.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
PY
  SPAWN_ACTIVE=1
  python3 - "$SPAWN_TIMEOUT" "$LOG_FILE" "$STATUS_FILE" "$RUNNER" "$LOG_REL" "$@" <<'PY'
import json, os, signal, subprocess, sys
from pathlib import Path

timeout_sec = float(sys.argv[1])
log_path = Path(sys.argv[2])
status_path = Path(sys.argv[3])
runner = sys.argv[4]
log_rel = sys.argv[5]
cmd = sys.argv[6:]

log_path.parent.mkdir(parents=True, exist_ok=True)
try:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout_part, stderr_part = proc.communicate(timeout=timeout_sec)
        out = (stdout_part or "") + ("\n" + stderr_part if stderr_part else "")
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError as exc:
            sys.stderr.write(f"{exc}\n")
        stdout_part, stderr_part = proc.communicate()
        out = (
            (stdout_part or "")
            + "\n"
            + (stderr_part or "")
            + f"\n[TIMEOUT] Subagent {runner} exceeded {timeout_sec}s limit.\n"
        )
        rc = 124
except FileNotFoundError:
    out = f"[ERROR] Runner binary not found on PATH: {cmd[0]}\n"
    rc = 127

if out.strip():
    sys.stdout.write(out if out.endswith("\n") else out + "\n")
log_path.write_text(out, encoding="utf-8")
lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
tail = lines[-1][:72] if lines else f"exit={rc}"
status_path.write_text(
    json.dumps({"runner": runner, "exit_code": rc, "log_file": log_rel, "tail": tail}, ensure_ascii=False),
    encoding="utf-8",
)
sys.exit(rc)
PY
}

PROMPT="Read $BRIEF_FILE carefully. Follow all required_principles and execute the Deliverable Contract. Run verify_cmd before finishing."

echo ">>> [pstack handoff] Spawning FRESH stateless subagent ($RUNNER, timeout=${SPAWN_TIMEOUT}s) with brief: $BRIEF_FILE"

if [[ -n "${PSTACK_SPAWN_TEST_CMD:-}" ]]; then
  run_with_timeout_and_log bash -c "$PSTACK_SPAWN_TEST_CMD"
  exit 0
fi

case "$RUNNER" in
  opencode)
    run_with_timeout_and_log opencode run "$PROMPT"
    ;;
  codex)
    read -r -a CODEX_ARGS <<< "$PSTACK_CODEX_FLAGS"
    run_with_timeout_and_log codex exec "${CODEX_ARGS[@]}" "$PROMPT"
    ;;
  codex-review)
    run_with_timeout_and_log codex review "$PROMPT"
    ;;
  claude)
    run_with_timeout_and_log claude -p "$PROMPT"
    ;;
  antigravity|agy)
    run_with_timeout_and_log agy -p "$PROMPT" --mode accept-edits
    ;;
  pi)
    if command -v pi >/dev/null 2>&1; then
      run_with_timeout_and_log pi -p "$PROMPT"
    else
      python3 "$SCRIPT_DIR/pstack-verify.py" prep-verifier | tee "$LOG_FILE"
      echo "[Desktop Handoff: Pi] Open a new tab in Pi and run: /pstack-build or /pstack-verify"
    fi
    ;;
  workbuddy)
    WB_CARD="$WORKSPACE_ROOT/.agents/handoffs/workbuddy-prompt.txt"
    {
      echo "=== PSTACK WORKBUDDY DESKTOP DISPATCH CARD ==="
      echo "TASK_ID    : $TASK_ID"
      echo "BRIEF_FILE : $BRIEF_FILE"
      echo "PROMPT     : $PROMPT"
      echo "TAB_1_CMD  : /pstack-build"
      echo "TAB_2_CMD  : /pstack-verify"
      echo "----------------------------------------------"
      python3 "$SCRIPT_DIR/pstack-verify.py" prep-verifier
    } | tee "$WB_CARD" "$LOG_FILE"
    echo "[Desktop Handoff: WorkBuddy] Dispatch card saved -> $WB_CARD"
    echo "[Desktop Handoff: WorkBuddy] Open a new tab in WorkBuddy and run: /pstack-build or /pstack-verify"
    ;;
  dry-run)
    {
      echo "[DRY-RUN] Verified brief successfully. Ready to dispatch prompt:"
      echo "  Runner  : $RUNNER"
      echo "  Task ID : $TASK_ID"
      echo "  Timeout : ${SPAWN_TIMEOUT}s"
      echo "  Log     : $LOG_REL"
      echo "  Prompt  : $PROMPT"
    } | tee "$LOG_FILE"
    ;;
  *)
    echo "[Error] Unknown runner: $RUNNER (supported: opencode | codex | codex-review | workbuddy | pi | claude | agy | dry-run)"
    exit 1
    ;;
esac
