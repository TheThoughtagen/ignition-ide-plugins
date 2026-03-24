# Plugin Testing Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Jython gateway testing, Playwright e2e testing, and auto-scaffolding to the `ignition-scada` Claude Code plugin so any Ignition project gets a complete test setup from one or two commands.

**Architecture:** Layered design — deterministic shell scripts do all file creation (heredocs), skills wrap them with auto-detection and user interaction, hooks self-gate and run tests automatically. All new files go in `claude-code-plugin/`.

**Tech Stack:** Bash (scripts), Markdown (skills), Jython (test framework), TypeScript (Playwright e2e), JSON (configs)

**Spec:** `docs/superpowers/specs/2026-03-24-plugin-testing-integration-design.md`

**Source reference:** WHK-Global at `~/data/projects/WHK-Global/` contains the working implementations to genericize.

---

## File Map

### New files to create

```
claude-code-plugin/
├── scripts/
│   ├── detect-project.sh          # Auto-detection script
│   ├── scaffold-testing.sh        # Jython framework + WebDev endpoints + stubs
│   ├── scaffold-e2e.sh            # Playwright setup
│   ├── run-tests.sh               # Post-commit gateway test hook
│   └── run-ui-tests.sh            # Post-edit Playwright test hook
├── skills/
│   ├── init-testing/SKILL.md      # Scaffold Jython + WebDev
│   ├── init-e2e/SKILL.md          # Scaffold Playwright
│   └── test/SKILL.md              # Run tests
```

### Files to modify

```
claude-code-plugin/
├── .claude-plugin/plugin.json     # Version bump 0.1.0 → 0.2.0, update description
├── hooks/hooks.json               # Add run-tests.sh and run-ui-tests.sh hooks
└── README.md                      # Add testing documentation
```

---

## Task 1: Detection Script

**Files:**
- Create: `claude-code-plugin/scripts/detect-project.sh`

The foundation — all skills and scaffold scripts depend on this.

- [ ] **Step 1: Write detect-project.sh**

Create the detection script. It must:
- Accept optional `$1` as target directory (default: `$PWD`)
- Walk up from target looking for `project.json`
- Parse `project.json` with `jq` for `.title`
- Derive `project_name` from directory name
- Probe `https://localhost:9043/StatusPing` with `--connect-timeout 3`, fall back to `http://localhost:8088/StatusPing`
- Check for `com.inductiveautomation.perspective/`, `com.inductiveautomation.webdev/`, `ignition/script-python/`
- If gateway reachable, query `${GATEWAY_URL}/system/tag-providers` for tag provider list (fall back to empty array)
- Check for existing scaffolded components (`ignition/script-python/testing/runner/`, `com.inductiveautomation.webdev/resources/testing/`, `e2e/package.json`, `.ignition-stubs/testing/`)
- Output JSON to stdout

```bash
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
```

- [ ] **Step 2: Make executable and test**

Run: `chmod +x claude-code-plugin/scripts/detect-project.sh`

Test against WHK-Global (should detect everything):
```bash
claude-code-plugin/scripts/detect-project.sh ~/data/projects/WHK-Global
```

Expected: JSON output with `project_name: "WHK-Global"`, `has_perspective: true`, `existing_testing.jython_framework: true`, etc.

Test against a non-Ignition directory:
```bash
claude-code-plugin/scripts/detect-project.sh /tmp
```

Expected: Error message about no project.json found.

- [ ] **Step 3: Commit**

```bash
git add claude-code-plugin/scripts/detect-project.sh
git commit -m "feat(plugin): add detect-project.sh auto-detection script"
```

---

## Task 2: Scaffold Testing Script

**Files:**
- Create: `claude-code-plugin/scripts/scaffold-testing.sh`

**Source:** Genericize from WHK-Global's:
- `ignition/script-python/testing/` (5 modules: runner, assertions, decorators, helpers, reporter)
- `com.inductiveautomation.webdev/resources/testing/` (2 endpoints: run, tags)
- `.ignition-stubs/testing/` (5 .pyi files)

- [ ] **Step 1: Write scaffold-testing.sh**

Create the script with these specifications:

**Arguments:** `--project-root`, `--project-name`, `--gateway-url`, `--tag-provider`, `--force`, `--dry-run`

**Genericizations from WHK-Global originals:**

1. **runner/code.py** — Replace hardcoded paths:
   - `/usr/local/bin/ignition/data/projects/WHK-Global/...` → `/usr/local/bin/ignition/data/projects/${PROJECT_NAME}/...`
   - `/Users/pmannion/data/projects/WHK-Global/...` → Use actual `PROJECT_ROOT` variable set at top of file
   - Add a `# Configuration` section at top: `PROJECT_NAME = "PLACEHOLDER"` (replaced by scaffold script with `sed`)

2. **assertions/code.py** — Use as-is from WHK-Global (fully generic already)

3. **decorators/code.py** — Use as-is from WHK-Global (fully generic already)

4. **helpers/code.py** — Drop `run_process_queue()` and `_run_process_queue_direct()` (WHK-specific business logic). Keep only:
   - `write_dataset_tag(tag_path, columns, types, rows)`
   - `clear_dataset_tag(tag_path, columns, types)`

5. **reporter/code.py** — Use as-is from WHK-Global (fully generic already)

6. **WebDev run/doGet.py** — Replace `"WHK-Global Test Runner"` with `"${PROJECT_NAME} Test Runner"` (sed replacement)

7. **WebDev run/doPost.py** — Use as-is (fully generic already — references `testing.runner` and `testing.reporter` which are module-relative)

8. **WebDev tags/doGet.py** — Replace hardcoded `[WHK01]` tag path in simulatorCsv section with `[${TAG_PROVIDER}]`. Replace `'WHK_Sim_program.csv'` filename with `'${PROJECT_NAME}_Sim_program.csv'`

9. **WebDev tags/doPost.py** — Replace hardcoded `/usr/local/bin/ignition/data/projects/WHK-Global` in importTags section. Drop the `mirror` handler that calls `general.tools.conversions.convert_to_memory_tags` (that's a WHK-specific script). Keep: writes, reads, script, deleteTags, importTags (with parameterized path)

10. **config.json** — Use as-is (identical for both endpoints)

11. **resource.json** — Use as-is (identical for all 5 modules)

12. **.pyi stubs** — Use as-is from WHK-Global stubs, minus the `run_process_queue` and `_run_process_queue_direct` entries in helpers.pyi

**Structure:**
- Parse args with `while` loop and `case` statement
- For each file: check if it exists (skip unless `--force`), create parent dirs with `mkdir -p`, write content with heredoc
- `--dry-run` prints what would be created without writing
- Track created/skipped counts, report at end

The script will be large (~800-1000 lines) due to heredoc file content. This is expected and intentional — the entire Jython framework is embedded.

- [ ] **Step 2: Make executable and test**

Test with dry-run against a temp directory:
```bash
mkdir -p /tmp/test-ignition-project
echo '{"title":"Test","enabled":true}' > /tmp/test-ignition-project/project.json
mkdir -p /tmp/test-ignition-project/ignition/script-python
mkdir -p /tmp/test-ignition-project/com.inductiveautomation.webdev/resources

claude-code-plugin/scripts/scaffold-testing.sh \
  --project-root /tmp/test-ignition-project \
  --project-name Test \
  --gateway-url https://localhost:9043 \
  --tag-provider default \
  --dry-run
```

Expected: List of files that would be created.

Test actual creation:
```bash
claude-code-plugin/scripts/scaffold-testing.sh \
  --project-root /tmp/test-ignition-project \
  --project-name Test \
  --gateway-url https://localhost:9043 \
  --tag-provider default
```

Expected: All files created. Verify:
- `runner/code.py` contains `PROJECT_NAME = "Test"` (not `WHK-Global`)
- `helpers/code.py` does NOT contain `run_process_queue`
- `doGet.py` shows `"Test Test Runner"`
- `config.json` has `require-auth: false`

Test idempotency:
```bash
# Run again — should skip all files
claude-code-plugin/scripts/scaffold-testing.sh \
  --project-root /tmp/test-ignition-project \
  --project-name Test \
  --gateway-url https://localhost:9043 \
  --tag-provider default
```

Expected: All files skipped.

Clean up: `rm -rf /tmp/test-ignition-project`

- [ ] **Step 3: Commit**

```bash
git add claude-code-plugin/scripts/scaffold-testing.sh
git commit -m "feat(plugin): add scaffold-testing.sh for Jython test framework"
```

---

## Task 3: Scaffold E2E Script

**Files:**
- Create: `claude-code-plugin/scripts/scaffold-e2e.sh`

**Source:** Genericize from WHK-Global's `e2e/` directory.

- [ ] **Step 1: Write scaffold-e2e.sh**

**Arguments:** `--project-root`, `--project-name`, `--gateway-url`, `--tag-provider`, `--perspective-project`, `--force`, `--dry-run`

**Genericizations from WHK-Global originals:**

1. **package.json** — Change `"name"` from `"whk-global-e2e"` to `"${PROJECT_NAME_LOWER}-e2e"` (lowercase). Keep same deps and scripts.

2. **tsconfig.json** — Use as-is (fully generic)

3. **playwright.config.ts** — Remove the `api` project block. Keep `setup` and `chromium` only. Replace hardcoded `QSI_WhiskeyHouseKentucky01` with env var reference (already uses `process.env.PERSPECTIVE_PROJECT`).

4. **.env.example** — Template with `IGNITION_URL`, `IGNITION_USER`, `IGNITION_PASSWORD`, `PERSPECTIVE_PROJECT=${PERSPECTIVE_PROJECT}`, `TAG_PROVIDER=${TAG_PROVIDER}`. Drop all MES/WMS vars.

5. **.gitignore** — `node_modules/`, `test-results/`, `playwright-report/`, `.auth/`, `.env`, `dist/`, `.playwright-running.lock`

6. **fixtures/auth.setup.ts** — Use as-is (already uses env vars, generic login detection)

7. **fixtures/perspective.ts** — Use as-is (fully generic)

8. **helpers/gateway-api.ts** — Drop everything below line 176 (MES, WMS, changeover tags, GraphQL sections). Replace hardcoded `WHK-Global` in `WEBDEV` constant with `process.env.IGNITION_PROJECT_NAME || "PROJECT_NAME_PLACEHOLDER"` (sed-replaced by script). Keep: `post()`, `get()`, tag operations, mirror operations, script invocation, health checks.

9. **pages/PerspectivePage.ts** — Use as-is (already uses env var for project name)

10. **components/PerspectiveComponent.ts, Button.ts, Table.ts** — Use as-is (fully generic)

11. **tests/smoke/perspective-loads.spec.ts** — Rewrite to be generic:
    - Keep "session loads and docks render" (universal)
    - Drop "Cooker 1 page loads" (WHK-specific)
    - Drop "top dock renders with plant instrumentation" (WHK-specific)
    - Drop "Changeover Dashboard loads" (WHK-specific, imports ChangeoverDashboard)
    - Drop "left dock menu tree" (WHK-specific labels)
    - Add generic tests: "session loads", "page content renders components", "navigation exists in DOM"

Same structure as scaffold-testing.sh: parse args, heredoc files, dry-run support, idempotent.

- [ ] **Step 2: Make executable and test**

Test with dry-run, then actual creation against temp directory. Verify:
- `gateway-api.ts` does NOT contain `mesLogin`, `wmsLogin`, `CHANGEOVER_TAGS`, `changeoverGet`
- `gateway-api.ts` DOES contain `readTags`, `writeTags`, `callScript`, `isGatewayReachable`
- `.env.example` does NOT contain `MES_HOST` or `WMS_HOST`
- `playwright.config.ts` does NOT have `api` project
- Smoke tests do NOT import `ChangeoverDashboard`

- [ ] **Step 3: Commit**

```bash
git add claude-code-plugin/scripts/scaffold-e2e.sh
git commit -m "feat(plugin): add scaffold-e2e.sh for Playwright test setup"
```

---

## Task 4: Hook Scripts

**Files:**
- Create: `claude-code-plugin/scripts/run-tests.sh`
- Create: `claude-code-plugin/scripts/run-ui-tests.sh`

- [ ] **Step 1: Write run-tests.sh**

Post-commit gateway test runner. Based on WHK-Global's `.claude/hooks/run-tests.sh` with these changes:
- Derive `PROJECT_NAME` from directory name (not hardcoded)
- Gateway URL from `$IGNITION_GATEWAY_URL` env var, or `.env` in project root, or fallback `https://localhost:9043`
- API token from `$IGNITION_API_TOKEN_FILE` env var (not hardcoded path)
- Command matching: `[[ "$COMMAND" =~ git\ commit($|\ ) ]]`
- Poll-based scan wait (5 iterations × 1s) instead of `sleep 3`
- Self-gating: exit 0 if no `project.json` or no `testing/run` WebDev endpoint

```bash
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
if [[ ! "$STDOUT" =~ create\ mode|file\ changed|files\ changed|insertions|deletions ]] && [[ ! "$STDOUT" =~ \[ ]]; then
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

# Wait for scan propagation (best-effort, max 5s)
for i in 1 2 3 4 5; do
  sleep 1
  curl -k -s --connect-timeout 2 "$GATEWAY_URL/StatusPing" > /dev/null 2>&1 && break
done

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
```

- [ ] **Step 2: Write run-ui-tests.sh**

Post-edit Playwright hook. Based on WHK-Global's `.claude/hooks/run-ui-tests.sh` with these changes:
- Find `e2e/` relative to project root (not hardcoded)
- Add `mkdir`-based concurrency guard
- Self-gating checks

```bash
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
```

- [ ] **Step 3: Make both executable**

```bash
chmod +x claude-code-plugin/scripts/run-tests.sh claude-code-plugin/scripts/run-ui-tests.sh
```

- [ ] **Step 4: Commit**

```bash
git add claude-code-plugin/scripts/run-tests.sh claude-code-plugin/scripts/run-ui-tests.sh
git commit -m "feat(plugin): add post-commit and post-edit test hook scripts"
```

---

## Task 5: Update hooks.json

**Files:**
- Modify: `claude-code-plugin/hooks/hooks.json`

- [ ] **Step 1: Update hooks.json**

Replace the current single-hook config with the full three-hook config from the spec:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/ignition-lint.sh",
            "timeout": 30
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/run-ui-tests.sh",
            "timeout": 120
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/run-tests.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add claude-code-plugin/hooks/hooks.json
git commit -m "feat(plugin): register gateway test and UI test hooks"
```

---

## Task 6: Skills — init-testing

**Files:**
- Create: `claude-code-plugin/skills/init-testing/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
description: Scaffold the Jython test framework, WebDev test endpoints, and type stubs into an Ignition project. Usage — /ignition-scada:init-testing [--all] [--force]
---

# Initialize Ignition Testing

Scaffold a complete Jython test framework into the current Ignition project. This creates:
- **testing/** script library (runner, assertions, decorators, helpers, reporter)
- **WebDev endpoints** for running tests and manipulating tags (`testing/run`, `testing/tags`)
- **Type stubs** for IDE completion (`.ignition-stubs/testing/`)

## Steps

1. Run the detection script to discover project context:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/detect-project.sh
   ```

2. Parse the JSON output and present findings to the user:
   - Project name and location
   - Gateway URL and reachability
   - Tag providers (if detected)
   - Any existing test infrastructure

3. Ask the user to confirm or provide their tag provider name.

4. If `existing_testing.jython_framework` or `existing_testing.webdev_endpoints` is true, warn the user and ask if they want to overwrite (`--force`).

5. Run the scaffold script:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold-testing.sh \
     --project-root <detected> \
     --project-name <detected> \
     --gateway-url <detected> \
     --tag-provider <confirmed>
   ```
   Add `--force` if user confirmed overwrite.

6. Report what was created (list the files).

7. If the gateway is reachable, verify the setup by hitting the test discovery endpoint:
   ```bash
   curl -k -s "https://localhost:9043/system/webdev/<project>/testing/run?discover=true"
   ```
   Note: This requires a gateway project scan first. Tell the user to scan from Designer or commit + push if using ignition-git-module.

8. Explain how to write a first test:
   - Create `ignition/script-python/<package>/__tests__/code.py`
   - Import `from testing.decorators import test` and `from testing.assertions import assert_equal`
   - Write `@test` decorated functions
   - Run from Script Console: `print testing.runner.run_all()`

If `$ARGUMENTS` contains `--all` and the project has Perspective (`has_perspective` is true), automatically proceed to run the `/ignition-scada:init-e2e` flow after completing the testing setup.
```

- [ ] **Step 2: Commit**

```bash
git add claude-code-plugin/skills/init-testing/SKILL.md
git commit -m "feat(plugin): add init-testing skill for Jython framework scaffolding"
```

---

## Task 7: Skills — init-e2e

**Files:**
- Create: `claude-code-plugin/skills/init-e2e/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
description: Scaffold Playwright e2e tests for Perspective views into an Ignition project. Usage — /ignition-scada:init-e2e [--force]
---

# Initialize E2E Tests

Scaffold a complete Playwright e2e test setup for Perspective views. This creates:
- **e2e/** directory with Playwright config, auth fixtures, and TypeScript setup
- **Page objects** for Perspective views (PerspectivePage base class)
- **Component wrappers** (Button, Table, PerspectiveComponent)
- **Gateway API helper** for tag read/write, script invocation, and health checks
- **Smoke tests** that verify session loading and basic rendering

## Steps

1. Run the detection script:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/detect-project.sh
   ```

2. Check `has_perspective` — if false, warn the user: "No Perspective module found (`com.inductiveautomation.perspective/` directory missing). E2E tests require Perspective views. Continue anyway?"

3. Present findings and ask the user to confirm their tag provider.

4. Auto-detect the Perspective project name:
   - If the gateway is reachable, the Perspective project name is typically the Ignition project name
   - Check environment for `PERSPECTIVE_PROJECT` variable
   - Ask the user to confirm the Perspective project name

5. Ask the user to confirm the Perspective project name.

6. Check if the Jython test framework exists (`existing_testing.jython_framework`). If not, inform the user and automatically run the testing scaffold first:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold-testing.sh \
     --project-root <detected> \
     --project-name <detected> \
     --gateway-url <detected> \
     --tag-provider <confirmed>
   ```
   The e2e gateway-api helper depends on the WebDev `testing/tags` endpoint.

7. Run the e2e scaffold script:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold-e2e.sh \
     --project-root <detected> \
     --project-name <detected> \
     --gateway-url <detected> \
     --tag-provider <confirmed> \
     --perspective-project <confirmed>
   ```

8. Install dependencies:
   ```bash
   cd <project-root>/e2e && npm install && npx playwright install chromium
   ```

9. Tell the user to set up credentials:
   - Copy `e2e/.env.example` to `e2e/.env`
   - Fill in `IGNITION_USER` and `IGNITION_PASSWORD`

10. Explain auth setup:
    - Run `cd e2e && npx playwright test --project=setup` to authenticate
    - Run `npm test` to run the smoke tests
    - Run `npx playwright show-report` to view results in a browser
```

- [ ] **Step 2: Commit**

```bash
git add claude-code-plugin/skills/init-e2e/SKILL.md
git commit -m "feat(plugin): add init-e2e skill for Playwright scaffolding"
```

---

## Task 8: Skills — test

**Files:**
- Create: `claude-code-plugin/skills/test/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

```markdown
---
description: Run Jython gateway tests or Playwright e2e tests. Usage — /ignition-scada:test [module|package|ui|e2e|smoke]
---

# Run Tests

Run tests for the current Ignition project. Routes to gateway tests (Jython) or browser tests (Playwright) based on arguments.

## Arguments

`$ARGUMENTS`

## Routing

| Argument | Action |
|----------|--------|
| *(empty)* | Run all gateway Jython tests |
| `<short-name>` (e.g. `changeover`) | Translate to module path and run: try `<name>.__tests__` first, search for matching module |
| `<dotted.path>` (contains `.`) | Run as module or package filter |
| `ui` or `e2e` | Run all Playwright tests |
| `ui <area>` | Run Playwright tests in `e2e/tests/<area>/` |
| `smoke` | Run `e2e/tests/smoke/` |

## Gateway Tests

1. Detect the project using the detect-project script:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/detect-project.sh
   ```

2. Check that test infrastructure exists (`existing_testing.jython_framework` and `existing_testing.webdev_endpoints`). If not, tell the user: "Test infrastructure not found. Run `/ignition-scada:init-testing` first."

3. Trigger a gateway project scan (if API token is available):
   ```bash
   TOKEN_FILE="${IGNITION_API_TOKEN_FILE:-}"
   if [ -n "$TOKEN_FILE" ] && [ -f "$TOKEN_FILE" ]; then
     TOKEN=$(cat "$TOKEN_FILE")
     curl -k -s -X POST -H "X-Ignition-API-Token: $TOKEN" \
       "<gateway>/data/project-scan-endpoint/scan?updateDesigners=true"
   fi
   ```

4. Wait 3-5 seconds for scan propagation.

5. Run the tests:
   ```bash
   # All tests
   curl -k -s -X POST "<gateway>/system/webdev/<project>/testing/run"

   # Specific module
   curl -k -s -X POST "<gateway>/system/webdev/<project>/testing/run?module=<module>"

   # Package filter
   curl -k -s -X POST "<gateway>/system/webdev/<project>/testing/run?package=<package>"
   ```

6. Parse the JSON response and present results:
   - Summary: total, passed, failed, skipped, errors, duration
   - On failure: show each failure with test name, error message, and traceback
   - On success: report concisely

## Playwright Tests

1. Check that `e2e/node_modules` exists. If not, tell the user to run `cd e2e && npm install && npx playwright install chromium`.

2. Check that `e2e/.auth/user.json` exists. If not, tell the user to run `cd e2e && npx playwright test --project=setup`.

3. Run the tests:
   ```bash
   # All e2e tests
   cd e2e && npx playwright test

   # Specific area
   cd e2e && npx playwright test tests/<area>/

   # Smoke only
   cd e2e && npx playwright test tests/smoke/

   # Add --headed if user says "headed" or "watch"
   ```

4. Parse the output and report results.

5. On failure, suggest: `cd e2e && npx playwright show-report`
```

- [ ] **Step 2: Commit**

```bash
git add claude-code-plugin/skills/test/SKILL.md
git commit -m "feat(plugin): add test skill for running gateway and e2e tests"
```

---

## Task 9: Plugin Manifest and README

**Files:**
- Modify: `claude-code-plugin/.claude-plugin/plugin.json`
- Modify: `claude-code-plugin/README.md`

- [ ] **Step 1: Update plugin.json**

Bump version to `0.2.0` and update description:

```json
{
  "name": "ignition-scada",
  "description": "Ignition SCADA development — API reference, expression language, auto-linting, test scaffolding, and automated testing for Ignition projects",
  "version": "0.2.0",
  "author": {
    "name": "Whiskey House",
    "url": "https://github.com/whiskeyhouse"
  },
  "homepage": "https://github.com/whiskeyhouse/ignition-nvim",
  "repository": "https://github.com/whiskeyhouse/ignition-nvim",
  "license": "MIT",
  "keywords": ["ignition", "scada", "ics", "inductive-automation", "jython", "plc", "testing", "playwright"],
  "skills": "./skills/",
  "hooks": "./hooks/hooks.json"
}
```

- [ ] **Step 2: Update README.md**

Add a Testing section after the existing content. Cover:
- What the testing features provide (Jython framework, e2e, hooks)
- Quick start: `/ignition-scada:init-testing --all`
- Running tests: `/ignition-scada:test`, `/ignition-scada:test ui`
- Deterministic mode: direct shell script usage
- Prerequisites: Node.js for e2e, `jq` for detection
- What the plugin scaffolds (file tree)
- What the hooks do automatically

- [ ] **Step 3: Commit**

```bash
git add claude-code-plugin/.claude-plugin/plugin.json claude-code-plugin/README.md
git commit -m "feat(plugin): bump to v0.2.0 with testing integration"
```

---

## Task 10: End-to-End Verification

- [ ] **Step 1: Verify plugin structure**

```bash
find claude-code-plugin -type f | sort
```

Expected: All files from the file map exist.

- [ ] **Step 2: Test detect-project.sh against WHK-Global**

```bash
claude-code-plugin/scripts/detect-project.sh ~/data/projects/WHK-Global
```

Expected: Complete JSON with all fields populated.

- [ ] **Step 3: Test scaffold scripts with --dry-run**

```bash
mkdir -p /tmp/verify-plugin
echo '{"title":"Verify","enabled":true}' > /tmp/verify-plugin/project.json
mkdir -p /tmp/verify-plugin/ignition/script-python
mkdir -p /tmp/verify-plugin/com.inductiveautomation.webdev/resources
mkdir -p /tmp/verify-plugin/com.inductiveautomation.perspective/views

claude-code-plugin/scripts/scaffold-testing.sh \
  --project-root /tmp/verify-plugin \
  --project-name Verify \
  --gateway-url https://localhost:9043 \
  --tag-provider VFY01 \
  --dry-run

claude-code-plugin/scripts/scaffold-e2e.sh \
  --project-root /tmp/verify-plugin \
  --project-name Verify \
  --gateway-url https://localhost:9043 \
  --tag-provider VFY01 \
  --perspective-project QSI_Verify \
  --dry-run
```

- [ ] **Step 4: Test full scaffold**

```bash
claude-code-plugin/scripts/scaffold-testing.sh \
  --project-root /tmp/verify-plugin \
  --project-name Verify \
  --gateway-url https://localhost:9043 \
  --tag-provider VFY01

claude-code-plugin/scripts/scaffold-e2e.sh \
  --project-root /tmp/verify-plugin \
  --project-name Verify \
  --gateway-url https://localhost:9043 \
  --tag-provider VFY01 \
  --perspective-project QSI_Verify

# Verify key substitutions
grep "PROJECT_NAME" /tmp/verify-plugin/ignition/script-python/testing/runner/code.py
grep "VFY01" /tmp/verify-plugin/e2e/.env.example
grep "QSI_Verify" /tmp/verify-plugin/e2e/.env.example
```

- [ ] **Step 5: Test hook scripts with mock input**

```bash
# Test run-tests.sh exits silently on non-commit
echo '{"tool_input":{"command":"git status"},"tool_result":{"stdout":""}}' | \
  claude-code-plugin/scripts/run-tests.sh

# Test run-ui-tests.sh exits silently on non-view file
echo '{"tool_input":{"file_path":"/tmp/foo.py"}}' | \
  claude-code-plugin/scripts/run-ui-tests.sh
```

Both should exit 0 with no output.

- [ ] **Step 6: Clean up and final commit**

```bash
rm -rf /tmp/verify-plugin
```

If any issues were found and fixed during verification, commit the fixes.
