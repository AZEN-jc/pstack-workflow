#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(python3 -c 'import os,sys; print(os.path.dirname(os.path.realpath(sys.argv[1])))' "${BASH_SOURCE[0]}")"
WORKSPACE_ROOT="$(python3 "$SCRIPT_DIR/pstack_resolver.py" --workspace-root)"

ARG1="${1:-}"
ARG2="${2:-}"

case "$ARG1" in
  opencode|codex|codex-review|claude|antigravity|agy|dry-run)
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
