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
   - **Parent project** (if this project inherits from another)

3. Ask the user to confirm or provide their tag provider name.

4. **Check for project inheritance.** If `parent` is not null:
   - Tell the user: "This project inherits from *{parent.name}*."
   - If `parent.has_jython_framework` is true: "The parent project already has the Jython test framework — your project inherits `testing.*` scripts automatically. I'll skip scaffolding scripts and only create the WebDev endpoints and type stubs."
   - If parent not found on disk (`parent.root` is null): ask the user for the parent project path, or offer to scaffold everything locally.

5. If `existing_testing.jython_framework` or `existing_testing.webdev_endpoints` is true, warn the user and ask if they want to overwrite (`--force`).

6. Run the scaffold script:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold-testing.sh \
     --project-root <detected> \
     --project-name <detected> \
     --gateway-url <detected> \
     --tag-provider <confirmed>
   ```
   Add `--skip-scripts` if the parent already has the Jython framework.
   Add `--force` if user confirmed overwrite.

6. Report what was created (list the files).

7. If the gateway is reachable, verify the setup by hitting the test discovery endpoint:
   ```bash
   curl -k -s "<gateway>/system/webdev/<project>/testing/run?discover=true"
   ```
   Note: This requires a gateway project scan first. Tell the user to scan from Designer or commit + push if using ignition-git-module.

8. Explain how to write a first test:
   - Create `ignition/script-python/<package>/__tests__/code.py`
   - Import `from testing.decorators import test` and `from testing.assertions import assert_equal`
   - Write `@test` decorated functions
   - Run from Script Console: `print testing.runner.run_all()`

If `$ARGUMENTS` contains `--all` and the project has Perspective (`has_perspective` is true), automatically proceed to run the `/ignition-scada:init-e2e` flow after completing the testing setup.
