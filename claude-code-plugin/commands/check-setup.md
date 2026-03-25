---
description: Validate your Ignition project setup — checks gateway, tooling, test infrastructure, and plugin health
argument-hint: ""
---

Run a full health check on the current Ignition project and report what's working, what's missing, and how to fix it.

## Steps

1. Run the detection script:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/detect-project.sh
   ```

2. Parse the JSON output and report each section with a status indicator:

### Project Detection
- Project name and title found → pass
- No project.json found → fail, explain they need to be in an Ignition project directory

### Gateway Connection
- `gateway_reachable: true` → pass, show URL
- `gateway_reachable: false` → warn, explain gateway needs to be running for tests. Show the URL that was probed.

### Project Inheritance
- `parent` is not null and `parent.root` found → pass, show parent name and what's inherited
- `parent` is not null but `parent.root` is null → warn, parent declared but not found on disk as sibling
- `parent` is null → info, standalone project (no inheritance)

### Tag Providers
- `tag_providers` has entries → pass, list them
- `tag_providers` is empty → warn, no providers detected. Explain this means the tags/ directory is empty or missing.

### Tooling — ignition-lint
- `tooling.ignition_lint: true` → pass
- `tooling.ignition_lint: false` → warn, auto-lint hook won't fire. Suggest: `pip install ignition-lint-toolkit`

### Tooling — ignition-git-module
- `tooling.git_module: true` → pass, show which evidence was found (git_repo, tag_exports, scan_endpoint)
- `tooling.git_module: false` → info, not detected. Explain this is optional but enables automatic project scanning after commits.

### Tooling — Scan Endpoint
- `tooling.scan_endpoint: true` → pass, test hooks can trigger project scans automatically
- `tooling.scan_endpoint: false` and gateway reachable → warn, scan endpoint not found. Test hooks will skip the scan step. If using ignition-git-module, check that the scan endpoint WebDev resource is deployed.
- Gateway not reachable → skip this check

### Test Infrastructure — Jython Framework
- `existing_testing.jython_framework: true` OR `parent.has_jython_framework: true` → pass (note if inherited)
- Both false → info, not scaffolded yet. Suggest: `/init-testing`

### Test Infrastructure — WebDev Endpoints
- `existing_testing.webdev_endpoints: true` → pass
- False → info, not scaffolded yet. Suggest: `/init-testing`

### Test Infrastructure — E2E Tests
- `existing_testing.e2e: true` → pass. Also check if `e2e/node_modules` exists (deps installed) and `e2e/.auth/user.json` exists (authenticated).
  - node_modules missing → warn, run `cd e2e && npm install && npx playwright install chromium`
  - .auth/user.json missing → warn, run `cd e2e && npx playwright test --project=setup`
- `existing_testing.e2e: false` → info, not scaffolded yet. Suggest: `/init-e2e`

### Test Infrastructure — Type Stubs
- `existing_testing.stubs: true` → pass
- False → info, IDE completions for testing.* won't work. Suggest: `/init-testing`

### Ignition Resource Structure
- Check for any directories in `ignition/script-python/` that are missing `resource.json` — these won't be loaded by the gateway.
  ```bash
  find <project_root>/ignition/script-python -type d -exec test ! -f '{}/resource.json' \; -print
  ```
  - None found → pass
  - Found some → warn, list them. Explain that every directory needs resource.json.

3. Present results as a table with status icons:
   - PASS = working correctly
   - WARN = something to fix (with actionable suggestion)
   - INFO = optional, not configured
   - FAIL = blocking issue

4. At the end, give a one-line summary: "X checks passed, Y warnings, Z issues" and suggest the most important next action if any warnings exist.
