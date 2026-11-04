#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SOURCE="$SOURCE_ROOT/.agents/skills/pstack"
ACTION="${1:---global}"
MODE="${2:-copy}"

ensure_skill_bundle_links() {
  ln -sfn "../../pstack" "$SKILL_SOURCE/pstack"
  ln -sfn "../../../scripts" "$SKILL_SOURCE/scripts"
}

register_global_agents() {
  ensure_skill_bundle_links

  local skill_targets=(
    "$HOME/.gemini/config/skills/pstack"
    "$HOME/.claude/skills/pstack"
    "$HOME/.codex/skills/pstack"
    "$HOME/.config/opencode/skills/pstack"
    "$HOME/.cursor/skills-cursor/pstack"
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
  echo "PSTACK MULTI-AGENT GLOBAL MOUNT STATUS"
  echo "===================================================================="
  local entries=(
    "Antigravity (agy):$HOME/.gemini/config/skills/pstack"
    "Claude Code (claude):$HOME/.claude/skills/pstack"
    "Codex CLI (codex):$HOME/.codex/skills/pstack"
    "OpenCode Skill:$HOME/.config/opencode/skills/pstack"
    "OpenCode Command (/pstack):$HOME/.config/opencode/command/pstack.md"
    "Cursor IDE (cursor):$HOME/.cursor/skills-cursor/pstack"
  )
  local missing=0
  for item in "${entries[@]}"; do
    local label="${item%%:*}"
    local path="${item#*:}"
    if [[ -e "$path" ]]; then
      local resolved
      resolved="$(readlink "$path" || echo "$path")"
      printf "  [MOUNTED] %-26s -> %s\n" "$label" "$resolved"
    else
      printf "  [MISSING] %-26s -> %s\n" "$label" "$path"
      missing=$((missing + 1))
    fi
  done
  echo "===================================================================="
  if [[ "$missing" -gt 0 ]]; then
    return 1
  fi
  echo "STATUS : ALL CHECKS GREEN (5/5 local agents mounted)"
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

  if [[ "$inject_mode" == "symlink" ]]; then
    ln -sfn "$SOURCE_ROOT/AGENTS.md" "$target_abs/AGENTS.md"
    ln -sfn "$SOURCE_ROOT/CLAUDE.md" "$target_abs/CLAUDE.md"
    mkdir -p "$target_abs/.cursor/rules"
    ln -sfn "$SOURCE_ROOT/.cursor/rules/pstack.mdc" "$target_abs/.cursor/rules/pstack.mdc"
    ln -sfn "$SOURCE_ROOT/scripts" "$target_abs/scripts"
    ln -sfn "$SOURCE_ROOT/.agents" "$target_abs/.agents"
    echo "[OK] Symlinked Pstack multi-agent topology into $target_abs"
  else
    cp "$SOURCE_ROOT/AGENTS.md" "$target_abs/AGENTS.md"
    cp "$SOURCE_ROOT/CLAUDE.md" "$target_abs/CLAUDE.md"
    mkdir -p "$target_abs/.cursor/rules" "$target_abs/scripts" "$target_abs/.agents"
    cp "$SOURCE_ROOT/.cursor/rules/pstack.mdc" "$target_abs/.cursor/rules/pstack.mdc"
    cp -R "$SOURCE_ROOT/scripts/"* "$target_abs/scripts/"
    cp -R "$SOURCE_ROOT/.agents/"* "$target_abs/.agents/"
    chmod +x "$target_abs/scripts/"*.py "$target_abs/scripts/"*.sh
    echo "[OK] Copied full Pstack multi-agent topology into $target_abs"
  fi
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
