# Evidence Pack: Multi-Agent Universal Adaptation & GitHub Deployment

## 1. Local Agent Global Directories Discovered (`[实测 Measured]`)
- **Antigravity (`agy`)**: `~/.gemini/config/skills/`
- **Claude Code (`claude`)**: `~/.claude/skills/` (reads `CLAUDE.md` in project root)
- **Codex CLI (`codex`)**: `~/.codex/skills/` (reads `AGENTS.md` in project root)
- **OpenCode (`opencode`)**: `~/.config/opencode/skills/` and `~/.config/opencode/command/*.md` (reads `AGENTS.md` in project root)
- **Cursor (`cursor`)**: `~/.cursor/skills-cursor/` (reads `.cursor/rules/*.mdc` and `AGENTS.md` in project root)

## 2. GitHub Authentication Status (`[实测 Measured]`)
- Logged into `github.com` via `gh` CLI as `azen07508-debug` with `repo`, `workflow`, `gist` scopes.

## Runtime Verification Digest
- **Command**: `python3 -m unittest discover -s tests -q && python3 scripts/verify-handoff.py && python3 scripts/verify-code-slop.py scripts` (`[实测 Measured]` at `2026-11-07T16:16:26+08:00`)
- **Exit Code & Digest**: `exit=0` | `sha256=308c2ffffd78`
- **Git Diff Summary**: `10 files changed, 263 insertions(+), 71 deletions(-)`
- **Output Tail**:
```text
  ====================================================================
  STATUS : ALL CHECKS GREEN (0 redundant comments, swallowed exceptions, or custom rule hi
  ====================================================================
  ----------------------------------------------------------------------
  Ran 8 tests in 4.210s
  OK
```
