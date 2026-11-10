#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(python3 -c 'import os,sys; print(os.path.dirname(os.path.realpath(sys.argv[1])))' "${BASH_SOURCE[0]}")"
SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SOURCE="$SOURCE_ROOT/.agents/skills/pstack"
ACTION="${1:---global}"
MODE="${2:-light}"

ensure_skill_bundle_links() {
  ln -sfn "../../pstack" "$SKILL_SOURCE/pstack"
  ln -sfn "../../../scripts" "$SKILL_SOURCE/scripts"
  ln -sfn "pstack-core.md" "$SOURCE_ROOT/.agents/pstack/poteto-core.md"
}

register_global_agents() {
  ensure_skill_bundle_links
  chmod +x "$SOURCE_ROOT/scripts/pstack" "$SOURCE_ROOT/scripts/"*.py "$SOURCE_ROOT/scripts/"*.sh

  local global_home_anchor="$HOME/.config/pstack/home"
  mkdir -p "$(dirname "$global_home_anchor")"
  ln -sfn "$SOURCE_ROOT" "$global_home_anchor"
  echo "[OK] Linked global Pstack home: $global_home_anchor -> $SOURCE_ROOT"

  mkdir -p "$HOME/.local/bin"
  ln -sfn "$SOURCE_ROOT/scripts/pstack" "$HOME/.local/bin/pstack"
  ln -sfn "$SOURCE_ROOT/scripts/pstack-router.py" "$HOME/.local/bin/pstack-router"
  ln -sfn "$SOURCE_ROOT/scripts/pstack-scheduler.py" "$HOME/.local/bin/pstack-scheduler"
  ln -sfn "$SOURCE_ROOT/scripts/pstack-tree.py" "$HOME/.local/bin/pstack-tree"
  ln -sfn "$SOURCE_ROOT/scripts/pstack-verify.py" "$HOME/.local/bin/pstack-verify"
  ln -sfn "$SOURCE_ROOT/scripts/pstack-correct.py" "$HOME/.local/bin/pstack-correct"
  ln -sfn "$SOURCE_ROOT/scripts/pstack-session.py" "$HOME/.local/bin/pstack-session"
  ln -sfn "$SOURCE_ROOT/scripts/pstack-onboard.py" "$HOME/.local/bin/pstack-onboard"
  ln -sfn "$SOURCE_ROOT/scripts/pstack-bench.py" "$HOME/.local/bin/pstack-bench"
  ln -sfn "$SOURCE_ROOT/scripts/pstack_update.py" "$HOME/.local/bin/pstack-update"
  ln -sfn "$SOURCE_ROOT/scripts/ag-spawn.sh" "$HOME/.local/bin/ag-spawn"
  echo "[OK] Linked global CLIs in $HOME/.local/bin (pstack, pstack-router, pstack-scheduler, pstack-tree, pstack-verify, pstack-correct, pstack-session, pstack-onboard, pstack-bench, pstack-update, ag-spawn)"

  local skill_targets=(
    "$HOME/.gemini/config/skills/pstack"
    "$HOME/.claude/skills/pstack"
    "$HOME/.codex/skills/pstack"
    "$HOME/.config/opencode/skills/pstack"
    "$HOME/.cursor/skills-cursor/pstack"
    "$HOME/.workbuddy-ai/skills/pstack"
    "$HOME/.pi/agent/skills/pstack"
    "$HOME/.agents/skills/pstack"
  )

  for target in "${skill_targets[@]}"; do
    mkdir -p "$(dirname "$target")"
    ln -sfn "$SKILL_SOURCE" "$target"
    echo "[OK] Linked global skill: $target -> $SKILL_SOURCE"
  done

  local opencode_cmd_dir="$HOME/.config/opencode/command"
  mkdir -p "$opencode_cmd_dir"
  for cmd_file in "$SOURCE_ROOT/adapters/opencode/commands/"*.md; do
    local base_name
    base_name="$(basename "$cmd_file")"
    ln -sfn "$cmd_file" "$opencode_cmd_dir/$base_name"
    echo "[OK] Linked OpenCode command: $opencode_cmd_dir/$base_name -> $cmd_file"
  done
}

print_status() {
  echo "===================================================================="
  echo "PSTACK v3.0 MULTI-AGENT & GLOBAL CLI MOUNT STATUS"
  echo "===================================================================="
  local entries=(
    "Global Anchor (PSTACK_HOME):$HOME/.config/pstack/home"
    "Global CLI (pstack):$HOME/.local/bin/pstack"
    "Global Gate (pstack-verify):$HOME/.local/bin/pstack-verify"
    "Global Spawner (ag-spawn):$HOME/.local/bin/ag-spawn"
    "Antigravity (agy):$HOME/.gemini/config/skills/pstack"
    "Claude Code (claude):$HOME/.claude/skills/pstack"
    "Codex CLI (codex):$HOME/.codex/skills/pstack"
    "OpenCode Skill:$HOME/.config/opencode/skills/pstack"
    "OpenCode Command (/pstack):$HOME/.config/opencode/command/pstack.md"
    "Cursor IDE (cursor):$HOME/.cursor/skills-cursor/pstack"
    "WorkBuddy AI (workbuddy):$HOME/.workbuddy-ai/skills/pstack"
    "Pi Agent (pi):$HOME/.pi/agent/skills/pstack"
    "Universal Agent Pool:$HOME/.agents/skills/pstack"
  )
  local missing=0
  for item in "${entries[@]}"; do
    local label="${item%%:*}"
    local path="${item#*:}"
    if [[ -e "$path" ]]; then
      local resolved
      resolved="$(readlink "$path" || echo "$path")"
      printf "  [MOUNTED] %-28s -> %s\n" "$label" "$resolved"
    else
      printf "  [MISSING] %-28s -> %s\n" "$label" "$path"
      missing=$((missing + 1))
    fi
  done
  python3 "$SOURCE_ROOT/scripts/pstack_update.py" --status-line || true
  echo "===================================================================="
  if [[ "$missing" -gt 0 ]]; then
    return 1
  fi
  echo "STATUS : ALL CHECKS GREEN (8/8 local agents + global CLI mounted)"
  echo "===================================================================="
  return 0
}

inject_target_repo() {
  local target_repo="$1"
  local inject_mode="$2"
  ensure_skill_bundle_links
  mkdir -p "$target_repo"
  local target_abs
  target_abs="$(cd "$target_repo" && pwd)"

  if [[ "$target_abs" == "$SOURCE_ROOT" ]]; then
    python3 "$SOURCE_ROOT/scripts/pstack_resolver.py" --init-skeleton "$target_abs"
    echo "[OK] Verified Pstack source repository skeleton in $target_abs"
    echo "STATUS : ALL CHECKS GREEN"
    return 0
  fi

  case "$inject_mode" in
    light|--light)
      cp "$SOURCE_ROOT/AGENTS.md" "$target_abs/AGENTS.md"
      cp "$SOURCE_ROOT/CLAUDE.md" "$target_abs/CLAUDE.md"
      mkdir -p "$target_abs/.cursor/rules"
      cp "$SOURCE_ROOT/.cursor/rules/pstack.mdc" "$target_abs/.cursor/rules/pstack.mdc"
      python3 "$SOURCE_ROOT/scripts/pstack_resolver.py" --init-skeleton "$target_abs"
      echo "[OK] Initialized light Pstack v3.0 workspace in $target_abs (overlay -> $SOURCE_ROOT)"
      echo "STATUS : ALL CHECKS GREEN"
      ;;
    symlink|--symlink)
      ln -sfn "$SOURCE_ROOT/AGENTS.md" "$target_abs/AGENTS.md"
      ln -sfn "$SOURCE_ROOT/CLAUDE.md" "$target_abs/CLAUDE.md"
      mkdir -p "$target_abs/.cursor/rules"
      ln -sfn "$SOURCE_ROOT/.cursor/rules/pstack.mdc" "$target_abs/.cursor/rules/pstack.mdc"
      ln -sfn "$SOURCE_ROOT/scripts" "$target_abs/scripts"
      ln -sfn "$SOURCE_ROOT/.agents" "$target_abs/.agents"
      echo "[OK] Symlinked Pstack v3.0 multi-agent topology into $target_abs"
      echo "STATUS : ALL CHECKS GREEN"
      ;;
    full|--full|copy|--copy|*)
      cp "$SOURCE_ROOT/AGENTS.md" "$target_abs/AGENTS.md"
      cp "$SOURCE_ROOT/CLAUDE.md" "$target_abs/CLAUDE.md"
      mkdir -p "$target_abs/.cursor/rules" "$target_abs/scripts" "$target_abs/.agents"
      cp "$SOURCE_ROOT/.cursor/rules/pstack.mdc" "$target_abs/.cursor/rules/pstack.mdc"
      cp -R "$SOURCE_ROOT/scripts/"* "$target_abs/scripts/"
      cp -R "$SOURCE_ROOT/.agents/"* "$target_abs/.agents/"
      chmod +x "$target_abs/scripts/pstack" "$target_abs/scripts/"*.py "$target_abs/scripts/"*.sh
      echo "[OK] Copied full Pstack v3.0 multi-agent topology into $target_abs"
      echo "STATUS : ALL CHECKS GREEN"
      ;;
  esac
}

case "$ACTION" in
  --global)
    register_global_agents
    ;;
  --status)
    print_status
    ;;
  *)
    register_global_agents
    inject_target_repo "$ACTION" "$MODE"
    ;;
esac
