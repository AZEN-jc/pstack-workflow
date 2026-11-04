#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BRIEF_FILE="${1:-$WORKSPACE_ROOT/.agents/handoffs/active-brief.md}"
RUNNER="${2:-opencode}"

if [[ ! -f "$BRIEF_FILE" ]]; then
  echo "[Error] Handoff brief not found: $BRIEF_FILE"
  exit 1
fi

echo ">>> [pstack gate] Validating handoff brief & ledger before spawning subagent..."
python3 "$SCRIPT_DIR/verify-handoff.py" "$BRIEF_FILE"

PROMPT="Read $BRIEF_FILE carefully. Follow all required_principles and execute the Deliverable Contract. Run verify_cmd before finishing."

echo ">>> [pstack handoff] Spawning FRESH stateless subagent ($RUNNER) with brief: $BRIEF_FILE"

case "$RUNNER" in
  opencode)
    opencode run "$PROMPT"
    ;;
  codex)
    codex exec "$PROMPT"
    ;;
  codex-review)
    codex review "$PROMPT"
    ;;
  claude)
    claude -p "$PROMPT"
    ;;
  antigravity|agy)
    agy -p "$PROMPT" --mode accept-edits
    ;;
  dry-run)
    echo "[DRY-RUN] Verified brief successfully. Ready to dispatch prompt:"
    echo "  Runner : $RUNNER"
    echo "  Prompt : $PROMPT"
    ;;
  *)
    echo "[Error] Unknown runner: $RUNNER (supported: opencode | codex | codex-review | claude | agy | dry-run)"
    exit 1
    ;;
esac
