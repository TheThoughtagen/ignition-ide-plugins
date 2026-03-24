---
sidebar_position: 3
---

# Skills Reference

The Claude Code plugin bundles 8 skills: 4 Claude-only (background knowledge) and 4 user-invocable (available from the `/` menu).

## Claude-Only Skills

These skills are never shown in the `/` menu. Claude loads them automatically when the context is relevant — you don't need to invoke them.

### ignition-api

**Teaches Claude:** The complete Ignition `system.*` scripting API.

Claude learns:
- All 14 `system.*` modules with 239 functions, including signatures and return types
- Jython 2.7 conventions: `print()` function form, no f-strings, no type hints, Java class imports
- `resource.json` requirements — every file in an Ignition project needs one, and the `files` array must list every file the gateway should load
- Script library structure: leaf modules (have `code.py`) vs package nodes (have child directories, no `code.py`)
- Common patterns: parameterized queries, tag reads, dataset iteration, logging
- Anti-patterns: string-formatted SQL, `import *`, hardcoded gateway URLs, shadowing `system`

### ignition-expressions

**Teaches Claude:** The Ignition expression language (NOT Python).

Claude learns:
- All 104 built-in functions across 10 categories: math (12), string (24), date/time (16), logic (8), type casting (7), dataset (10), JSON (8), tag quality (7), color (2), advanced (10)
- Expression syntax: `if({[.]value} > 100, "High", "Normal")`
- Property references: `{this.props.value}`, `{view.custom.x}`, `{view.params.x}`
- Key rules: `now()` defaults to 1-second polling (always specify rate), `runScript()` for calling project scripts from expressions
- Common mistakes: confusing expression syntax with Python

### ignition-testing

**Teaches Claude:** The Jython test framework reference.

Claude learns:
- All `testing.*` modules: runner, assertions, decorators, helpers, reporter
- Test discovery convention: `__tests__/code.py` inside the package being tested
- Decorator usage: `@test`, `@skip(reason)`, `@setup`, `@teardown`, `@expected_error(ExceptionType)`
- All 11 assertion functions with signatures
- WebDev endpoint API: `testing/run` (discover, execute, format options) and `testing/tags` (read, write, script invocation, delete)
- Project inheritance: framework inherited from parent, WebDev endpoints always project-scoped
- Runner discovery: how the filesystem walk works, what to do when child project tests are not discovered
- `resource.json` is required for every test module — the number one cause of test discovery failures

### ignition-e2e

**Teaches Claude:** Playwright testing for Perspective views.

Claude learns:
- Perspective DOM conventions: `data-component-path` (positional indices with `C`, `L[n]`, `T[n]` prefixes), `data-component` type attributes
- PerspectivePage page object: `openPage()`, `waitForPageContent()`, `componentByType()`, `pageLabelWithText()`, `dismissPopups()`
- Component wrappers: Button (`click()`, `isEnabled()`), Table (`waitForData()`, `getRowCount()`, `getCellText()`)
- Gateway API helper: `readTags()`, `writeTags()`, `callScript()`, `mirrorTags()`, `isGatewayReachable()`
- Auth fixture: auto-login, session persistence to `.auth/user.json`, credential handling via environment variables
- Critical rules: never use `page.goto()` after initial session open, left dock is `onDemand`, embedded views reset path counters

---

## User-Invocable Skills

These skills appear in the `/` menu and can be invoked directly.

### ignition-lint

**Usage:** `/ignition-scada:ignition-lint [file|directory|profile]`

Runs `ignition-lint` to validate Ignition project files. The linter checks Jython scripts, Perspective views, tag definitions, and expression bindings.

**Arguments:**
- A file or directory path — lint that specific target
- A profile name — use that profile on the project
- Empty — lint the whole project with the `default` profile

**Profiles:** `default`, `full`, `scripts-only`, `perspective-only`, `naming-only`

**Examples:**

```bash
/ignition-scada:ignition-lint
/ignition-scada:ignition-lint scripts-only
/ignition-scada:ignition-lint ignition/script-python/core/util/code.py
```

**Diagnostic codes:**

| Category | Codes |
|----------|-------|
| Script | `JYTHON_SYNTAX_ERROR`, `JYTHON_PRINT_STATEMENT`, `JYTHON_IMPORT_STAR`, `JYTHON_DEPRECATED_ITERITEMS`, `JYTHON_MIXED_INDENTATION`, `JYTHON_BAD_COMPONENT_REF`, `JYTHON_HARDCODED_LOCALHOST`, `JYTHON_HTTP_WITHOUT_EXCEPTION_HANDLING`, `IGNITION_SYSTEM_OVERRIDE`, `IGNITION_HARDCODED_GATEWAY`, `IGNITION_HARDCODED_DB`, `IGNITION_DEBUG_PRINT`, `IGNITION_UNKNOWN_SYSTEM_CALL`, `LONG_LINE`, `MISSING_DOCSTRING` |
| Expression | `EXPR_NOW_DEFAULT_POLLING`, `EXPR_NOW_LOW_POLLING`, `EXPR_UNKNOWN_FUNCTION`, `EXPR_INVALID_PROPERTY_REF`, `EXPR_BAD_COMPONENT_REF` |
| Perspective | `EMPTY_COMPONENT_NAME`, `GENERIC_COMPONENT_NAME`, `MISSING_TAG_PATH`, `MISSING_TAG_FALLBACK`, `MISSING_EXPRESSION`, `INVALID_BINDING_TYPE`, `UNUSED_CUSTOM_PROPERTY`, `UNUSED_PARAM_PROPERTY`, `PERFORMANCE_CONSIDERATION`, `ACCESSIBILITY_LABELING` |
| Tag | `INVALID_TAG_TYPE`, `MISSING_DATA_TYPE`, `MISSING_VALUE_SOURCE`, `MISSING_TYPE_ID`, `OPC_MISSING_CONFIG`, `EXPR_MISSING_EXPRESSION`, `HISTORY_NO_PROVIDER` |

**Prerequisite:** `pip install ignition-lint-toolkit`

### init-testing

**Usage:** `/ignition-scada:init-testing [--all] [--force]`

Scaffolds the Jython test framework, WebDev test endpoints, and type stubs into the current Ignition project.

**What it creates:**

| Component | Path | Inherited? |
|-----------|------|-----------|
| Test runner | `ignition/script-python/testing/runner/` | Yes (from parent) |
| Assertions | `ignition/script-python/testing/assertions/` | Yes |
| Decorators | `ignition/script-python/testing/decorators/` | Yes |
| Helpers | `ignition/script-python/testing/helpers/` | Yes |
| Reporter | `ignition/script-python/testing/reporter/` | Yes |
| Run endpoint | `com.inductiveautomation.webdev/resources/testing/run/` | No (project-scoped) |
| Tags endpoint | `com.inductiveautomation.webdev/resources/testing/tags/` | No (project-scoped) |
| Type stubs | `.ignition-stubs/testing/` | N/A (local files) |

**Flags:**
- `--all` — After completing test setup, automatically proceed to scaffold e2e tests (if Perspective is detected)
- `--force` — Overwrite existing files

**Flow:**
1. Runs `detect-project.sh` to discover project context
2. Presents findings (project name, gateway, parent, tag providers)
3. Asks user to confirm tag provider
4. Checks for project inheritance — skips framework modules if parent has them
5. Runs `scaffold-testing.sh`
6. Verifies setup by hitting the discovery endpoint (if gateway is reachable)
7. Explains how to write the first test

### init-e2e

**Usage:** `/ignition-scada:init-e2e [--force]`

Scaffolds Playwright browser tests for Perspective views.

**What it creates:**

| Component | Path |
|-----------|------|
| Playwright config | `e2e/playwright.config.ts` |
| Auth fixture | `e2e/fixtures/auth.setup.ts` |
| Perspective fixture | `e2e/fixtures/perspective.ts` |
| PerspectivePage | `e2e/pages/PerspectivePage.ts` |
| Component base class | `e2e/components/PerspectiveComponent.ts` |
| Button wrapper | `e2e/components/Button.ts` |
| Table wrapper | `e2e/components/Table.ts` |
| Gateway API helper | `e2e/helpers/gateway-api.ts` |
| Smoke tests | `e2e/tests/smoke/*.spec.ts` |
| Environment template | `e2e/.env.example` |
| Package config | `e2e/package.json`, `e2e/tsconfig.json` |
| Git ignore | `e2e/.gitignore` |

**Flags:**
- `--force` — Overwrite existing files

**Flow:**
1. Runs `detect-project.sh`
2. Checks for Perspective module (`com.inductiveautomation.perspective/`)
3. If Jython test framework is not set up, scaffolds it first (the gateway API helper depends on `testing/tags`)
4. Runs `scaffold-e2e.sh`
5. Installs dependencies (`npm install`, `playwright install chromium`)
6. Sets up `.env` (copies from parent if available, otherwise uses template)
7. Explains auth setup and how to run smoke tests

**Prerequisite:** Node.js must be installed. Chromium is installed automatically by Playwright.

### test

**Usage:** `/ignition-scada:test [module|package|ui|e2e|smoke]`

Runs gateway Jython tests or Playwright browser tests. Default is always gateway tests.

**Routing table:**

| Argument | Action |
|----------|--------|
| *(empty)* | Run all gateway Jython tests |
| `<short-name>` (e.g., `changeover`) | Find matching module, run gateway test |
| `<dotted.path>` (e.g., `core.mes`) | Run as package filter for gateway tests |
| `ui` or `e2e` | Run all Playwright browser tests |
| `ui <area>` (e.g., `ui changeover`) | Run Playwright tests in `e2e/tests/<area>/` |
| `ui smoke` | Run Playwright smoke tests |
| `smoke` | Run gateway tests (NOT Playwright — "smoke" without `ui` prefix means gateway) |

**Ambiguity rule:** If the user says "run tests", "test it", or any unqualified test request, the skill always defaults to gateway Jython tests. Playwright is only used when explicitly requested with `ui`, `e2e`, `browser`, or `playwright`.

**Examples:**

```bash
/ignition-scada:test                    # All gateway tests
/ignition-scada:test changeover         # Gateway tests for changeover module
/ignition-scada:test core.mes           # Gateway tests for core.mes package
/ignition-scada:test ui                 # All Playwright tests
/ignition-scada:test ui smoke           # Playwright smoke tests
/ignition-scada:test ui changeover      # Playwright tests for changeover area
```
