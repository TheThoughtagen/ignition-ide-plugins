#!/usr/bin/env bash
# detect-project.sh — Auto-detect Ignition project structure and gateway state.
# Usage: detect-project.sh [project-directory]
# Outputs JSON with project metadata, gateway status, and existing test infrastructure.

set -euo pipefail

TARGET="${1:-$PWD}"

# Walk up to find project.json
find_project_root() {
  local dir="$1"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/project.json" ]; then
      echo "$dir"
      return 0
    fi
    dir=$(dirname "$dir")
  done
  return 1
}

PROJECT_ROOT=$(find_project_root "$TARGET") || {
  echo '{"error": "No project.json found walking up from '"$TARGET"'"}' >&2
  exit 1
}

PROJECT_NAME=$(basename "$PROJECT_ROOT")
PROJECT_TITLE=$(jq -r '.title // ""' "$PROJECT_ROOT/project.json" 2>/dev/null || echo "")

# Probe gateway
GATEWAY_URL=""
GATEWAY_REACHABLE=false

for url in "https://localhost:9043" "http://localhost:8088"; do
  if curl -k -s --connect-timeout 3 "$url/StatusPing" > /dev/null 2>&1; then
    GATEWAY_URL="$url"
    GATEWAY_REACHABLE=true
    break
  fi
done

GATEWAY_URL="${GATEWAY_URL:-https://localhost:9043}"

# Detect tag providers
TAG_PROVIDERS="[]"
if [ "$GATEWAY_REACHABLE" = true ]; then
  TAG_PROVIDERS=$(curl -k -s --connect-timeout 3 "$GATEWAY_URL/system/tag-providers" 2>/dev/null || echo "[]")
  # Validate it's JSON array
  if ! echo "$TAG_PROVIDERS" | jq -e 'type == "array"' > /dev/null 2>&1; then
    TAG_PROVIDERS="[]"
  fi
fi

# Check for modules
HAS_PERSPECTIVE=false
HAS_WEBDEV=false
HAS_SCRIPTING=false
[ -d "$PROJECT_ROOT/com.inductiveautomation.perspective" ] && HAS_PERSPECTIVE=true
[ -d "$PROJECT_ROOT/com.inductiveautomation.webdev" ] && HAS_WEBDEV=true
[ -d "$PROJECT_ROOT/ignition/script-python" ] && HAS_SCRIPTING=true

# Check existing test infrastructure
HAS_JYTHON_FRAMEWORK=false
HAS_WEBDEV_ENDPOINTS=false
HAS_E2E=false
HAS_STUBS=false
[ -d "$PROJECT_ROOT/ignition/script-python/testing/runner" ] && HAS_JYTHON_FRAMEWORK=true
[ -d "$PROJECT_ROOT/com.inductiveautomation.webdev/resources/testing/run" ] && HAS_WEBDEV_ENDPOINTS=true
[ -f "$PROJECT_ROOT/e2e/package.json" ] && HAS_E2E=true
[ -d "$PROJECT_ROOT/.ignition-stubs/testing" ] && HAS_STUBS=true

jq -n \
  --arg project_root "$PROJECT_ROOT" \
  --arg project_title "$PROJECT_TITLE" \
  --arg project_name "$PROJECT_NAME" \
  --arg gateway_url "$GATEWAY_URL" \
  --argjson gateway_reachable "$GATEWAY_REACHABLE" \
  --argjson has_perspective "$HAS_PERSPECTIVE" \
  --argjson has_webdev "$HAS_WEBDEV" \
  --argjson has_scripting "$HAS_SCRIPTING" \
  --argjson tag_providers "$TAG_PROVIDERS" \
  --argjson jython_framework "$HAS_JYTHON_FRAMEWORK" \
  --argjson webdev_endpoints "$HAS_WEBDEV_ENDPOINTS" \
  --argjson e2e "$HAS_E2E" \
  --argjson stubs "$HAS_STUBS" \
  '{
    project_root: $project_root,
    project_title: $project_title,
    project_name: $project_name,
    gateway_url: $gateway_url,
    gateway_reachable: $gateway_reachable,
    has_perspective: $has_perspective,
    has_webdev: $has_webdev,
    has_scripting: $has_scripting,
    tag_providers: $tag_providers,
    existing_testing: {
      jython_framework: $jython_framework,
      webdev_endpoints: $webdev_endpoints,
      e2e: $e2e,
      stubs: $stubs
    }
  }'
