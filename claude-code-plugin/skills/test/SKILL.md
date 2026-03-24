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

   # Add --headed if the user says "headed" or "watch"
   ```

4. Parse the output and report results.

5. On failure, suggest: `cd e2e && npx playwright show-report`
