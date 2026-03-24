#!/usr/bin/env bash
# run-ui-tests.sh — Post-edit Playwright hook for Perspective view changes.
# Self-gates: silently exits if not editing a view.json or e2e not set up.

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only trigger on Perspective view.json edits
case "$FILE_PATH" in
  *com.inductiveautomation.perspective/views/*/view.json) ;;
  *) exit 0 ;;
esac

PROJECT_ROOT=$(find_project_root "$(dirname "$FILE_PATH")") || exit 0
E2E_DIR="$PROJECT_ROOT/e2e"

# Silent exit if e2e not set up
[ -d "$E2E_DIR/node_modules" ] || exit 0
[ -f "$E2E_DIR/.auth/user.json" ] || exit 0

# Concurrency guard (portable mkdir lock with stale detection)
LOCK_DIR="$E2E_DIR/.playwright-running.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  # Check for stale lock (older than 10 minutes)
  if [ -d "$LOCK_DIR" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
    if [ "$LOCK_AGE" -gt 600 ]; then
      echo "Removing stale Playwright lock (${LOCK_AGE}s old)" >&2
      rm -rf "$LOCK_DIR"
      mkdir "$LOCK_DIR" 2>/dev/null || exit 0
    else
      echo "Playwright tests already running — skipping" >&2
      exit 0
    fi
  else
    exit 0
  fi
fi
trap 'rm -rf "$LOCK_DIR" 2>/dev/null || true' EXIT

# Extract view area for scoped testing
VIEW_AREA=$(echo "$FILE_PATH" | sed -n 's|.*views/\([^/]*\)/.*|\1|p')
VIEW_AREA_LOWER=$(echo "$VIEW_AREA" | tr '[:upper:]' '[:lower:]')

cd "$E2E_DIR"
if [ -n "$VIEW_AREA_LOWER" ] && [ -d "$E2E_DIR/tests/$VIEW_AREA_LOWER" ]; then
  npx playwright test "tests/$VIEW_AREA_LOWER" --reporter=list 2>&1 | tail -20 >&2
  TEST_EXIT=${PIPESTATUS[0]}
else
  npx playwright test tests/smoke/ --reporter=list 2>&1 | tail -20 >&2
  TEST_EXIT=${PIPESTATUS[0]}
fi

if [ "$TEST_EXIT" -ne 0 ]; then
  echo "Playwright tests failed for view: ${VIEW_AREA:-unknown}" >&2
  exit 1
fi
