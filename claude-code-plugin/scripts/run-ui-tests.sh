#!/usr/bin/env bash
# run-ui-tests.sh — Post-edit Playwright hook for Perspective view changes.
# Self-gates: silently exits if not editing a view.json or e2e not set up.

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only trigger on view.json edits
case "$FILE_PATH" in
  */view.json) ;;
  *) exit 0 ;;
esac

# Must be a Perspective view
if [[ "$FILE_PATH" != *"com.inductiveautomation.perspective/views/"* ]]; then
  exit 0
fi

# Find project root
find_project_root() {
  local dir="$1"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/project.json" ]; then echo "$dir"; return 0; fi
    dir=$(dirname "$dir")
  done
  return 1
}

PROJECT_ROOT=$(find_project_root "$(dirname "$FILE_PATH")") || exit 0
E2E_DIR="$PROJECT_ROOT/e2e"

# Silent exit if e2e not set up
[ -d "$E2E_DIR/node_modules" ] || exit 0
[ -f "$E2E_DIR/.auth/user.json" ] || exit 0

# Concurrency guard (portable mkdir lock)
LOCK_DIR="$E2E_DIR/.playwright-running.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

# Extract view area for scoped testing
VIEW_AREA=$(echo "$FILE_PATH" | sed -n 's|.*views/\([^/]*\)/.*|\1|p')
VIEW_AREA_LOWER=$(echo "$VIEW_AREA" | tr '[:upper:]' '[:lower:]')

TEST_DIR="$E2E_DIR/tests/$VIEW_AREA_LOWER"

cd "$E2E_DIR"
if [ -d "$TEST_DIR" ]; then
  npx playwright test "$TEST_DIR" --reporter=list 2>&1 | tail -5 >&2 || true
else
  npx playwright test tests/smoke/ --reporter=list 2>&1 | tail -5 >&2 || true
fi

exit 0
