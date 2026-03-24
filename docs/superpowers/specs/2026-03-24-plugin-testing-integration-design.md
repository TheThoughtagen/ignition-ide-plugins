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
- `gateway_url`: Probe `https://localhost:9043/StatusPing`, fall back to `http://localhost:8088/StatusPing`
- `gateway_reachable`: StatusPing returned 200
- `has_perspective`: `com.inductiveautomation.perspective/` directory exists
- `has_webdev`: `com.inductiveautomation.webdev/` directory exists
- `has_scripting`: `ignition/script-python/` directory exists
- `tag_providers`: If gateway reachable, query tag browse endpoint for provider list
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

**Both scripts are idempotent.** They check for existing files before writing. With `--force`, they overwrite. Without it, they skip and report what was skipped.

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
3. Check `existing_testing.jython_framework` — if false, run `init-testing` first (the e2e tests depend on the gateway API endpoint for tag operations and project scanning)
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
2. Wait 3 seconds for propagation
3. Run the tests
4. Parse and present results (summary + failure details)
5. On missing infrastructure, suggest the appropriate init skill

### Hook Scripts

Two new hook scripts in `scripts/`, plus the existing `ignition-lint.sh`:

#### `scripts/run-tests.sh` — Post-commit gateway tests

- **Trigger:** `PostToolUse` on `Bash` — filters for `git commit` commands
- **Detection:** Walks up from cwd to find `project.json`, derives project name from directory
- **Gateway URL:** Reads from `$IGNITION_GATEWAY_URL` env var, or `.env` in project root, or falls back to `https://localhost:9043`
- **API token:** Reads from `$IGNITION_API_TOKEN_FILE` env var (no hardcoded path)
- **Flow:** Probe gateway → trigger scan → wait 3s → POST to `testing/run` → parse results → report summary to stderr
- **Silent exit if:** Gateway unreachable, endpoint doesn't exist, commit failed

#### `scripts/run-ui-tests.sh` — Post-edit Playwright tests

- **Trigger:** `PostToolUse` on `Edit|Write` — filters for `*/view.json` under Perspective views
- **Detection:** Finds `e2e/` relative to project root (not hardcoded path)
- **Scoping:** Extracts view area from path (`views/{Area}/...`) → maps to `e2e/tests/{area}/`
- **Fallback:** If no matching test directory, runs `e2e/tests/smoke/`
- **Silent exit if:** `e2e/node_modules` doesn't exist, `.auth/user.json` doesn't exist

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

### What the Plugin Does NOT Scaffold

Business-logic test modules. The framework gives you `testing.*` and the endpoints. Writing actual tests (`core.mes.changeover.__tests__/code.py`) is the developer's job — the plugin just makes it easy to get started.

Project-specific page objects. `PerspectivePage.ts` is the base. Specific page objects like `ChangeoverDashboard.ts` are project-specific and written by the developer as they build views.

MES/WMS/domain-specific API helpers. The `gateway-api.ts` provides tag ops, script calls, and health checks. Domain integrations (GraphQL, REST APIs, OAuth flows) are added per-project.

## Testing the Plugin Itself

The scaffolding scripts can be tested by running them against a temp directory and validating the output file tree. No gateway needed — just check that the right files are created with the right content substitutions.

The hook scripts can be tested by piping them mock JSON input (simulating Claude Code's hook protocol) and checking exit codes + stderr output.

## Migration Path for WHK-Global

Once the plugin ships, WHK-Global can:
1. Install the plugin
2. Delete `.claude/hooks/ignition-lint.sh`, `run-tests.sh`, `run-ui-tests.sh` (plugin hooks replace them)
3. Delete `.claude/commands/test.md` (plugin `/ignition-scada:test` replaces it)
4. Keep project-specific test modules, page objects, and domain helpers (those aren't in the plugin)
5. Keep `.claude/settings.json` hooks section can be cleaned up (plugin hooks handle it)
