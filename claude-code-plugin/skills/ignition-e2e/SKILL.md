---
name: ignition-e2e
description: Ignition Perspective e2e testing reference — Playwright page objects, gateway API helpers, and Perspective DOM conventions. Use when writing or debugging Playwright browser tests for Perspective views.
user-invocable: false
---

# Ignition Perspective E2E Testing Reference

This project uses Playwright to test Ignition Perspective views in a real browser. Tests run against a live gateway, authenticate through the Perspective login form, and interact with the actual Perspective SPA.

## Architecture

- **e2e/** directory at project root contains all Playwright tests
- **PerspectivePage** — base page object that wraps Playwright's `Page` for Perspective conventions
- **Component wrappers** — typed wrappers for Perspective components (Button, Table, etc.)
- **gateway-api.ts** — Node.js helper that calls WebDev endpoints for tag read/write, script invocation
- **Auth fixture** — authenticates once, persists session to `.auth/user.json` for reuse

## Inheritable Projects

E2E tests target Perspective views rendered in a browser. Inheritable (parent) projects — those where other projects list them as `"parent"` in `project.json` — typically have no `com.inductiveautomation.perspective/` directory and no views. If you're in a parent project, E2E tests can be proxied through a child project that has Perspective views. The `/ignition-scada:test ui` command detects this automatically, finds child projects with E2E setup, and runs Playwright from the child's `e2e/` directory.

## Perspective DOM Conventions (CRITICAL)

Perspective is a React SPA served over WebSocket. The DOM has specific conventions you MUST understand:

### data-component-path

Every Perspective component has `data-component-path` using **positional indices**, NOT the named paths from `view.json`.

**Prefix convention:**
- `L[n]` = left dock (e.g., `L[0]`, `L[1]`)
- `T[n]` = top dock (e.g., `T[0]`)
- `C` = center (page content)
- `$` separates embedded view boundaries
- `:` separates child indices

**Examples:**
- `C` — the root page content container
- `C:0:1` — second child of first child of page content
- `C:0$0:2` — embedded view boundary, then third child
- `T[0]:0:1` — top dock, first container, second child
- `L[0]` — left dock

### data-component

The component type attribute: `data-component="ia.display.label"`, `data-component="ia.input.button"`, etc.

### Key rules

1. **Never use `page.goto()` after initial session open** — it creates a new WebSocket session. Use `PerspectivePage.openPage(route)` instead. Exception: the very first navigation to the session root (e.g., for dock-only tests) may use `page.goto()`.
2. **Page content is scoped by `C` prefix** — use `perspective.pageContent()` to exclude docks.
3. **Docks render independently** — top dock (`T[0]`) may be visible before page content (`C`).
4. **Embedded views reset the path counter** — `$` marks the boundary, child indices restart from 0.
5. **Left dock is often `onDemand`** — check `toBeAttached()` not `toBeVisible()`.

## PerspectivePage (Base Page Object)

```typescript
import { PerspectivePage } from "../pages/PerspectivePage";

// Available methods:
perspective.openPage("/route")           // Open a page route (call once per test)
perspective.waitForPageContent(timeout?)  // Wait for C-prefixed content to render
perspective.waitForSession(timeout?)      // Wait for any [data-component] elements
perspective.pageContent()                // Locator scoped to page content (excludes docks)
perspective.componentByType("ia.display.label")  // Find by component type in page content
perspective.pageLabelWithText("Title")   // Find label with text in page content
perspective.pageText("some text")        // Find visible text in page content
perspective.dismissPopups()              // Close popup overlays
perspective.dumpComponentPaths()         // Debug: list all component paths in DOM
```

## Component Wrappers

### PerspectiveComponent (base)
```typescript
const comp = new PerspectiveComponent(locator, page);
await comp.isVisible(timeout?)      // Returns boolean
await comp.waitForVisible(timeout?) // Throws if not visible
await comp.getText()                // Text content
```

### Button (`ia.input.button`)
```typescript
const btn = new Button(locator, page);
await btn.click()       // Wait for visible, then click
await btn.isEnabled()   // Checks for "ia_button--disabled" class
```

### Table (`ia.display.table`)
```typescript
const table = new Table(locator, page);
await table.waitForData(timeout?)       // Wait for first row to render
await table.getRowCount()               // Number of visible rows
await table.clickRow(index)             // Click row by index
await table.getCellText(row, column)    // Get cell text content
```

Row selector: `.ia_table__body__row`
Cell selector: `.ia_table__body__cell`

## Gateway API Helper

Call WebDev endpoints from test code:

```typescript
import { readTags, writeTags, readTag, writeTag, callScript, isGatewayReachable, mirrorTags, deleteMirror } from "../helpers/gateway-api";

// Tag operations
const values = await readTags(["[WHK01]Path/To/Tag1", "[WHK01]Path/To/Tag2"]);
// Returns: { "[WHK01]Path/To/Tag1": { value: 42, quality: "Good", good: true } }

const val = await readTag("[WHK01]Path/To/Tag");  // Single tag, returns value or null

await writeTag("[default]Test/Tag", 42);           // Single write, returns boolean
await writeTags([{ path: "[default]Test/Tag1", value: "hello" }, { path: "[default]Test/Tag2", value: 123 }]);

// Script invocation — call real Jython scripts on the gateway
const result = await callScript("core.mes.changeover.client.get_state", ["cooker"]);
// Returns: { success: true, result: { current_state: "idle", ... } }

// Tag mirroring — clone OPC tags to memory for testing without PLC
await mirrorTags("[WHK01]Distillery01/Mashing01", "[WHK01]Distillery01/Mashing01_MEM");
// ... run tests against memory tags ...
await deleteMirror("[WHK01]Distillery01/Mashing01_MEM");  // Cleanup

// Health check
const reachable = await isGatewayReachable();  // Quick connectivity check
```

## Auth Setup

The `fixtures/auth.setup.ts` handles authentication:
1. Navigates to `/data/perspective/client/<PROJECT>`
2. Polls for login form (`input.username-field`) or live session (`[data-component]`)
3. If login form: fills credentials from `IGNITION_USER`/`IGNITION_PASSWORD` env vars
4. Persists session to `.auth/user.json` for reuse across tests

**If auth fails:** Run `cd e2e && npx playwright test --project=setup` to re-authenticate.

## Custom Fixture

Use the `perspective` fixture instead of raw `page`:

```typescript
import { test, expect } from "../fixtures/perspective";

test("my test", async ({ perspective }) => {
  await perspective.openPage("/my-page");
  const title = perspective.pageLabelWithText("My Title");
  await expect(title.first()).toBeVisible();
});
```

This auto-wraps `page` in a `PerspectivePage` instance.

## Writing Tests

### Basic smoke test
```typescript
import { test, expect } from "../../fixtures/perspective";

test.describe("My View smoke tests", () => {
  test("page loads with expected title", async ({ perspective }) => {
    await perspective.openPage("/my-view");
    const title = perspective.pageLabelWithText("Expected Title");
    await expect(title.first()).toBeVisible({ timeout: 15_000 });
  });

  test("table renders with data", async ({ perspective }) => {
    await perspective.openPage("/my-view");
    const table = perspective.componentByType("ia.display.table");
    await expect(table.first()).toBeVisible();
    // Check for data rows
    await expect(table.locator(".ia_table__body__row").first()).toBeVisible({ timeout: 10_000 });
  });
});
```

### Integration test with tag setup
```typescript
import { test, expect } from "../../fixtures/perspective";
import { writeTag, readTag, callScript } from "../../helpers/gateway-api";

test.describe("Changeover integration", () => {
  test.beforeAll(async () => {
    // Set up test state via gateway API
    await writeTag("[default]Test/State", "idle");
  });

  test.afterAll(async () => {
    // Cleanup
    await writeTag("[default]Test/State", "");
  });

  test("state change reflects in UI", async ({ perspective }) => {
    await perspective.openPage("/changeover");
    // Trigger state change via script
    await callScript("core.mes.changeover.client.transition", ["cooker", "start"]);
    // Verify UI updates
    const label = perspective.pageText("running");
    await expect(label).toBeVisible({ timeout: 10_000 });
  });
});
```

### Testing docks
```typescript
test("top dock shows plant data", async ({ perspective }) => {
  // Don't use openPage for dock-only tests — just navigate to session root
  await perspective.page.goto(`/data/perspective/client/${process.env.PERSPECTIVE_PROJECT}`);
  await perspective.waitForSession();

  const topDock = perspective.page.locator("[data-component-path^='T[0]']");
  await expect(topDock.first()).toBeVisible();
});

test("left dock menu exists", async ({ perspective }) => {
  await perspective.openPage("/some-page");
  // Left dock is onDemand — check attached, not visible
  const menu = perspective.page.locator("[data-component='ia.navigation.menutree']");
  await expect(menu).toBeAttached({ timeout: 10_000 });
});
```

## Running Tests

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

## Environment Variables

Set in `e2e/.env`:

| Variable | Purpose | Example |
|----------|---------|---------|
| `IGNITION_URL` | Gateway base URL | `https://localhost:9043` |
| `IGNITION_USER` | Login username | `admin` |
| `IGNITION_PASSWORD` | Login password | `password` |
| `PERSPECTIVE_PROJECT` | Perspective project name | `QSI_WhiskeyHouseKentucky01` |
| `TAG_PROVIDER` | Default tag provider | `WHK01` |

## Common Pitfalls

1. **Perspective takes 30-45s to reload after a project scan.** The auth fixture has a 45s timeout for this reason. If tests fail immediately after a scan, wait and retry.
2. **Don't call `page.goto()` mid-test.** This kills the WebSocket session. Navigate within Perspective using component interactions or `openPage()` for the initial load.
3. **Embedded views load asynchronously.** Wait for specific content inside them, don't rely on the parent container being visible.
4. **Tables render headers before data.** Use `table.waitForData()` or wait for `.ia_table__body__row` specifically.
5. **Popups from startup scripts** can block interaction. Call `perspective.dismissPopups()` after `openPage()` if needed.
