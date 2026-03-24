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

9. Set up the `.env` file:
   - Check detection output for `parent.has_e2e_env`. If the parent project has an existing `e2e/.env`:
     - Tell the user: "Your parent project *{parent.name}* already has an `e2e/.env` at `{parent.e2e_env_path}`. Since both projects share the same gateway, I can copy it and just update the `PERSPECTIVE_PROJECT` name."
     - Copy the parent's `.env` to `<project-root>/e2e/.env`
     - Update `PERSPECTIVE_PROJECT` to the confirmed value for this project
     - Show the user what was set and ask them to verify credentials are still correct
   - If no parent `.env` exists:
     - Copy `e2e/.env.example` to `e2e/.env`
     - Tell the user to fill in `IGNITION_USER` and `IGNITION_PASSWORD`
   - **Never commit `.env`** — it's in the scaffolded `.gitignore`

10. Explain auth setup:
    - Run `cd e2e && npx playwright test --project=setup` to authenticate
    - Run `npm test` to run the smoke tests
    - Run `npx playwright show-report` to view results in a browser
