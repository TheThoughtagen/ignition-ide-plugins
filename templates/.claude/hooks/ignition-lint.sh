#!/usr/bin/env bash
# ignition-lint.sh — Claude Code PostToolUse hook
# Runs ignition-lint on .py and .json files after Write/Edit operations.
# Feeds diagnostics back so Claude can fix issues immediately.

set -euo pipefail

# Read hook input from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

BASENAME=$(basename "$FILE_PATH")
EXT="${FILE_PATH##*.}"

# Skip files outside the Ignition project
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  case "$FILE_PATH" in
    "$CLAUDE_PROJECT_DIR"/*) ;;
    *) exit 0 ;;
  esac
fi

# Check if ignition-lint is available
if ! command -v ignition-lint &>/dev/null; then
  exit 0
fi

run_lint() {
  local target="$1"
  local profile="$2"
  local output

  output=$(ignition-lint --target "$target" --profile "$profile" 2>&1) || true

  if [ -n "$output" ]; then
    # Feed issues back to Claude as structured JSON
    jq -n \
      --arg reason "ignition-lint found issues in $BASENAME" \
      --arg context "$output" \
      '{
        decision: "block",
        reason: $reason,
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext: $context
        }
      }'
  fi
}

case "$EXT" in
  py)
    run_lint "$FILE_PATH" "scripts-only"
    ;;
  json)
    case "$BASENAME" in
      view.json)
        run_lint "$FILE_PATH" "perspective-only"
        ;;
      tags.json)
        run_lint "$FILE_PATH" "full"
        ;;
    esac
    ;;
esac

exit 0
