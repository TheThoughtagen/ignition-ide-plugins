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

# Check for parent project (Ignition project inheritance)
PARENT_NAME=$(jq -r '.parent // ""' "$PROJECT_ROOT/project.json" 2>/dev/null || echo "")
PARENT_ROOT=""
PARENT_HAS_JYTHON_FRAMEWORK=false
PARENT_HAS_WEBDEV_ENDPOINTS=false

if [ -n "$PARENT_NAME" ]; then
  # Parent projects are typically siblings in the same directory
  CANDIDATE="$(dirname "$PROJECT_ROOT")/$PARENT_NAME"
  if [ -f "$CANDIDATE/project.json" ]; then
    PARENT_ROOT="$CANDIDATE"
    [ -d "$PARENT_ROOT/ignition/script-python/testing/runner" ] && PARENT_HAS_JYTHON_FRAMEWORK=true
    [ -d "$PARENT_ROOT/com.inductiveautomation.webdev/resources/testing/run" ] && PARENT_HAS_WEBDEV_ENDPOINTS=true
  fi
fi

# Check for parent e2e .env (can be reused/copied for child projects)
PARENT_HAS_E2E_ENV=false
PARENT_E2E_ENV_PATH=""
if [ -n "$PARENT_ROOT" ] && [ -f "$PARENT_ROOT/e2e/.env" ]; then
  PARENT_HAS_E2E_ENV=true
  PARENT_E2E_ENV_PATH="$PARENT_ROOT/e2e/.env"
fi

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

# Detect tag providers from the tags/ directory on disk.
# Each .json file or subdirectory in tags/ is a provider.
# Filter out system providers (System, Gateway) — users want their own.
TAG_PROVIDERS="[]"
if [ -d "$PROJECT_ROOT/tags" ]; then
  TAG_PROVIDERS=$(
    (ls "$PROJECT_ROOT/tags" 2>/dev/null || true) | \
    sed 's/\.json$//' | \
    grep -v -E '^(System|Gateway)$' | \
    jq -R -s 'split("\n") | map(select(length > 0))'
  )
fi
# If this project has no tags/ but parent does, check parent
if [ "$TAG_PROVIDERS" = "[]" ] && [ -n "$PARENT_ROOT" ] && [ -d "$PARENT_ROOT/tags" ]; then
  TAG_PROVIDERS=$(
    (ls "$PARENT_ROOT/tags" 2>/dev/null || true) | \
    sed 's/\.json$//' | \
    grep -v -E '^(System|Gateway)$' | \
    jq -R -s 'split("\n") | map(select(length > 0))'
  )
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
  --arg parent_name "$PARENT_NAME" \
  --arg parent_root "$PARENT_ROOT" \
  --argjson parent_has_jython_framework "$PARENT_HAS_JYTHON_FRAMEWORK" \
  --argjson parent_has_webdev_endpoints "$PARENT_HAS_WEBDEV_ENDPOINTS" \
  --argjson parent_has_e2e_env "$PARENT_HAS_E2E_ENV" \
  --arg parent_e2e_env_path "$PARENT_E2E_ENV_PATH" \
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
    parent: (if $parent_name == "" then null else {
      name: $parent_name,
      root: (if $parent_root == "" then null else $parent_root end),
      has_jython_framework: $parent_has_jython_framework,
      has_webdev_endpoints: $parent_has_webdev_endpoints,
      has_e2e_env: $parent_has_e2e_env,
      e2e_env_path: (if $parent_e2e_env_path == "" then null else $parent_e2e_env_path end)
    } end),
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
