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

Eight skills are bundled:

| Skill | Invocable? | Purpose |
|-------|-----------|---------|
| `ignition-api` | Claude-only | Jython conventions, all `system.*` modules, Ignition resource structure (`resource.json`), script library rules. |
| `ignition-expressions` | Claude-only | Expression language syntax and all 104 built-in functions. |
| `ignition-testing` | Claude-only | Test framework reference — `testing.*` modules, decorators, assertions, WebDev endpoints, discovery conventions. |
| `ignition-e2e` | Claude-only | Playwright reference — Perspective DOM conventions, PerspectivePage, component wrappers, gateway API helper. |
| `ignition-lint` | User + Claude | `/ignition-scada:ignition-lint` — lint files or the whole project on demand. |
| `init-testing` | User + Claude | `/ignition-scada:init-testing` — scaffold Jython test framework + WebDev endpoints + type stubs. |
| `init-e2e` | User + Claude | `/ignition-scada:init-e2e` — scaffold Playwright browser tests for Perspective views. |
| `test` | User + Claude | `/ignition-scada:test` — run gateway Jython tests or Playwright browser tests. |

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

Two commands to go from zero to a full test suite:

```
/ignition-scada:init-testing    # Gateway Jython tests
/ignition-scada:init-e2e        # Playwright browser tests (Perspective)
```

### What happens when you run `/ignition-scada:init-testing`

The plugin auto-detects your project — name, gateway, tag providers, parent project inheritance — and scaffolds everything you need:

```
❯ /ignition-scada:init-testing

⏺ Here's what I found:

  ┌────────────┬──────────────────────────────────────────────┐
  │  Property  │                    Value                     │
  ├────────────┼──────────────────────────────────────────────┤
  │ Project    │ My Site HMI (MySite01)                       │
  ├────────────┼──────────────────────────────────────────────┤
  │ Gateway    │ https://localhost:9043 (reachable)            │
  ├────────────┼──────────────────────────────────────────────┤
  │ Parent     │ Global (has Jython framework + WebDev)        │
  ├────────────┼──────────────────────────────────────────────┤
  │ Tag provs  │ SITE01, default, QSI_UDTs                    │
  └────────────┴──────────────────────────────────────────────┘

  Inherited from parent (NOT created here):
  The Jython test framework lives in Global and is inherited
  automatically. Any __tests__ modules you write will be
  discovered alongside the parent's tests.

  Created here (project-scoped, NOT inherited):
  - WebDev endpoints (testing/run, testing/tags)
  - Type stubs (.ignition-stubs/testing/)

⏺ Which tag provider? → SITE01

⏺ Scaffold complete: 14 created, 0 skipped.

⏺ Gateway discovered 11 test modules:
  core.mes.changeover.__tests__, core.util.__tests__, ...

  Writing your first test:
  ignition/script-python/<package>/__tests__/code.py
```

It understands Ignition project inheritance — if your parent project already has the test framework, it skips duplicating scripts and only creates what each project actually needs (WebDev endpoints are project-scoped in Ignition).

### What happens when you run `/ignition-scada:init-e2e`

Scaffolds Playwright browser tests with Perspective-aware page objects, then authenticates and runs smoke tests:

```
❯ /ignition-scada:init-e2e

⏺ Perspective module found. Parent project has e2e/.env — copying
  credentials and updating project name.

⏺ Scaffold done: 13 files created.

⏺ Installing dependencies...
  npm install ✓
  playwright install chromium ✓

❯ Yes, run the auth setup and smoke tests

⏺ ✓ authenticate (4.6s)
  ✓ session loads and docks render (2.8s)
  ✓ page content renders (2.7s)
  ✓ navigation exists in DOM (3.9s)

  4 passed, 0 failed (19s total)
```

### Running tests

```bash
/ignition-scada:test                    # All gateway Jython tests
/ignition-scada:test changeover         # Specific module
/ignition-scada:test core.mes           # By package prefix
/ignition-scada:test ui                 # All Playwright browser tests
/ignition-scada:test ui smoke           # Playwright smoke tests only
```

### What gets scaffolded

**`/ignition-scada:init-testing`** creates:
- `ignition/script-python/testing/` — 5 modules (runner, assertions, decorators, helpers, reporter) — *skipped if inherited from parent*
- `com.inductiveautomation.webdev/resources/testing/` — 2 endpoints (run, tags) — *always created, not inherited*
- `.ignition-stubs/testing/` — type stubs for IDE completion

**`/ignition-scada:init-e2e`** creates:
- `e2e/` — Playwright config, auth fixtures, gateway API helper, PerspectivePage page object, component wrappers (Button, Table), smoke tests

### Deterministic mode (no Claude)

The scaffolding scripts can be run directly:

```bash
./scripts/detect-project.sh /path/to/project
./scripts/scaffold-testing.sh --project-root /path/to/project --project-name MySite --tag-provider SITE01
./scripts/scaffold-e2e.sh --project-root /path/to/project --project-name MySite --tag-provider SITE01 --perspective-project MySite01
```

Both support `--dry-run` to preview and `--force` to overwrite. Use `--skip-scripts` if the parent project has the Jython framework.

### Prerequisites

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
    ignition-api/SKILL.md         # system.* API + resource structure (Claude-only)
    ignition-expressions/SKILL.md # Expression language reference (Claude-only)
    ignition-testing/SKILL.md     # Test framework reference (Claude-only)
    ignition-e2e/SKILL.md         # Playwright/Perspective reference (Claude-only)
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
