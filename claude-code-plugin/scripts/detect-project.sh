#!/usr/bin/env bash
# detect-project.sh — Auto-detect Ignition project structure and gateway state.
# Usage: detect-project.sh [project-directory]
# Outputs JSON with project metadata, gateway status, and existing test infrastructure.

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

TARGET="${1:-$PWD}"

PROJECT_ROOT=$(find_project_root "$TARGET") || {
  jq -n --arg target "$TARGET" '{"error": ("No project.json found walking up from " + $target)}' >&2
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
# Detect tag providers from a tags/ directory
detect_tag_providers() {
  local dir="$1"
  if [ -d "$dir/tags" ]; then
    (ls "$dir/tags" 2>/dev/null || true) | \
    sed 's/\.json$//' | \
    (grep -v -E '^(System|Gateway)$' || true) | \
    jq -R -s 'split("\n") | map(select(length > 0))'
  else
    echo "[]"
  fi
}

TAG_PROVIDERS=$(detect_tag_providers "$PROJECT_ROOT")
# If this project has no tags/ but parent does, check parent
if [ "$TAG_PROVIDERS" = "[]" ] && [ -n "$PARENT_ROOT" ]; then
  TAG_PROVIDERS=$(detect_tag_providers "$PARENT_ROOT")
fi

# Check for modules
HAS_PERSPECTIVE=false
HAS_WEBDEV=false
HAS_SCRIPTING=false
[ -d "$PROJECT_ROOT/com.inductiveautomation.perspective" ] && HAS_PERSPECTIVE=true
[ -d "$PROJECT_ROOT/com.inductiveautomation.webdev" ] && HAS_WEBDEV=true
[ -d "$PROJECT_ROOT/ignition/script-python" ] && HAS_SCRIPTING=true

# Check for tooling
HAS_IGNITION_LINT=false
IGNITION_LINT_PATH=""
if command -v ignition-lint &>/dev/null; then
  HAS_IGNITION_LINT=true
  IGNITION_LINT_PATH=$(command -v ignition-lint)
elif pip3 list 2>/dev/null | grep -qi ignition-lint; then
  HAS_IGNITION_LINT=true
  IGNITION_LINT_PATH="pip3"
fi

# Check for ignition-git-module evidence
# The git module syncs Ignition projects to a git repo. Evidence:
# - .git directory at or above the projects directory
# - tags/ directory contains exported tag JSON files (not just provider dirs)
# - A project-scan endpoint exists on the gateway
PROJECTS_DIR=$(dirname "$PROJECT_ROOT")
HAS_GIT_MODULE=false
HAS_GIT_REPO=false
HAS_TAG_EXPORTS=false
HAS_SCAN_ENDPOINT=false

# Git repo at projects level or project level
if [ -d "$PROJECTS_DIR/.git" ] || [ -d "$PROJECT_ROOT/.git" ]; then
  HAS_GIT_REPO=true
  HAS_GIT_MODULE=true
fi

# Tag exports — _types_ directories or deep JSON structures indicate git-managed tags
if [ -d "$PROJECT_ROOT/tags" ]; then
  # _types_ is the UDT export convention from ignition-git-module
  if find "$PROJECT_ROOT/tags" -name "_types_" -type d -maxdepth 3 2>/dev/null | grep -q .; then
    HAS_TAG_EXPORTS=true
    HAS_GIT_MODULE=true
  # .tag-groups.json or .tag-config.json are git module artifacts
  elif find "$PROJECT_ROOT/tags" -name ".tag-groups.json" -o -name ".tag-config.json" -maxdepth 2 2>/dev/null | grep -q .; then
    HAS_TAG_EXPORTS=true
    HAS_GIT_MODULE=true
  fi
fi

# Check parent too
if [ -n "$PARENT_ROOT" ] && [ "$HAS_TAG_EXPORTS" = false ] && [ -d "$PARENT_ROOT/tags" ]; then
  if find "$PARENT_ROOT/tags" -name "_types_" -type d -maxdepth 3 2>/dev/null | grep -q .; then
    HAS_TAG_EXPORTS=true
    HAS_GIT_MODULE=true
  elif find "$PARENT_ROOT/tags" -name ".tag-groups.json" -o -name ".tag-config.json" -maxdepth 2 2>/dev/null | grep -q .; then
    HAS_TAG_EXPORTS=true
    HAS_GIT_MODULE=true
  fi
fi

# Project scan endpoint (requires gateway + API token)
if [ "$GATEWAY_REACHABLE" = true ]; then
  SCAN_RESPONSE=$(curl -k -s -X POST --connect-timeout 3 -o /dev/null -w "%{http_code}" \
    "$GATEWAY_URL/data/project-scan-endpoint/scan" 2>/dev/null || echo "000")
  # 401 = endpoint exists but needs auth, 200 = open, 405 = exists but wrong method
  if [ "$SCAN_RESPONSE" = "401" ] || [ "$SCAN_RESPONSE" = "200" ] || [ "$SCAN_RESPONSE" = "405" ]; then
    HAS_SCAN_ENDPOINT=true
    HAS_GIT_MODULE=true
  fi
fi

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
  --argjson has_ignition_lint "$HAS_IGNITION_LINT" \
  --argjson has_git_module "$HAS_GIT_MODULE" \
  --argjson has_git_repo "$HAS_GIT_REPO" \
  --argjson has_tag_exports "$HAS_TAG_EXPORTS" \
  --argjson has_scan_endpoint "$HAS_SCAN_ENDPOINT" \
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
    tooling: {
      ignition_lint: $has_ignition_lint,
      git_module: $has_git_module,
      git_repo: $has_git_repo,
      tag_exports: $has_tag_exports,
      scan_endpoint: $has_scan_endpoint
    },
    existing_testing: {
      jython_framework: $jython_framework,
      webdev_endpoints: $webdev_endpoints,
      e2e: $e2e,
      stubs: $stubs
    }
  }'
