# Plugin Testing Integration Design

**Date:** 2026-03-24
**Status:** Draft
**Scope:** Integrate Jython gateway testing and Playwright e2e testing into the `ignition-scada` Claude Code plugin

## Problem

WHK-Global has a mature testing infrastructure — a Jython unit test framework that runs on the Ignition gateway, Playwright e2e tests for Perspective views, and Claude Code hooks that tie them together. But this infrastructure is bespoke to that one project. Every new Ignition project starts from zero.

The `ignition-scada` Claude Code plugin already provides auto-linting, API reference, and expression language support. Extending it with test scaffolding means any Ignition developer gets a complete testing setup with one or two commands.

## Decision: Option B + C Hybrid

**Layered skills** for orchestration and context-awareness, backed by **deterministic shell scripts** for reproducibility. Skills call the scripts; users can also call the scripts directly without Claude.

## Architecture

### Detection Layer

`scripts/detect-project.sh` — shared auto-detection script.

**Inputs:** Optional project directory (defaults to walking up from `$PWD` looking for `project.json`).

**Outputs JSON:**
```json
{
  "project_root": "/path/to/project",
  "project_title": "Global",
  "project_name": "WHK-Global",
  "gateway_url": "https://localhost:9043",
  "gateway_reachable": true,
  "has_perspective": true,
  "has_webdev": true,
  "has_scripting": true,
  "tag_providers": ["WHK01", "default"],
  "existing_testing": {
    "jython_framework": false,
    "webdev_endpoints": false,
    "e2e": false,
    "stubs": false
  }
}
```

**Detection logic:**
- `project_root`: Walk up from target dir looking for `project.json`
- `project_title`: Parse `project.json` → `.title`
- `project_name`: Directory name containing `project.json`
- `gateway_url`: Probe `https://localhost:9043/StatusPing` then `http://localhost:8088/StatusPing` with `--connect-timeout 3` (3-second connection timeout to avoid hanging on unreachable gateways)
- `gateway_reachable`: StatusPing returned 200
- `has_perspective`: `com.inductiveautomation.perspective/` directory exists
- `has_webdev`: `com.inductiveautomation.webdev/` directory exists
- `has_scripting`: `ignition/script-python/` directory exists
- `tag_providers`: If gateway reachable, query the built-in Ignition tag browse endpoint at `${GATEWAY_URL}/system/tag-providers` (no auth required, returns JSON array of provider names). If the endpoint is unavailable (older Ignition versions), fall back to browsing `${GATEWAY_URL}/system/webdev/${PROJECT_NAME}/testing/tags?browse=providers` if the WebDev endpoint exists, otherwise return empty array
- `existing_testing`: Check for each scaffolded component

When the gateway is unreachable, `tag_providers` is an empty array and `gateway_reachable` is false. Scaffolding still proceeds — tag provider becomes a placeholder in `.env.example`.

**The skills present detection results to the user and ask them to confirm or correct the tag provider.** This is the one interactive step — everything else is automatic.

### Scaffolding Scripts

Two deterministic shell scripts that create files via heredocs. No LLM involved.

#### `scripts/scaffold-testing.sh`

**Inputs:** `--project-root`, `--project-name`, `--gateway-url`, `--tag-provider`
**Flag:** `--force` to overwrite existing files (default: skip existing)

**Creates:**

```
ignition/script-python/testing/
├── runner/
│   ├── code.py          # Test discovery and execution
│   └── resource.json    # Ignition resource descriptor
├── assertions/
│   ├── code.py          # assert_equal, assert_true, assert_raises, etc.
│   └── resource.json
├── decorators/
│   ├── code.py          # @test, @skip, @setup, @teardown, @expected_error
│   └── resource.json
├── helpers/
│   ├── code.py          # Tag read/write helpers for integration tests
│   └── resource.json
└── reporter/
    ├── code.py          # JSON, console, and JUnit XML formatters
    └── resource.json

com.inductiveautomation.webdev/resources/testing/
├── run/
│   ├── doGet.py         # GET: discover test modules
│   ├── doPost.py        # POST: run tests (module, package, or all)
│   └── config.json      # WebDev endpoint config (no auth required)
└── tags/
    ├── doGet.py         # GET: browse tags, export simulator CSV
    ├── doPost.py        # POST: read/write/mirror tags, call scripts
    └── config.json

.ignition-stubs/testing/
├── runner.pyi
├── assertions.pyi
├── decorators.pyi
├── helpers.pyi
└── reporter.pyi
```

**Key genericizations from WHK-Global:**
- Runner discovery paths are parameterized: uses `PROJECT_NAME` variable instead of hardcoded `WHK-Global`
- Runner checks both Docker path (`/usr/local/bin/ignition/data/projects/${PROJECT_NAME}/...`) and local dev path (the actual `project_root`)
- Helpers drop WHK-specific `run_process_queue` — only generic tag operations remain
- Tag endpoint's `_ensureTag` and data type inference are kept (universally useful)
- WebDev endpoints use the project name in their URL path automatically (Ignition convention)

#### `scripts/scaffold-e2e.sh`

**Inputs:** `--project-root`, `--project-name`, `--gateway-url`, `--tag-provider`, `--perspective-project`
**Flag:** `--force` to overwrite existing files

**Creates:**

```
e2e/
├── package.json              # @playwright/test, dotenv
├── tsconfig.json             # ES2022, NodeNext, path aliases
├── playwright.config.ts      # Projects: setup, chromium, api
├── .env.example              # Template with all config vars
├── .gitignore                # node_modules, test-results, .auth, .env
├── fixtures/
│   ├── auth.setup.ts         # Gateway authentication (login form detection)
│   └── perspective.ts        # Custom PerspectivePage fixture
├── helpers/
│   └── gateway-api.ts        # Tag ops, health checks, script invocation
├── pages/
│   └── PerspectivePage.ts    # Base page object for Perspective views
├── components/
│   ├── PerspectiveComponent.ts  # Base component wrapper
│   ├── Button.ts                # ia.input.button wrapper
│   └── Table.ts                 # ia.display.table wrapper
└── tests/
    └── smoke/
        └── perspective-loads.spec.ts  # Generic smoke tests
```

**Key genericizations from WHK-Global:**
- `gateway-api.ts` drops MES-specific methods (`mesLogin`, `mesGraphQL`, `changeoverGet/Post`), WMS methods (`wmsLogin`, `wmsGet/Post`), and changeover tag helpers — these are WHK business logic
- Keeps: tag read/write/mirror, script invocation, health checks, project scan trigger
- `.env.example` has `IGNITION_URL`, `IGNITION_USER`, `IGNITION_PASSWORD`, `PERSPECTIVE_PROJECT`, `TAG_PROVIDER` — no MES/WMS vars
- `playwright.config.ts` has `setup` and `chromium` projects only — no `api` project (that was WHK-specific test matching)
- Smoke tests are generic: "session loads", "page renders components", "docks exist" — no references to specific WHK views like "Mash Cooker #1" or "Changeover Dashboard"
- `PerspectivePage.ts` is kept as-is — its conventions (`data-component-path`, dock prefixes, WebSocket SPA behavior) are universal Perspective patterns
- `auth.setup.ts` is kept as-is — the login form detection (`input.username-field`, `div.submit-button`) is standard Ignition IdP

**Both scripts are idempotent.** They check for existing files before writing. With `--force`, they overwrite. Without it, they skip and report what was skipped. Both also support `--dry-run` to preview what files would be created without writing anything.

**Partial failure recovery:** If a script fails mid-execution (e.g., disk full, permission error), it leaves whatever files were successfully created. Re-running without `--force` recovers gracefully — it skips the already-created files and creates only the missing ones. The detection layer's `existing_testing` checks are granular enough to identify partial states (e.g., `jython_framework: true` but `webdev_endpoints: false`).

### Plugin Skills

Three new user-invocable skills:

#### `/ignition-scada:init-testing`

1. Run `detect-project.sh` (from project root or cwd)
2. Present findings: "Found project *{title}* at `{root}`, gateway at `{url}` ({reachable/unreachable}), tag providers: {list}"
3. Ask user to confirm or provide tag provider
4. Check `existing_testing.jython_framework` and `existing_testing.webdev_endpoints` — warn if already scaffolded, offer `--force`
5. Call `scaffold-testing.sh` with confirmed parameters
6. Report what was created
7. If gateway reachable: run test discovery endpoint to verify setup works
8. Explain how to write a first test: create `ignition/script-python/{package}/__tests__/code.py`, import decorators/assertions, write `@test` function

Supports `--all` flag: after scaffolding testing, automatically runs `init-e2e` flow if the project has Perspective.

#### `/ignition-scada:init-e2e`

1. Run `detect-project.sh`
2. Check `has_perspective` — if false, warn: "No Perspective module found. E2E tests require Perspective views. Continue anyway?"
3. Check `existing_testing.jython_framework` — if false, inform the user and automatically call `scaffold-testing.sh` with the already-confirmed parameters (no second interactive confirmation — the tag provider was already confirmed in step 4). The e2e tests depend on the WebDev `testing/tags` endpoint for tag operations.
4. Present findings, ask user to confirm tag provider
5. Auto-detect Perspective project name: check for `com.inductiveautomation.perspective/` views, or if gateway reachable, query for running Perspective projects
6. Ask user to confirm Perspective project name
7. Call `scaffold-e2e.sh` with confirmed parameters
8. Run `cd e2e && npm install && npx playwright install chromium`
9. Prompt user to set credentials: "Copy `e2e/.env.example` to `e2e/.env` and fill in `IGNITION_USER` and `IGNITION_PASSWORD`"
10. Explain auth setup: "Run `cd e2e && npx playwright test --project=setup` to authenticate, then `npm test` to run smoke tests"

#### `/ignition-scada:test`

Routes based on arguments. Detects project context automatically.

| Invocation | Action |
|------------|--------|
| `/ignition-scada:test` | Run all gateway Jython tests |
| `/ignition-scada:test {short-name}` | Translate to `{package}.{name}.__tests__` and run that module |
| `/ignition-scada:test {dotted.path}` | Run as module or package filter |
| `/ignition-scada:test ui` or `e2e` | Run all Playwright tests |
| `/ignition-scada:test ui {area}` | Run `e2e/tests/{area}/` |
| `/ignition-scada:test smoke` | Run `e2e/tests/smoke/` |

All test invocations:
1. Trigger a gateway project scan first (to pick up recent file changes)
2. Poll for scan completion: hit `StatusPing` up to 5 times at 1-second intervals (max 5s wait). This replaces the hardcoded 3-second sleep — faster for small projects, more reliable for large ones. If polling times out, proceed anyway (tests may use stale scripts but won't fail to run)
3. Run the tests
4. Parse and present results (summary + failure details)
5. On missing infrastructure, suggest the appropriate init skill

### Hook Scripts

Two new hook scripts in `scripts/`, plus the existing `ignition-lint.sh`:

#### `scripts/run-tests.sh` — Post-commit gateway tests

- **Trigger:** `PostToolUse` on `Bash` — filters for `git commit` commands
- **Command matching:** Reads `tool_input.command` from hook JSON. Matches if the command string contains `git commit` (simple substring match via `[[ "$COMMAND" =~ "git commit" ]]`). This intentionally matches `git commit -m`, `git commit --amend`, etc. Also checks `tool_result.stdout` for commit success indicators (`file changed`, `insertions`, `deletions`, or branch ref like `[main abc1234]`) to avoid running tests on failed commits.
- **Detection:** Walks up from cwd to find `project.json`, derives project name from directory
- **Gateway URL:** Reads from `$IGNITION_GATEWAY_URL` env var, or `.env` in project root, or falls back to `https://localhost:9043`
- **API token:** Reads from `$IGNITION_API_TOKEN_FILE` env var (no hardcoded path). Used for project scan trigger only. If no token file is set, scan trigger is skipped (tests still run against whatever scripts the gateway has loaded).
- **Flow:** Probe gateway (3s connect timeout) → trigger scan → poll for completion (max 5s) → POST to `testing/run` → parse results → report summary to stderr
- **Silent exit if:** Gateway unreachable, endpoint doesn't exist, commit failed, not in an Ignition project

#### `scripts/run-ui-tests.sh` — Post-edit Playwright tests

- **Trigger:** `PostToolUse` on `Edit|Write` — filters for `*/view.json` under Perspective views
- **Detection:** Finds `e2e/` relative to project root (not hardcoded path)
- **Scoping:** Extracts view area from path (`views/{Area}/...`) → maps to `e2e/tests/{area}/`
- **Fallback:** If no matching test directory, runs `e2e/tests/smoke/`
- **Concurrency guard:** Uses a lockfile (`e2e/.playwright-running.lock`) with `flock` to prevent concurrent Playwright runs. If another test run is in progress, the hook silently exits. The lockfile is removed on completion (or by trap on exit).
- **Silent exit if:** `e2e/node_modules` doesn't exist, `.auth/user.json` doesn't exist, another test run is in progress, not a Perspective view.json

**Performance note:** The self-gating check for `run-ui-tests.sh` is cheap — it reads `tool_input.file_path` from stdin, does a string match on `view.json`, checks two filesystem paths, and exits. This runs on every `Edit|Write` alongside `ignition-lint.sh`, but the early-exit path is ~5ms. The Playwright launch only happens for actual Perspective view edits.

#### Self-gating design

All hooks are registered at the plugin level in `hooks/hooks.json`. They fire on every matching tool use across all projects. Each hook self-gates:

1. Check if we're in an Ignition project (walk up for `project.json`)
2. Check if the relevant infrastructure exists (testing endpoint, e2e directory)
3. If either check fails, `exit 0` silently

This means installing the plugin is safe before running any init skills. The hooks are dormant until the test infrastructure is scaffolded.

### Updated `hooks/hooks.json`

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

### Final Plugin Structure

```
claude-code-plugin/
├── .claude-plugin/
│   └── plugin.json                    # v0.2.0
├── hooks/
│   └── hooks.json                     # 3 hooks: lint, gateway tests, UI tests
├── scripts/
│   ├── detect-project.sh              # NEW — auto-detection (shared)
│   ├── scaffold-testing.sh            # NEW — Jython + WebDev scaffolding
│   ├── scaffold-e2e.sh               # NEW — Playwright scaffolding
│   ├── ignition-lint.sh              # EXISTING — auto-lint on edit
│   ├── run-tests.sh                  # NEW — post-commit gateway tests
│   └── run-ui-tests.sh              # NEW — post-edit Playwright tests
├── skills/
│   ├── ignition-api/SKILL.md         # EXISTING — system.* API reference
│   ├── ignition-expressions/SKILL.md # EXISTING — expression language
│   ├── ignition-lint/SKILL.md        # EXISTING — manual lint
│   ├── init-testing/SKILL.md         # NEW — scaffold Jython + WebDev
│   ├── init-e2e/SKILL.md            # NEW — scaffold Playwright
│   └── test/SKILL.md                # NEW — run tests
└── README.md                         # Updated with testing docs
```

### Authentication Model

Three auth contexts exist in this system, each appropriate for its use case:

| Context | Auth method | Why |
|---------|------------|-----|
| **WebDev test endpoints** (`testing/run`, `testing/tags`) | No auth (`require-auth: false` in config.json) | These are developer-only endpoints on a local/dev gateway. They read/write tags and run scripts — capabilities that any authenticated Designer user already has. Requiring auth would add friction with no security benefit in dev. **Production gateways should never have these endpoints deployed.** |
| **Gateway project scan** (triggered by hooks) | API token via `$IGNITION_API_TOKEN_FILE` | The scan endpoint is a custom WebDev endpoint that triggers Ignition's project resource reload. Token auth prevents accidental scans from unauthorized sources. Optional — hooks skip the scan if no token is configured. |
| **Playwright e2e tests** | Username/password in `e2e/.env` | Playwright authenticates through the Perspective login form (same as a real user). Credentials are stored in `.env` (gitignored) and persisted to `.auth/user.json` by the auth setup fixture. |

The `.env` file is gitignored by the scaffolded `e2e/.gitignore`. The auth state file `.auth/user.json` is also gitignored.

### Version Control Guidance

All scaffolded files should be committed to version control:
- `ignition/script-python/testing/` — these are Ignition project resources, same as any other script module
- `com.inductiveautomation.webdev/resources/testing/` — WebDev endpoints are project resources
- `.ignition-stubs/testing/` — type stubs for IDE support
- `e2e/` — test infrastructure (minus `node_modules/`, `test-results/`, `.auth/`, `.env`, which are in `.gitignore`)

### Platform Support

The plugin targets **macOS and Linux**. All scripts are bash. Windows users should use WSL, which is the standard recommendation for Claude Code on Windows. The detection and scaffolding scripts use POSIX-compatible utilities (`curl`, `jq`, `mkdir`, `cat`) that are available in all bash environments.

### What the Plugin Does NOT Scaffold

Business-logic test modules. The framework gives you `testing.*` and the endpoints. Writing actual tests (`core.mes.changeover.__tests__/code.py`) is the developer's job — the plugin just makes it easy to get started.

Project-specific page objects. `PerspectivePage.ts` is the base. Specific page objects like `ChangeoverDashboard.ts` are project-specific and written by the developer as they build views.

MES/WMS/domain-specific API helpers. The `gateway-api.ts` provides tag ops, script calls, and health checks. Domain integrations (GraphQL, REST APIs, OAuth flows) are added per-project.

## Testing the Plugin Itself

The scaffolding scripts can be tested by running them against a temp directory and validating the output file tree. No gateway needed — just check that the right files are created with the right content substitutions.

The hook scripts can be tested by piping them mock JSON input (simulating Claude Code's hook protocol) and checking exit codes + stderr output.

## Migration Path for WHK-Global

Once the plugin ships, WHK-Global can:

1. Install the plugin (`claude plugin add`)
2. Delete per-project hook scripts:
   - `rm .claude/hooks/ignition-lint.sh` (replaced by plugin `scripts/ignition-lint.sh`)
   - `rm .claude/hooks/run-tests.sh` (replaced by plugin `scripts/run-tests.sh`)
   - `rm .claude/hooks/run-ui-tests.sh` (replaced by plugin `scripts/run-ui-tests.sh`)
3. Delete per-project command:
   - `rm .claude/commands/test.md` (replaced by plugin `/ignition-scada:test` skill)
4. Clean up `.claude/settings.json` — remove the entire `hooks` section (plugin hooks handle it):
   ```diff
   - "hooks": { "PostToolUse": [...] }
   ```
5. Set environment variables (or add to `.env`):
   - `IGNITION_API_TOKEN_FILE=~/whiskeyhouse/whk-services-deployments/secrets/IGNITION_API_TOKEN`
6. Keep everything else — project-specific test modules (`core/mes/changeover/__tests__/`), page objects (`ChangeoverDashboard.ts`), domain API helpers (MES/WMS methods in `gateway-api.ts`), and the existing `testing/` framework files are all project-specific and remain unchanged
