---
name: test
description: Run Jython gateway tests or Playwright e2e tests. Usage — /ignition-scada:test [module|package|ui|e2e|smoke]
---

# Run Tests

Run tests for the current Ignition project. Routes to gateway tests (Jython) or browser tests (Playwright) based on arguments.

## Arguments

`$ARGUMENTS`

## Routing

**Default is always gateway (Jython) tests.** Only route to Playwright when explicitly asked with `ui` or `e2e`.

| Argument | Action |
|----------|--------|
| *(empty)* | Run all gateway Jython tests |
| `<short-name>` (e.g. `changeover`) | Translate to module path and run gateway test: try `<name>.__tests__` first, search for matching module |
| `<dotted.path>` (contains `.`) | Run as gateway module or package filter |
| `ui` or `e2e` | Run all Playwright browser tests |
| `ui <area>` | Run Playwright tests in `e2e/tests/<area>/` |
| `ui smoke` | Run Playwright smoke tests (`e2e/tests/smoke/`) |
| `smoke` | Run gateway Jython tests — NOT Playwright. "Smoke test" without `ui` prefix means gateway tests. |

**Ambiguity rule:** If the user says "smoke test", "run tests", "test it", or any unqualified test request — **always default to gateway Jython tests**, not Playwright. Only use Playwright when the user explicitly says "ui", "e2e", "browser", or "playwright".

## Gateway Tests

1. Detect the project using the detect-project script:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/detect-project.sh
   ```

2. Check that test infrastructure exists (`existing_testing.jython_framework` and `existing_testing.webdev_endpoints`). If not, tell the user: "Test infrastructure not found. Run `/ignition-scada:init-testing` first."

3. **Commit or stash pending changes** before proceeding. The force scan in the next step can trigger the Designer or Git module to write back to the project directory — uncommitted work could be overwritten.

4. **Bump `resource.json` versions** for any script modules that were edited since the last test run. Ignition's Jython runtime caches compiled modules in `sys.modules` — a project scan alone does NOT flush this cache. Incrementing the `version` field is the strongest signal to force re-import.

   For each modified `code.py`, increment `version` in the adjacent `resource.json`:
   ```json
   { "version": 2, ... }
   ```

5. Trigger a gateway project scan with `forceUpdate=true` (if API token is available):
   ```bash
   TOKEN_FILE="${IGNITION_API_TOKEN_FILE:-}"
   if [ -n "$TOKEN_FILE" ] && [ -f "$TOKEN_FILE" ]; then
     TOKEN=$(cat "$TOKEN_FILE")
     curl -k -s -X POST -H "X-Ignition-API-Token: $TOKEN" \
       "<gateway>/data/project-scan-endpoint/scan?updateDesigners=true&forceUpdate=true"
   fi
   ```

   **Why `forceUpdate=true`?** Without it, the scan may skip resources it considers unchanged. Combined with the version bump, this ensures the gateway picks up the new bytecode.

6. Wait 3-5 seconds for scan propagation.

7. Run the tests:
   ```bash
   # All tests
   curl -k -s -X POST "<gateway>/system/webdev/<project>/testing/run"

   # Specific module
   curl -k -s -X POST "<gateway>/system/webdev/<project>/testing/run?module=<module>"

   # Package filter
   curl -k -s -X POST "<gateway>/system/webdev/<project>/testing/run?package=<package>"
   ```

8. Parse the JSON response and present results:
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

   # Add --headed if the user says "headed" or "watch"
   ```

4. Parse the output and report results.

5. On failure, suggest: `cd e2e && npx playwright show-report`
