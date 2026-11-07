#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(python3 -c 'import os,sys; print(os.path.dirname(os.path.realpath(sys.argv[1])))' "${BASH_SOURCE[0]}")"
WORKSPACE_ROOT="$(python3 "$SCRIPT_DIR/pstack_resolver.py" --workspace-root)"

SPAWN_TIMEOUT="${PSTACK_SPAWN_TIMEOUT:-600}"
PSTACK_CODEX_FLAGS="${PSTACK_CODEX_FLAGS:---full-auto}"
ARG1=""
ARG2=""

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
    python3 - "$STATUS_FILE" "$RUNNER" "$rc" "$LOG_REL" "$LOG_FILE" <<'PY'
import json, sys
from pathlib import Path
status_path, runner, rc, log_rel, log_file = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], Path(sys.argv[5])
lines = [ln.strip() for ln in log_file.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()] if log_file.exists() else []
tail = lines[-1][:72] if lines else f"exit={rc}"
Path(status_path).write_text(json.dumps({"runner": runner, "exit_code": rc, "log_file": log_rel, "tail": tail}, ensure_ascii=False), encoding="utf-8")
PY
    python3 "$SCRIPT_DIR/pstack-session.py" pause "CRASH_RECOVERY: runner=$RUNNER exit=$rc log=$LOG_REL" || true
  fi
}
trap on_spawn_exit EXIT

run_with_timeout_and_log() {
  SPAWN_ACTIVE=1
  python3 - "$SPAWN_TIMEOUT" "$LOG_FILE" "$STATUS_FILE" "$RUNNER" "$LOG_REL" "$@" <<'PY'
import json, subprocess, sys
from pathlib import Path

timeout_sec = float(sys.argv[1])
log_path = Path(sys.argv[2])
status_path = Path(sys.argv[3])
runner = sys.argv[4]
log_rel = sys.argv[5]
cmd = sys.argv[6:]

log_path.parent.mkdir(parents=True, exist_ok=True)
try:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, check=False)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    rc = proc.returncode
except subprocess.TimeoutExpired as exc:
    stdout_part = exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
    stderr_part = exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    out = stdout_part + "\n" + stderr_part + f"\n[TIMEOUT] Subagent {runner} exceeded {timeout_sec}s limit.\n"
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
