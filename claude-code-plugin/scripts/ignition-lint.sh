#!/usr/bin/env bash
# ignition-lint.sh — PostToolUse hook for Ignition projects
# Only runs when the edited file is inside an Ignition project (has project.json).

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Bail if no file path or file doesn't exist
if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

PROJECT_ROOT=$(find_project_root "$(dirname "$FILE_PATH")") || exit 0

# Only proceed if ignition-lint is installed
if ! command -v ignition-lint &>/dev/null; then
  exit 0
fi

BASENAME=$(basename "$FILE_PATH")
EXT="${FILE_PATH##*.}"
OUTPUT=""

case "$EXT" in
  py)
    OUTPUT=$(ignition-lint --target "$FILE_PATH" --profile scripts-only 2>&1) || true
    ;;
  json)
    case "$BASENAME" in
      view.json)
        OUTPUT=$(ignition-lint --target "$FILE_PATH" --profile perspective-only 2>&1) || true
        ;;
      tags.json)
        OUTPUT=$(ignition-lint --target "$FILE_PATH" --profile full 2>&1) || true
        ;;
    esac
    ;;
esac

if [ -n "$OUTPUT" ]; then
  jq -n \
    --arg reason "ignition-lint found issues in $BASENAME" \
    --arg context "$OUTPUT" \
    '{
      decision: "block",
      reason: $reason,
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        additionalContext: $context
      }
    }'
fi

exit 0
