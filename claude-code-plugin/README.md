# Ignition SCADA — Claude Code Plugin

A Claude Code plugin that gives Claude full domain awareness when working on Ignition SCADA projects. Includes auto-linting, the complete `system.*` API reference (14 modules, 239 functions), the expression language catalog (104 functions), and automated test scaffolding for both Jython gateway tests and Playwright e2e tests.

## What It Does

| Feature | Description |
|---------|-------------|
| **Auto-lint hook** | Runs `ignition-lint` after every Write/Edit on `.py`, `view.json`, and `tags.json` files. Diagnostics are fed back to Claude so it fixes issues immediately. |
| **API reference** | Claude knows every `system.*` function — completions, conventions, anti-patterns — without you having to explain the API. |
| **Expression language** | Claude understands Ignition's expression syntax (NOT Python) and all 104 built-in functions. |
| **Manual lint skill** | Run `/ignition-scada:ignition-lint` to lint specific files or the whole project on demand. |
| **Test scaffolding** | `/ignition-scada:init-testing` scaffolds a Jython test framework (runner, assertions, decorators) + WebDev endpoints + type stubs. `/ignition-scada:init-e2e` adds Playwright browser tests. |
| **Test runner** | `/ignition-scada:test` runs gateway Jython tests or Playwright e2e tests with smart routing. |
| **Auto-test hooks** | After `git commit`, runs gateway tests automatically. After editing a `view.json`, runs scoped Playwright tests. |

## Install

```bash
claude plugin add --from whiskeyhouse/ignition-nvim --path claude-code-plugin
```

Or from a local clone:

```bash
claude plugin add --from /path/to/ignition-nvim/claude-code-plugin
```

## Prerequisites

The auto-lint hook requires [`ignition-lint`](https://pypi.org/project/ignition-lint-toolkit/):

```bash
pip install ignition-lint-toolkit
```

If `ignition-lint` is not installed, the hook silently exits — nothing breaks.

The hook also requires `jq` for JSON parsing (pre-installed on most systems).

## How It Works

### Auto-Lint Hook

After every Write or Edit, the hook checks if the file is inside an Ignition project (walks up from the file looking for `project.json`). If it is:

- `.py` files are linted with the `scripts-only` profile
- `view.json` files are linted with the `perspective-only` profile
- `tags.json` files are linted with the `full` profile

Any issues are returned as structured JSON, which Claude reads and acts on — typically fixing the issue in its next edit.

Files outside Ignition projects are ignored. The hook is safe for global install.

### Skills

Six skills are bundled:

| Skill | Invocable? | Purpose |
|-------|-----------|---------|
| `ignition-api` | Claude-only | Loaded automatically when Claude writes Ignition scripts. Provides Jython conventions, all `system.*` modules, common patterns, and anti-patterns. |
| `ignition-expressions` | Claude-only | Loaded automatically when Claude writes expression bindings. All 104 functions with signatures, descriptions, and usage tips. |
| `ignition-lint` | User + Claude | Run `/ignition-scada:ignition-lint` to lint files or the project. Claude explains diagnostics and applies fixes. |
| `init-testing` | User + Claude | Run `/ignition-scada:init-testing` to scaffold the Jython test framework, WebDev endpoints, and type stubs. Use `--all` to also scaffold e2e tests. |
| `init-e2e` | User + Claude | Run `/ignition-scada:init-e2e` to scaffold Playwright browser tests for Perspective views. |
| `test` | User + Claude | Run `/ignition-scada:test` to run gateway or e2e tests. Routes based on arguments. |

Claude-only skills are never shown in the `/` menu — they're background knowledge that Claude draws on when relevant.

## Plugin vs Templates

This repo offers two ways to give Claude Ignition awareness:

| | Plugin (`claude-code-plugin/`) | Templates (`templates/`) |
|--|------|-----------|
| **Scope** | Global — works across all your Ignition projects | Per-project — files live in your project repo |
| **Install** | `claude plugin add` once | Copy files or run `setup.sh` per project |
| **Updates** | `claude plugin update` | Re-run setup or manually copy |
| **Best for** | Developers who work on multiple Ignition projects | Teams who want the config checked into their project |

Both approaches include the same lint hook and the same domain knowledge. The plugin packages it as a reusable install; the templates embed it directly.

## Quick Start — Testing

```bash
# Scaffold the Jython test framework + WebDev endpoints
/ignition-scada:init-testing

# Also scaffold Playwright e2e tests (requires Perspective module)
/ignition-scada:init-testing --all

# Run tests
/ignition-scada:test                    # All gateway Jython tests
/ignition-scada:test changeover         # Specific module
/ignition-scada:test ui                 # All Playwright tests
/ignition-scada:test smoke              # Smoke tests only
```

### Deterministic Mode

The scaffolding scripts can be run directly without Claude:

```bash
# Detect project
./scripts/detect-project.sh /path/to/project

# Scaffold testing
./scripts/scaffold-testing.sh \
  --project-root /path/to/project \
  --project-name MyProject \
  --gateway-url https://localhost:9043 \
  --tag-provider MYP01

# Scaffold e2e
./scripts/scaffold-e2e.sh \
  --project-root /path/to/project \
  --project-name MyProject \
  --gateway-url https://localhost:9043 \
  --tag-provider MYP01 \
  --perspective-project QSI_MyProject
```

Both scripts support `--dry-run` to preview and `--force` to overwrite existing files.

### What Gets Scaffolded

**`/ignition-scada:init-testing`** creates:
- `ignition/script-python/testing/` — 5 modules (runner, assertions, decorators, helpers, reporter)
- `com.inductiveautomation.webdev/resources/testing/` — 2 endpoints (run, tags)
- `.ignition-stubs/testing/` — type stubs for IDE completion

**`/ignition-scada:init-e2e`** creates:
- `e2e/` — Playwright config, auth fixtures, gateway API helper, page objects, component wrappers, smoke tests

### Testing Prerequisites

- **Gateway tests:** A running Ignition gateway (local or Docker)
- **E2E tests:** Node.js, Chromium (installed automatically by Playwright)
- **Both:** `jq` for the detection script (pre-installed on most systems)

## File Structure

```
claude-code-plugin/
  .claude-plugin/
    plugin.json               # Plugin manifest (name, version, entry points)
  hooks/
    hooks.json                # PostToolUse hooks (lint, gateway tests, UI tests)
  scripts/
    detect-project.sh         # Auto-detect project structure and gateway state
    scaffold-testing.sh       # Scaffold Jython test framework + WebDev endpoints
    scaffold-e2e.sh           # Scaffold Playwright e2e test setup
    ignition-lint.sh          # Lint hook script (finds project.json, runs linter)
    run-tests.sh              # Post-commit gateway test hook
    run-ui-tests.sh           # Post-edit Playwright test hook
  skills/
    ignition-api/SKILL.md         # system.* API reference (Claude-only)
    ignition-expressions/SKILL.md # Expression language reference (Claude-only)
    ignition-lint/SKILL.md        # Manual lint skill (user-invocable)
    init-testing/SKILL.md         # Test framework scaffolding (user-invocable)
    init-e2e/SKILL.md             # E2E test scaffolding (user-invocable)
    test/SKILL.md                 # Test runner (user-invocable)
```

## Diagnostic Codes

The hook and lint skill report issues using these codes. See the [ignition-lint docs](https://pypi.org/project/ignition-lint-toolkit/) for full details.

**Script:** `JYTHON_SYNTAX_ERROR`, `JYTHON_PRINT_STATEMENT`, `JYTHON_IMPORT_STAR`, `IGNITION_UNKNOWN_SYSTEM_CALL`, `IGNITION_SYSTEM_OVERRIDE`, `LONG_LINE`, `MISSING_DOCSTRING`

**Expression:** `EXPR_NOW_DEFAULT_POLLING`, `EXPR_NOW_LOW_POLLING`, `EXPR_UNKNOWN_FUNCTION`, `EXPR_BAD_COMPONENT_REF`

**Perspective:** `EMPTY_COMPONENT_NAME`, `GENERIC_COMPONENT_NAME`, `MISSING_TAG_PATH`, `MISSING_EXPRESSION`, `INVALID_BINDING_TYPE`

**Tag:** `INVALID_TAG_TYPE`, `MISSING_DATA_TYPE`, `MISSING_VALUE_SOURCE`, `OPC_MISSING_CONFIG`
