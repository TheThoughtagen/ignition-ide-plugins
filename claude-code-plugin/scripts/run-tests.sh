#!/usr/bin/env bash
# run-tests.sh — Post-commit gateway test hook
# Triggers gateway scan, runs Jython tests, reports results.
# Self-gates: silently exits if not in an Ignition project or test infra missing.

set -euo pipefail

INPUT=$(cat)

# Only trigger on git commit
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
if [[ ! "$COMMAND" =~ git\ commit($|\ ) ]]; then
  exit 0
fi

# Check commit succeeded
STDOUT=$(echo "$INPUT" | jq -r '.tool_result.stdout // empty')
if [[ ! "$STDOUT" =~ create\ mode|file\ changed|files\ changed|insertions|deletions ]] && [[ ! "$STDOUT" =~ \[[a-z]+\ [a-f0-9] ]]; then
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

PROJECT_ROOT=$(find_project_root "$PWD") || exit 0
PROJECT_NAME=$(basename "$PROJECT_ROOT")

# Check test infrastructure exists
if [ ! -d "$PROJECT_ROOT/com.inductiveautomation.webdev/resources/testing/run" ]; then
  exit 0
fi

# Gateway URL
GATEWAY_URL="${IGNITION_GATEWAY_URL:-}"
if [ -z "$GATEWAY_URL" ] && [ -f "$PROJECT_ROOT/e2e/.env" ]; then
  GATEWAY_URL=$(grep -E '^IGNITION_URL=' "$PROJECT_ROOT/e2e/.env" 2>/dev/null | cut -d= -f2- || true)
fi
GATEWAY_URL="${GATEWAY_URL:-https://localhost:9043}"

# Check gateway reachable
if ! curl -k -s --connect-timeout 3 "$GATEWAY_URL/StatusPing" > /dev/null 2>&1; then
  exit 0
fi

# Trigger project scan (optional — requires API token)
TOKEN_FILE="${IGNITION_API_TOKEN_FILE:-}"
if [ -n "$TOKEN_FILE" ] && [ -f "$TOKEN_FILE" ]; then
  TOKEN=$(cat "$TOKEN_FILE")
  curl -k -s -X POST -H "X-Ignition-API-Token: $TOKEN" \
    "$GATEWAY_URL/data/project-scan-endpoint/scan?updateDesigners=true" > /dev/null 2>&1 || true
fi

# Wait for scan propagation (best-effort delay — Ignition has no scan-completion endpoint)
sleep 3

# Run tests
ENDPOINT="$GATEWAY_URL/system/webdev/$PROJECT_NAME/testing/run"
RESULT=$(curl -k -s -X POST "$ENDPOINT" 2>/dev/null) || exit 0

# Parse results
PASSED=$(echo "$RESULT" | jq -r '.passed // 0')
FAILED=$(echo "$RESULT" | jq -r '.failed // 0')
ERRORS=$(echo "$RESULT" | jq -r '.errors // 0')
SKIPPED=$(echo "$RESULT" | jq -r '.skipped // 0')
TOTAL=$(echo "$RESULT" | jq -r '.total // 0')
DURATION=$(echo "$RESULT" | jq -r '.duration_ms // 0')

if [ "$FAILED" -eq 0 ] && [ "$ERRORS" -eq 0 ]; then
  echo "Tests: $PASSED passed, $SKIPPED skipped ($TOTAL total, ${DURATION}ms)" >&2
else
  echo "TESTS FAILED: $PASSED passed, $FAILED failed, $ERRORS errors ($TOTAL total, ${DURATION}ms)" >&2
  echo "$RESULT" | jq -r '
    .modules[]?.results[]? |
    select(.status == "failed" or .status == "error") |
    "  \(.status | ascii_upcase): \(.name) — \(.message)"
  ' 2>/dev/null >&2 || true
fi

exit 0
