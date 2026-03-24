#!/usr/bin/env bash
# run-tests.sh — Post-commit gateway test hook
# Triggers gateway scan, runs Jython tests, reports results.
# Self-gates: silently exits if not in an Ignition project or test infra missing.

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

INPUT=$(cat)

# Only trigger on git commit
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
if [[ ! "$COMMAND" =~ git\ commit($|\ ) ]]; then
  exit 0
fi

# Check commit succeeded (exit code 0 = success)
EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_result.exit_code // 1')
if [ "$EXIT_CODE" -ne 0 ]; then
  exit 0
fi

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
  echo "Ignition gateway not reachable at $GATEWAY_URL — skipping post-commit tests" >&2
  exit 0
fi

# Trigger project scan (optional — requires API token)
TOKEN_FILE="${IGNITION_API_TOKEN_FILE:-}"
if [ -n "$TOKEN_FILE" ] && [ -f "$TOKEN_FILE" ]; then
  TOKEN=$(cat "$TOKEN_FILE")
  if ! curl -k -s --max-time 10 -X POST -H "X-Ignition-API-Token: $TOKEN" \
    "$GATEWAY_URL/data/project-scan-endpoint/scan?updateDesigners=true" > /dev/null 2>&1; then
    echo "Warning: project scan request failed — tests may run against stale state" >&2
  fi
fi

# Wait for scan propagation (best-effort delay — Ignition has no scan-completion endpoint)
sleep 3

# Run tests
ENDPOINT="$GATEWAY_URL/system/webdev/$PROJECT_NAME/testing/run"
RESULT=$(curl -k -s --fail --max-time 60 -X POST "$ENDPOINT" 2>/dev/null) || {
  echo "Test endpoint unreachable or returned error: $ENDPOINT" >&2
  exit 1
}

# Validate response structure
if ! echo "$RESULT" | jq -e '.total' > /dev/null 2>&1; then
  echo "Unexpected response from test endpoint:" >&2
  echo "$RESULT" | head -5 >&2
  exit 1
fi

# Parse results (single jq call)
read -r PASSED FAILED ERRORS SKIPPED TOTAL DURATION < <(
  echo "$RESULT" | jq -r '[.passed // 0, .failed // 0, .errors // 0, .skipped // 0, .total // 0, .duration_ms // 0] | @tsv'
)

if [ "$FAILED" -eq 0 ] && [ "$ERRORS" -eq 0 ]; then
  echo "Tests: $PASSED passed, $SKIPPED skipped ($TOTAL total, ${DURATION}ms)" >&2
  exit 0
else
  echo "TESTS FAILED: $PASSED passed, $FAILED failed, $ERRORS errors ($TOTAL total, ${DURATION}ms)" >&2
  echo "$RESULT" | jq -r '
    .modules[]?.results[]? |
    select(.status == "failed" or .status == "error") |
    "  \(.status | ascii_upcase): \(.name) — \(.message)"
  ' 2>/dev/null >&2 || true
  exit 1
fi
