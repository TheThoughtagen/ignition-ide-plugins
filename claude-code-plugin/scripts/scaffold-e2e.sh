#!/usr/bin/env bash
# scaffold-e2e.sh — Scaffold Playwright E2E tests for Perspective views.
# Part of the Ignition Dev Tools Claude Code plugin.
#
# Creates ~13 files in an e2e/ directory:
#   1. Configuration       (package.json, tsconfig.json, playwright.config.ts, .env.example, .gitignore)
#   2. Fixtures            (auth.setup.ts, perspective.ts)
#   3. Helpers             (gateway-api.ts)
#   4. Page objects        (PerspectivePage.ts)
#   5. Components          (PerspectiveComponent.ts, Button.ts, Table.ts)
#   6. Smoke tests         (perspective-loads.spec.ts)
#
# Usage:
#   scaffold-e2e.sh --project-root /path/to/project --project-name MyProject \
#     [--gateway-url https://localhost:9043] [--tag-provider default] \
#     [--perspective-project MyProject] [--force] [--dry-run]

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

PROJECT_ROOT="" PROJECT_NAME="" GATEWAY_URL="" TAG_PROVIDER=""
PERSPECTIVE_PROJECT="" FORCE=false DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root)          PROJECT_ROOT="$2";          shift 2 ;;
    --project-name)          PROJECT_NAME="$2";          shift 2 ;;
    --gateway-url)           GATEWAY_URL="$2";           shift 2 ;;
    --tag-provider)          TAG_PROVIDER="$2";          shift 2 ;;
    --perspective-project)   PERSPECTIVE_PROJECT="$2";   shift 2 ;;
    --force)                 FORCE=true;                 shift ;;
    --dry-run)               DRY_RUN=true;               shift ;;
    -h|--help)
      sed -n '2,18s/^# //p' "$0"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# Validate required args
[[ -z "$PROJECT_ROOT" ]]  && { echo "Error: --project-root required" >&2; exit 1; }
[[ -z "$PROJECT_NAME" ]]  && { echo "Error: --project-name required" >&2; exit 1; }
GATEWAY_URL="${GATEWAY_URL:-https://localhost:9043}"
TAG_PROVIDER="${TAG_PROVIDER:-default}"
PERSPECTIVE_PROJECT="${PERSPECTIVE_PROJECT:-$PROJECT_NAME}"

# Verify project root exists
[[ -d "$PROJECT_ROOT" ]] || { echo "Error: project root does not exist: $PROJECT_ROOT" >&2; exit 1; }

# Derive lowercase name for package.json
PKG_NAME=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' _' '--')

CREATED=0 SKIPPED=0

echo "Scaffolding E2E test framework for project: $PROJECT_NAME"
echo "  Project root:          $PROJECT_ROOT"
echo "  Gateway URL:           $GATEWAY_URL"
echo "  Tag provider:          $TAG_PROVIDER"
echo "  Perspective project:   $PERSPECTIVE_PROJECT"
echo ""

# ===================================================================
# 1. Configuration files
# ===================================================================

echo "--- Configuration ---"

# --- package.json ---

PACKAGE_JSON=$(cat <<JSONEOF
{
  "name": "${PKG_NAME}-e2e",
  "private": true,
  "scripts": {
    "test": "npx playwright test",
    "test:headed": "npx playwright test --headed",
    "test:smoke": "npx playwright test tests/smoke/",
    "report": "npx playwright show-report"
  },
  "devDependencies": {
    "@playwright/test": "^1.50.0",
    "dotenv": "^16.4.0"
  }
}
JSONEOF
)
write_file "e2e/package.json" "$PACKAGE_JSON"

# --- tsconfig.json ---

TSCONFIG_JSON=$(cat <<'JSONEOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": ".",
    "baseUrl": ".",
    "paths": {
      "@pages/*": ["pages/*"],
      "@components/*": ["components/*"],
      "@fixtures/*": ["fixtures/*"]
    }
  },
  "include": ["**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
JSONEOF
)
write_file "e2e/tsconfig.json" "$TSCONFIG_JSON"

# --- playwright.config.ts ---

PLAYWRIGHT_CONFIG=$(cat <<'TSEOF'
import { defineConfig, devices } from "@playwright/test";
import * as dotenv from "dotenv";
import * as path from "path";

dotenv.config({ path: path.resolve(__dirname, ".env") });

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  timeout: 60_000,

  use: {
    baseURL: process.env.IGNITION_URL || "https://localhost:9043",
    ignoreHTTPSErrors: true,
    actionTimeout: 15_000,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "setup",
      testDir: "./fixtures",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: path.resolve(__dirname, ".auth/user.json"),
      },
      dependencies: ["setup"],
    },
  ],
});
TSEOF
)
write_file "e2e/playwright.config.ts" "$PLAYWRIGHT_CONFIG"

# --- .env.example ---

ENV_EXAMPLE=$(cat <<ENVEOF
IGNITION_URL=${GATEWAY_URL}
IGNITION_USER=
IGNITION_PASSWORD=
PERSPECTIVE_PROJECT=${PERSPECTIVE_PROJECT}
TAG_PROVIDER=${TAG_PROVIDER}
ENVEOF
)
write_file "e2e/.env.example" "$ENV_EXAMPLE"

# --- .gitignore ---

GITIGNORE=$(cat <<'GIEOF'
node_modules/
test-results/
playwright-report/
.auth/
.env
dist/
.playwright-running.lock
GIEOF
)
write_file "e2e/.gitignore" "$GITIGNORE"


# ===================================================================
# 2. Fixtures
# ===================================================================

echo ""
echo "--- Fixtures ---"

# --- fixtures/auth.setup.ts ---

AUTH_SETUP=$(cat <<'TSEOF'
import { test as setup } from "@playwright/test";
import * as path from "path";

const AUTH_FILE = path.resolve(__dirname, "../.auth/user.json");

setup.setTimeout(60_000);

setup("authenticate", async ({ page }) => {
  const project =
    process.env.PERSPECTIVE_PROJECT || "MyProject";

  await page.goto(`/data/perspective/client/${project}`);

  // Wait for either a login form or a live Perspective session.
  // In guest mode, the session starts directly without login.
  // After a project scan, Perspective takes up to 30s to reload.
  // Use polling instead of waitForFunction to avoid actionTimeout cap.
  let result: string = "timeout";
  const deadline = Date.now() + 45_000;
  while (Date.now() < deadline) {
    result = await page.evaluate(() => {
      if (document.querySelector("input.username-field")) return "login";
      if (document.querySelectorAll("[data-component]").length > 0)
        return "session";
      return "waiting";
    });
    if (result === "login" || result === "session") break;
    await page.waitForTimeout(1_000);
  }

  if (result === "timeout" || result === "waiting") {
    throw new Error(
      "Neither login form nor Perspective session appeared within 45s"
    );
  }

  if (result === "login") {
    const user = process.env.IGNITION_USER;
    const pass = process.env.IGNITION_PASSWORD;

    if (!user || !pass) {
      throw new Error(
        "Login form detected but IGNITION_USER/PASSWORD not set in e2e/.env"
      );
    }

    await page.locator("input.username-field").fill(user);
    await page.locator("input.password-field").fill(pass);
    await page.locator("div.submit-button").click();

    await page.waitForFunction(
      () => document.querySelectorAll("[data-component]").length > 0,
      { timeout: 30_000 }
    );
  }

  // Session is live — persist auth state for reuse
  await page.context().storageState({ path: AUTH_FILE });
});
TSEOF
)
write_file "e2e/fixtures/auth.setup.ts" "$AUTH_SETUP"

# --- fixtures/perspective.ts ---

PERSPECTIVE_FIXTURE=$(cat <<'TSEOF'
import { test as base } from "@playwright/test";
import { PerspectivePage } from "../pages/PerspectivePage";

type PerspectiveFixtures = {
  perspective: PerspectivePage;
};

export const test = base.extend<PerspectiveFixtures>({
  perspective: async ({ page }, use) => {
    const perspective = new PerspectivePage(page);
    await use(perspective);
  },
});

export { expect } from "@playwright/test";
TSEOF
)
write_file "e2e/fixtures/perspective.ts" "$PERSPECTIVE_FIXTURE"


# ===================================================================
# 3. Helpers
# ===================================================================

echo ""
echo "--- Helpers ---"

# --- helpers/gateway-api.ts (genericized — WHK-specific code removed) ---

GATEWAY_API=$(cat <<TSEOF
/**
 * Gateway API helper — calls WebDev endpoints from Playwright tests.
 *
 * Uses the testing/tags endpoint for read/write (test-only),
 * and GatewayAPI endpoints for health checks and queries.
 */

// Allow self-signed certs — the local gateway uses a self-signed TLS cert.
// Playwright's \`request\` fixture handles this via \`ignoreHTTPSErrors: true\`,
// but raw Node \`fetch\` calls in this module need the env var.
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const BASE =
  process.env.IGNITION_URL || "https://localhost:9043";
const WEBDEV = \`\${BASE}/system/webdev/${PROJECT_NAME}\`;

async function post(path: string, body: unknown): Promise<unknown> {
  const res = await fetch(\`\${WEBDEV}\${path}\`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    // @ts-expect-error -- Node 18+ fetch supports this for self-signed certs
    dispatcher: undefined,
  });
  if (!res.ok) {
    throw new Error(\`\${path} returned \${res.status}: \${await res.text()}\`);
  }
  return res.json();
}

async function get(path: string): Promise<unknown> {
  const res = await fetch(\`\${WEBDEV}\${path}\`, {
    // @ts-expect-error
    dispatcher: undefined,
  });
  if (!res.ok) {
    throw new Error(\`\${path} returned \${res.status}: \${await res.text()}\`);
  }
  return res.json();
}

// ── Tag operations (via testing/tags endpoint) ──

export interface TagValue {
  value: unknown;
  quality: string;
  good: boolean;
}

export interface WriteResult {
  path: string;
  success: boolean;
  quality: string;
}

/** Read tag values from the gateway. */
export async function readTags(
  paths: string[]
): Promise<Record<string, TagValue>> {
  const data = (await post("/testing/tags", { reads: paths })) as {
    values: Record<string, TagValue>;
  };
  return data.values;
}

/** Write tag values to the gateway. */
export async function writeTags(
  writes: Array<{ path: string; value: unknown }>
): Promise<WriteResult[]> {
  const data = (await post("/testing/tags", { writes })) as {
    results: WriteResult[];
  };
  return data.results;
}

/** Read a single tag and return its value (or null if bad quality). */
export async function readTag(path: string): Promise<unknown> {
  const values = await readTags([path]);
  const tag = values[path];
  return tag?.good ? tag.value : null;
}

/** Write a single tag value. */
export async function writeTag(
  path: string,
  value: unknown
): Promise<boolean> {
  const results = await writeTags([{ path, value }]);
  return results[0]?.success ?? false;
}

// ── Tag mirroring (OPC → memory copies for testing without PLC) ──
// To enable mirrorTags(), implement convert_to_memory_tags() in your gateway
// script library, then uncomment the mirror block in the testing/tags endpoint.

/** Delete a tag tree (cleanup after tests). */
export async function deleteMirror(path: string): Promise<boolean> {
  const data = (await post("/testing/tags", { deleteTags: path })) as {
    deleteTags: { success: boolean };
  };
  return data.deleteTags?.success ?? false;
}

// ── Gateway script invocation (call real Jython scripts from tests) ──

export interface ScriptResult {
  success: boolean;
  result?: unknown;
  error?: string;
}

/**
 * Call a gateway script function by its dotted path.
 * Executes the real Jython code on the gateway — no mocking.
 *
 * @example callScript("my.project.scripts.validate", [arg1, arg2])
 */
export async function callScript(
  path: string,
  args: unknown[] = [],
  kwargs: Record<string, unknown> = {}
): Promise<ScriptResult> {
  const data = (await post("/testing/tags", {
    script: { path, args, kwargs },
  })) as { script: ScriptResult };
  return data.script;
}

// ── Health checks ──

/** Quick connectivity check — returns true if gateway responds. */
export async function isGatewayReachable(): Promise<boolean> {
  try {
    const res = await fetch(\`\${BASE}/StatusPing\`, {
      signal: AbortSignal.timeout(5_000),
      // @ts-expect-error
      dispatcher: undefined,
    });
    return res.ok;
  } catch {
    return false;
  }
}
TSEOF
)
write_file "e2e/helpers/gateway-api.ts" "$GATEWAY_API"


# ===================================================================
# 4. Page Objects
# ===================================================================

echo ""
echo "--- Page Objects ---"

# --- pages/PerspectivePage.ts ---

PERSPECTIVE_PAGE=$(cat <<'TSEOF'
import { Page, Locator } from "@playwright/test";

/**
 * Base page object for Perspective views.
 *
 * Perspective is a React SPA served over WebSocket. Key DOM facts:
 * - data-component-path uses positional indices, NOT named paths from view.json
 * - Prefix convention: L[n]=left dock, T[n]=top dock, C=center (page content)
 * - $ separates embedded view boundaries, : separates child indices
 * - Never use page.goto() after the initial session open — it creates a new session
 */
export class PerspectivePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  private get project(): string {
    return process.env.PERSPECTIVE_PROJECT || "MyProject";
  }

  /** Open a Perspective session at the given page route. Call once per test. */
  async openPage(pageRoute: string): Promise<void> {
    const route = pageRoute.startsWith("/") ? pageRoute : `/${pageRoute}`;
    await this.page.goto(
      `/data/perspective/client/${this.project}${route}`
    );
    await this.waitForPageContent();
  }

  /** Wait for the center (page) content area to render. */
  async waitForPageContent(timeout = 30_000): Promise<void> {
    await this.page
      .locator("[data-component-path^='C']")
      .first()
      .waitFor({ state: "visible", timeout });
  }

  /** Wait for any Perspective components to load (docks included). */
  async waitForSession(timeout = 30_000): Promise<void> {
    await this.page.waitForFunction(
      () => document.querySelectorAll("[data-component]").length > 3,
      { timeout }
    );
  }

  /** Scope a locator to the page content area (excludes docks). */
  pageContent(): Locator {
    return this.page.locator("[data-component-path^='C']").first();
  }

  /** Find a component by type within the page content area. */
  componentByType(type: string): Locator {
    return this.page.locator(
      `[data-component-path^='C'] [data-component='${type}'], [data-component-path^='C'][data-component='${type}']`
    );
  }

  /** Find a label containing specific text in the page content area. */
  pageLabelWithText(text: string): Locator {
    return this.page
      .locator("[data-component-path^='C'] [data-component='ia.display.label']")
      .filter({ hasText: text });
  }

  /** Find visible text anywhere in the page content (not docks). */
  pageText(text: string): Locator {
    return this.pageContent().getByText(text);
  }

  /** Dismiss any popup overlays (e.g. startup script modals). */
  async dismissPopups(): Promise<void> {
    const overlay = this.page.locator(".popup-overlay .close-button");
    if (await overlay.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await overlay.click();
    }
  }

  /** Get all component paths currently in the DOM (useful for debugging). */
  async dumpComponentPaths(): Promise<string[]> {
    return this.page.evaluate(() => {
      const els = document.querySelectorAll("[data-component-path]");
      return Array.from(els).map((el) => {
        const path = el.getAttribute("data-component-path") || "";
        const comp = el.getAttribute("data-component") || "";
        return `${path} → ${comp}`;
      });
    });
  }
}
TSEOF
)
write_file "e2e/pages/PerspectivePage.ts" "$PERSPECTIVE_PAGE"


# ===================================================================
# 5. Components
# ===================================================================

echo ""
echo "--- Components ---"

# --- components/PerspectiveComponent.ts ---

PERSPECTIVE_COMPONENT=$(cat <<'TSEOF'
import { Locator, Page } from "@playwright/test";

/**
 * Base class for Perspective component wrappers.
 * Wraps a Locator and adds common operations.
 */
export class PerspectiveComponent {
  readonly locator: Locator;
  readonly page: Page;

  constructor(locator: Locator, page: Page) {
    this.locator = locator;
    this.page = page;
  }

  async isVisible(timeout = 5_000): Promise<boolean> {
    return this.locator.isVisible({ timeout }).catch(() => false);
  }

  async waitForVisible(timeout = 10_000): Promise<void> {
    await this.locator.waitFor({ state: "visible", timeout });
  }

  async getText(): Promise<string> {
    return (await this.locator.textContent()) ?? "";
  }
}
TSEOF
)
write_file "e2e/components/PerspectiveComponent.ts" "$PERSPECTIVE_COMPONENT"

# --- components/Button.ts ---

BUTTON_COMPONENT=$(cat <<'TSEOF'
import { Locator, Page } from "@playwright/test";
import { PerspectiveComponent } from "./PerspectiveComponent";

/**
 * Wrapper for ia.input.button components.
 */
export class Button extends PerspectiveComponent {
  constructor(locator: Locator, page: Page) {
    super(locator, page);
  }

  async click(): Promise<void> {
    await this.waitForVisible();
    await this.locator.click();
  }

  async isEnabled(): Promise<boolean> {
    // Perspective disables buttons via an "ia_button--disabled" class
    const classes = (await this.locator.getAttribute("class")) ?? "";
    return !classes.includes("disabled");
  }
}
TSEOF
)
write_file "e2e/components/Button.ts" "$BUTTON_COMPONENT"

# --- components/Table.ts ---

TABLE_COMPONENT=$(cat <<'TSEOF'
import { Locator, Page } from "@playwright/test";
import { PerspectiveComponent } from "./PerspectiveComponent";

/**
 * Wrapper for ia.display.table components.
 */
export class Table extends PerspectiveComponent {
  constructor(locator: Locator, page: Page) {
    super(locator, page);
  }

  /** Wait until at least one data row is rendered. */
  async waitForData(timeout = 15_000): Promise<void> {
    await this.locator
      .locator(".ia_table__body__row")
      .first()
      .waitFor({ state: "visible", timeout });
  }

  async getRowCount(): Promise<number> {
    return this.locator.locator(".ia_table__body__row").count();
  }

  async clickRow(index: number): Promise<void> {
    await this.locator
      .locator(".ia_table__body__row")
      .nth(index)
      .click();
  }

  async getCellText(row: number, column: number): Promise<string> {
    const cell = this.locator
      .locator(".ia_table__body__row")
      .nth(row)
      .locator(".ia_table__body__cell")
      .nth(column);
    return (await cell.textContent()) ?? "";
  }
}
TSEOF
)
write_file "e2e/components/Table.ts" "$TABLE_COMPONENT"


# ===================================================================
# 6. Smoke Tests
# ===================================================================

echo ""
echo "--- Smoke Tests ---"

# --- tests/smoke/perspective-loads.spec.ts (generic — no WHK references) ---

SMOKE_TESTS=$(cat <<'TSEOF'
import { test, expect } from "../../fixtures/perspective";

test.describe("Perspective smoke tests", () => {
  test("session loads successfully", async ({ perspective }) => {
    await perspective.openPage("/");
    await perspective.waitForSession();

    // Verify the Perspective session is active by checking for any rendered component
    const anyComponent = perspective.page.locator("[data-component]");
    await expect(anyComponent.first()).toBeVisible({ timeout: 15_000 });
  });

  test("page content renders", async ({ perspective }) => {
    await perspective.openPage("/");
    await perspective.waitForPageContent();

    // At least one Perspective component should exist in the page content area
    const components = perspective.page.locator(
      "[data-component-path^='C'] [data-component]"
    );
    await expect(components.first()).toBeVisible({ timeout: 10_000 });
    expect(await components.count()).toBeGreaterThan(0);
  });

  test("no console errors on load", async ({ perspective }) => {
    const errors: string[] = [];
    perspective.page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await perspective.openPage("/");
    await perspective.waitForPageContent();

    // Filter out known benign errors (e.g., favicon 404)
    const realErrors = errors.filter((e) => !e.includes("favicon"));
    expect(realErrors).toEqual([]);
  });
});
TSEOF
)
write_file "e2e/tests/smoke/perspective-loads.spec.ts" "$SMOKE_TESTS"


# ===================================================================
# Summary
# ===================================================================

echo ""
if [[ "$DRY_RUN" = true ]]; then
  echo "Dry run complete. No files were written."
else
  echo "Scaffold complete: $CREATED created, $SKIPPED skipped."
fi
