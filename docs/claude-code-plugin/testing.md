---
sidebar_position: 2
---

# Testing

The Claude Code plugin provides a complete testing story for Ignition projects: a Jython test framework that runs on the gateway with full access to `system.*` APIs, real tags, and database connections, plus Playwright browser tests for Perspective views. Two commands get you from zero to a full test suite.

```bash
/ignition-scada:init-testing    # Gateway Jython tests
/ignition-scada:init-e2e        # Playwright browser tests (Perspective)
```

## Gateway Jython Tests

### What the Framework Provides

The Jython test framework is a set of script library modules that run inside the Ignition gateway. It consists of five modules:

| Module | Purpose |
|--------|---------|
| `testing.runner` | Discovers `__tests__` modules by walking the filesystem, imports them, executes `@test`-decorated functions |
| `testing.assertions` | 11 assertion functions that raise `TestAssertionError` with structured `actual`/`expected` attributes |
| `testing.decorators` | `@test`, `@skip`, `@setup`, `@teardown`, `@expected_error` |
| `testing.helpers` | Utility functions for tag setup/teardown (DataSet writing, tag reconfiguration) |
| `testing.reporter` | Output formatting — JSON, console text, JUnit XML |

Plus two WebDev endpoints:

| Endpoint | Purpose |
|----------|---------|
| `testing/run` | HTTP API for test discovery and execution (GET for discover, POST to run) |
| `testing/tags` | HTTP API for tag read/write/delete and script invocation from external tools |

### How to Scaffold

Run the init-testing skill:

```bash
/ignition-scada:init-testing
```

The plugin auto-detects your project — name, gateway, tag providers, parent project inheritance — and scaffolds everything:

```text
> /ignition-scada:init-testing

  Here's what I found:

  Property    Value
  ----------  ------------------------------------------
  Project     My Site HMI (MySiteHMI)
  Gateway     https://localhost:9043 (reachable)
  Parent      Global (has Jython framework + WebDev)
  Tag provs   SITE01, default

  Inherited from parent (NOT created here):
  The Jython test framework lives in Global and is inherited
  automatically. Any __tests__ modules you write will be
  discovered alongside the parent's tests.

  Created here (project-scoped, NOT inherited):
  - WebDev endpoints (testing/run, testing/tags)
  - Type stubs (.ignition-stubs/testing/)

  Which tag provider? > SITE01

  Scaffold complete: 14 created, 0 skipped.

  Gateway discovered 11 test modules:
  core.mes.changeover.__tests__, core.util.__tests__, ...

  Writing your first test:
  ignition/script-python/<package>/__tests__/code.py
```

### Project Inheritance

Ignition projects can inherit from a parent project. The scaffolding understands this:

**Inherited from parent (NOT created locally):**
- The Jython test framework (`testing.*` modules) — lives in the parent, shared across all child projects
- Test modules (`__tests__/code.py`) — can exist in both parent and child; the runner discovers all of them

**Always created locally (NOT inherited in Ignition):**
- WebDev endpoints (`testing/run`, `testing/tags`) — HTTP APIs are project-scoped in Ignition. Each project needs its own endpoints even if the scripts behind them are inherited.
- Type stubs (`.ignition-stubs/testing/`) — local files for IDE completion, not Ignition resources

If the parent project already has the test framework, the scaffolding uses `--skip-scripts` to avoid duplicating it. If the parent project is not found on disk, the plugin asks whether to scaffold everything locally or provide the parent path.

### Writing Tests

Tests go **inside the package they test** as a `__tests__` subdirectory. Never create standalone top-level test packages.

```text
CORRECT:
ignition/script-python/core/util/__tests__/code.py          # tests core.util
ignition/script-python/core/mes/changeover/__tests__/code.py # tests core.mes.changeover

WRONG:
ignition/script-python/tests/__tests__/code.py               # standalone — no matching code
```

A test file looks like this:

```python
from testing.decorators import test, skip, setup, teardown, expected_error
from testing.assertions import assert_equal, assert_true, assert_not_none, assert_raises

@setup
def setup_module():
    """Runs once before all tests in this module."""
    pass

@teardown
def teardown_module():
    """Runs once after all tests in this module."""
    pass

@test
def test_basic_logic():
    result = 2 + 2
    assert_equal(result, 4, "basic math works")

@test
def test_tag_value():
    result = system.tag.readBlocking(["[default]Some/Tag"])[0]
    assert_not_none(result.value, "tag should have a value")
    assert_true(result.quality.isGood(), "tag quality should be good")

@skip("waiting on PLC config")
@test
def test_not_ready_yet():
    pass

@expected_error(ValueError)
@test
def test_bad_input():
    int("not a number")
```

Every test directory needs a `resource.json` alongside `code.py` — without it, Ignition silently ignores the module:

```json
{
  "scope": "A",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": ["code.py"],
  "attributes": {
    "lastModification": {
      "actor": "external",
      "timestamp": "2026-01-01T00:00:00Z"
    }
  }
}
```

### Decorators

| Decorator | Purpose |
|-----------|---------|
| `@test` | Marks a function as a test case. The runner discovers functions with `_is_test = True`. |
| `@skip(reason="")` | Skips the test. Apply **before** `@test`: `@skip("reason")` then `@test` on the next line. |
| `@setup` | Module-level setup — runs once before all tests. One per module. |
| `@teardown` | Module-level teardown — runs once after all tests. One per module. |
| `@expected_error(ExceptionType)` | Test passes if the given exception is raised, fails otherwise. |

### Assertions

| Function | Purpose |
|----------|---------|
| `assert_equal(actual, expected, msg=None)` | `actual == expected` |
| `assert_not_equal(actual, expected, msg=None)` | `actual != expected` |
| `assert_true(val, msg=None)` | `val` is truthy |
| `assert_false(val, msg=None)` | `val` is falsy |
| `assert_none(val, msg=None)` | `val is None` |
| `assert_not_none(val, msg=None)` | `val is not None` |
| `assert_close(actual, expected, tolerance=0.001, msg=None)` | Floating point comparison within tolerance |
| `assert_raises(callable_fn, exception_type, msg=None)` | `callable_fn()` raises `exception_type`. Returns the caught exception. |
| `assert_tag_value(tag_path, expected, msg=None)` | Reads a real gateway tag and asserts its value. Uses `system.tag.readBlocking`. |
| `assert_contains(container, item, msg=None)` | `item in container` |
| `assert_isinstance(obj, expected_type, msg=None)` | `isinstance(obj, expected_type)` |

All assertions raise `TestAssertionError` (subclass of `AssertionError`) with `actual` and `expected` attributes for structured reporting.

### Running Tests

**From the Script Console:**

```python
print testing.runner.run_all()
print testing.runner.run_module("core.mes.changeover.__tests__")
print testing.reporter.to_console(testing.runner.run_all())
```

**Via HTTP (WebDev endpoints):**

```bash
# Discover test modules
curl -k -s "https://localhost:9043/system/webdev/MySiteHMI/testing/run?discover=true"

# Run all tests
curl -k -s -X POST "https://localhost:9043/system/webdev/MySiteHMI/testing/run"

# Run specific module
curl -k -s -X POST "https://localhost:9043/system/webdev/MySiteHMI/testing/run?module=core.mes.changeover.__tests__"

# Run by package prefix
curl -k -s -X POST "https://localhost:9043/system/webdev/MySiteHMI/testing/run?package=core.mes"

# Output formats: json (default), junit, text
curl -k -s -X POST "https://localhost:9043/system/webdev/MySiteHMI/testing/run?format=text"
```

HTTP response codes: **200** = all passed, **207** = failures/errors, **500** = runner error.

**Via Claude Code:**

```bash
/ignition-scada:test                    # All gateway Jython tests
/ignition-scada:test changeover         # Specific module
/ignition-scada:test core.mes           # By package prefix
```

### WebDev Endpoints

#### testing/run

| Method | Query Params | Description |
|--------|-------------|-------------|
| GET | `discover=true` | List all discovered test modules |
| POST | *(none)* | Run all tests |
| POST | `module=<path>` | Run a specific module (e.g., `core.mes.changeover.__tests__`) |
| POST | `package=<prefix>` | Run all modules matching a package prefix (e.g., `core.mes`) |
| POST | `format=json\|junit\|text` | Output format (default: `json`) |

#### testing/tags

Read/write tags and invoke scripts from external tools:

```bash
# Read tags
curl -k -s -X POST "https://localhost:9043/system/webdev/MySiteHMI/testing/tags" \
  -H "Content-Type: application/json" \
  -d '{"reads": ["[SITE01]Path/To/Tag"]}'

# Write tags (auto-creates if missing)
curl -k -s -X POST "https://localhost:9043/system/webdev/MySiteHMI/testing/tags" \
  -H "Content-Type: application/json" \
  -d '{"writes": [{"path": "[default]Test/Tag", "value": 42}]}'

# Call a gateway script function
curl -k -s -X POST "https://localhost:9043/system/webdev/MySiteHMI/testing/tags" \
  -H "Content-Type: application/json" \
  -d '{"script": {"path": "core.util.secrets.get_secret", "args": ["mes-host"]}}'

# Delete tags (cleanup)
curl -k -s -X POST "https://localhost:9043/system/webdev/MySiteHMI/testing/tags" \
  -H "Content-Type: application/json" \
  -d '{"deleteTags": "[default]Test/Tag"}'
```

### Common Patterns

**Testing a script function that reads tags:**

```python
@test
def test_get_area_state():
    from core.mes.changeover import client
    result = client.get_state("cooker")
    assert_not_none(result, "should return state dict")
    assert_contains(result, "current_state")
```

**Testing with tag setup/teardown:**

```python
@setup
def setup_module():
    from testing.helpers import write_dataset_tag
    write_dataset_tag(
        "[default]Test/Queue",
        ["Id", "Value"], ["String", "Int4"],
        [["A", 1], ["B", 2]]
    )

@teardown
def teardown_module():
    from testing.helpers import clear_dataset_tag
    clear_dataset_tag("[default]Test/Queue", ["Id", "Value"], ["String", "Int4"])

@test
def test_queue_processing():
    qv = system.tag.readBlocking(["[default]Test/Queue"])[0]
    ds = qv.value
    assert_equal(ds.getRowCount(), 2)
```

---

## Playwright E2E Tests

### What Gets Scaffolded

The `/ignition-scada:init-e2e` command creates a complete Playwright test setup for Perspective views:

| Component | Description |
|-----------|-------------|
| `playwright.config.ts` | Playwright config with auth project, base URL, timeouts |
| `fixtures/auth.setup.ts` | Auto-login, session persistence to `.auth/user.json` |
| `fixtures/perspective.ts` | Custom test fixture providing `PerspectivePage` |
| `pages/PerspectivePage.ts` | Base page object for Perspective DOM conventions |
| `components/Button.ts` | Wrapper for `ia.input.button` |
| `components/Table.ts` | Wrapper for `ia.display.table` |
| `helpers/gateway-api.ts` | Tag read/write, script invocation, health checks via WebDev |
| `tests/smoke/*.spec.ts` | Smoke tests for session loading, dock rendering, page content |
| `.env.example` | Environment variable template |

### How to Scaffold

```bash
/ignition-scada:init-e2e
```

Example flow:

```text
> /ignition-scada:init-e2e

  Perspective module found. Parent project has e2e/.env — copying
  credentials and updating project name.

  Scaffold done: 13 files created.

  Installing dependencies...
  npm install done
  playwright install chromium done

> Yes, run the auth setup and smoke tests

  authenticate (4.6s)
  session loads and docks render (2.8s)
  page content renders (2.7s)
  navigation exists in DOM (3.9s)

  4 passed, 0 failed (19s total)
```

### Auth Setup

The auth fixture (`fixtures/auth.setup.ts`) handles Perspective authentication:

1. Navigates to `/data/perspective/client/<PROJECT>`
2. Polls for login form (`input.username-field`) or existing live session (`[data-component]`)
3. If login form appears: fills credentials from `IGNITION_USER`/`IGNITION_PASSWORD` environment variables
4. Persists session to `.auth/user.json` for reuse across tests

If auth fails or expires, re-authenticate:

```bash
cd e2e && npx playwright test --project=setup
```

### Environment Variables

Set in `e2e/.env` (never committed — included in `.gitignore`):

| Variable | Purpose | Example |
|----------|---------|---------|
| `IGNITION_URL` | Gateway base URL | `https://localhost:9043` |
| `IGNITION_USER` | Login username | `admin` |
| `IGNITION_PASSWORD` | Login password | `password` |
| `PERSPECTIVE_PROJECT` | Perspective project name | `MySiteHMI` |
| `TAG_PROVIDER` | Default tag provider | `SITE01` |

### PerspectivePage

The base page object wraps Playwright's `Page` for Perspective conventions:

```typescript
import { PerspectivePage } from "../pages/PerspectivePage";

// Navigation
perspective.openPage("/route")           // Open a page route (call once per test)
perspective.waitForPageContent(timeout?)  // Wait for C-prefixed content to render
perspective.waitForSession(timeout?)      // Wait for any [data-component] elements

// Locators
perspective.pageContent()                // Scoped to page content (excludes docks)
perspective.componentByType("ia.display.label")  // Find by component type
perspective.pageLabelWithText("Title")   // Find label with specific text
perspective.pageText("some text")        // Find visible text in page content

// Utilities
perspective.dismissPopups()              // Close popup overlays
perspective.dumpComponentPaths()         // Debug: list all component paths in DOM
```

### Perspective DOM Conventions

Perspective is a React SPA served over WebSocket. Every component has `data-component-path` using positional indices, not the named paths from `view.json`.

**Prefix convention:**

| Prefix | Meaning |
|--------|---------|
| `C` | Center (page content) |
| `L[n]` | Left dock (e.g., `L[0]`, `L[1]`) |
| `T[n]` | Top dock (e.g., `T[0]`) |
| `$` | Embedded view boundary |
| `:` | Child index separator |

**Examples:**
- `C` — root page content container
- `C:0:1` — second child of first child of page content
- `C:0$0:2` — embedded view boundary, then third child
- `T[0]:0:1` — top dock, first container, second child

**Key rules:**
1. Never use `page.goto()` after initial session open — it creates a new WebSocket session. Use `perspective.openPage(route)` instead.
2. Page content is scoped by `C` prefix — use `perspective.pageContent()` to exclude docks.
3. Docks render independently — top dock (`T[0]`) may be visible before page content (`C`).
4. Embedded views reset the path counter — `$` marks the boundary, child indices restart from 0.
5. Left dock is often `onDemand` — check `toBeAttached()` not `toBeVisible()`.

### Component Wrappers

#### Button (`ia.input.button`)

```typescript
const btn = new Button(locator, page);
await btn.click()       // Wait for visible, then click
await btn.isEnabled()   // Checks for "ia_button--disabled" class
```

#### Table (`ia.display.table`)

```typescript
const table = new Table(locator, page);
await table.waitForData(timeout?)       // Wait for first row to render
await table.getRowCount()               // Number of visible rows
await table.clickRow(index)             // Click row by index
await table.getCellText(row, column)    // Get cell text content
```

### Gateway API Helper

Call WebDev endpoints from test code to set up state, read tags, or invoke gateway scripts:

```typescript
import {
  readTags, writeTags, readTag, writeTag,
  callScript, isGatewayReachable, mirrorTags, deleteMirror
} from "../helpers/gateway-api";

// Tag operations
const values = await readTags(["[SITE01]Path/To/Tag1", "[SITE01]Path/To/Tag2"]);
const val = await readTag("[SITE01]Path/To/Tag");
await writeTag("[default]Test/Tag", 42);

// Script invocation — call real Jython scripts on the gateway
const result = await callScript("core.mes.changeover.client.get_state", ["cooker"]);

// Tag mirroring — clone OPC tags to memory for testing without PLC
await mirrorTags("[SITE01]Area/Equipment", "[SITE01]Area/Equipment_MEM");
// ... run tests against memory tags ...
await deleteMirror("[SITE01]Area/Equipment_MEM");

// Health check
const reachable = await isGatewayReachable();
```

### Writing Tests

**Basic smoke test:**

```typescript
import { test, expect } from "../../fixtures/perspective";

test.describe("Overview smoke tests", () => {
  test("page loads with expected title", async ({ perspective }) => {
    await perspective.openPage("/overview");
    const title = perspective.pageLabelWithText("Plant Overview");
    await expect(title.first()).toBeVisible({ timeout: 15_000 });
  });

  test("table renders with data", async ({ perspective }) => {
    await perspective.openPage("/overview");
    const table = perspective.componentByType("ia.display.table");
    await expect(table.first()).toBeVisible();
    await expect(
      table.locator(".ia_table__body__row").first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
```

**Integration test with tag setup:**

```typescript
import { test, expect } from "../../fixtures/perspective";
import { writeTag, callScript } from "../../helpers/gateway-api";

test.describe("Changeover integration", () => {
  test.beforeAll(async () => {
    await writeTag("[default]Test/State", "idle");
  });

  test.afterAll(async () => {
    await writeTag("[default]Test/State", "");
  });

  test("state change reflects in UI", async ({ perspective }) => {
    await perspective.openPage("/changeover");
    await callScript("core.mes.changeover.client.transition", ["cooker", "start"]);
    const label = perspective.pageText("running");
    await expect(label).toBeVisible({ timeout: 10_000 });
  });
});
```

**Testing docks:**

```typescript
test("left dock menu exists", async ({ perspective }) => {
  await perspective.openPage("/some-page");
  // Left dock is onDemand — check attached, not visible
  const menu = perspective.page.locator("[data-component='ia.navigation.menutree']");
  await expect(menu).toBeAttached({ timeout: 10_000 });
});
```

### Running Tests

```bash
cd e2e

# All tests
npx playwright test

# Specific area
npx playwright test tests/changeover/

# Smoke tests only
npx playwright test tests/smoke/

# Headed mode (see the browser)
npx playwright test --headed

# Single test file
npx playwright test tests/smoke/perspective-loads.spec.ts

# View HTML report after failures
npx playwright show-report
```

Via Claude Code:

```bash
/ignition-scada:test ui                 # All Playwright browser tests
/ignition-scada:test ui smoke           # Playwright smoke tests only
/ignition-scada:test ui changeover      # Specific area
```

### Common Pitfalls

1. **Perspective takes 30-45s to reload after a project scan.** The auth fixture has a 45s timeout for this reason. If tests fail immediately after a scan, wait and retry.
2. **Don't call `page.goto()` mid-test.** This kills the WebSocket session. Navigate within Perspective using component interactions or `openPage()` for the initial load.
3. **Embedded views load asynchronously.** Wait for specific content inside them, don't rely on the parent container being visible.
4. **Tables render headers before data.** Use `table.waitForData()` or wait for `.ia_table__body__row` specifically.
5. **Popups from startup scripts** can block interaction. Call `perspective.dismissPopups()` after `openPage()` if needed.

---

## Auto-Test Hooks

The plugin includes two PostToolUse hooks that run tests automatically.

### Post-Commit Gateway Tests

After every `git commit` (detected by inspecting Bash tool output), the `run-tests.sh` hook:

1. Checks if the working directory is inside an Ignition project (`project.json` exists)
2. Checks if test infrastructure is set up (`testing/run` WebDev endpoint exists)
3. Checks if the gateway is reachable
4. Optionally triggers a project scan (if `IGNITION_API_TOKEN_FILE` is set)
5. Waits 3 seconds for scan propagation
6. Runs all tests via `testing/run` endpoint
7. Reports pass/fail summary to Claude

If any check fails, the hook silently exits. It is safe for global install.

### Post-Edit Playwright Tests

After every Write or Edit on a `view.json` file inside `com.inductiveautomation.perspective/views/`, the `run-ui-tests.sh` hook:

1. Checks if the file is a Perspective view
2. Checks if `e2e/` is set up (has `node_modules` and `.auth/user.json`)
3. Extracts the view area name from the file path
4. If matching tests exist in `e2e/tests/<area>/`, runs those. Otherwise, runs smoke tests.
5. Uses a directory-based lock to prevent concurrent Playwright runs

### Self-Gating

Both hooks silently exit when they detect any of these conditions:
- Not inside an Ignition project (no `project.json` in any parent directory)
- Test infrastructure not scaffolded
- Gateway not reachable (post-commit hook)
- E2E not set up (post-edit hook)

This means you can install the plugin globally and it will only activate when you are actually working on an Ignition project with tests configured.

---

## Deterministic Mode

All scaffolding scripts can be run directly from the command line, without Claude:

```bash
# Detect project structure
./scripts/detect-project.sh /path/to/project

# Scaffold Jython test framework
./scripts/scaffold-testing.sh \
  --project-root /path/to/project \
  --project-name MySiteHMI \
  --tag-provider SITE01

# Scaffold Playwright e2e tests
./scripts/scaffold-e2e.sh \
  --project-root /path/to/project \
  --project-name MySiteHMI \
  --tag-provider SITE01 \
  --perspective-project MySiteHMI
```

### Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--dry-run` | Both | Preview what would be created without writing files |
| `--force` | Both | Overwrite existing files |
| `--skip-scripts` | `scaffold-testing.sh` | Skip the Jython framework modules (use when parent project already has them) |

### Prerequisites

- **Gateway tests:** A running Ignition gateway (local or Docker)
- **E2E tests:** Node.js, Chromium (installed automatically by Playwright)
- **Both:** `jq` for the detection script (pre-installed on most systems)
