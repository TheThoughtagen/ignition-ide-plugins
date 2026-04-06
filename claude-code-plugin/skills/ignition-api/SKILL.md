---
name: ignition-api
description: Ignition system.* API reference — 14 modules, 239 functions. Use when writing Ignition Jython scripts.
user-invocable: false
---

# Ignition System API Reference

You are writing code for **Ignition SCADA** by Inductive Automation. Scripts run in **Jython 2.7** (Python 2.7 on JVM). The scripting API is `system.*`.

## CRITICAL: resource.json Required for EVERY Ignition Resource

**Every file or directory you create inside an Ignition project MUST have a `resource.json`.** Without it, the gateway silently ignores the resource — no error, no warning, it simply doesn't exist at runtime. This is the #1 cause of "not found" errors when managing Ignition projects via git.

This applies to ALL resource types:

| Resource type | Where | resource.json goes |
|---------------|-------|--------------------|
| **Script modules** | `ignition/script-python/my_package/` | Next to `code.py` in every directory in the path |
| **Script sub-packages** | `ignition/script-python/my_package/sub/` | In `sub/` too — every level needs one |
| **Test modules** | `ignition/script-python/pkg/__tests__/` | In both `pkg/` AND `__tests__/` |
| **Perspective views** | `com.inductiveautomation.perspective/views/MyView/` | Next to `view.json` |
| **Named queries** | `com.inductiveautomation.naming/queries/MyQuery/` | Next to `query.json` |
| **Vision windows** | `com.inductiveautomation.vision/windows/MyWindow/` | Next to `window.json` |
| **WebDev endpoints** | `com.inductiveautomation.webdev/resources/my-endpoint/` | Next to `doGet.py`, `config.json`, etc. |
| **Alarm pipelines** | `com.inductiveautomation.alarm-notification/pipelines/` | Next to pipeline resource files |
| **Tag configs** | `tags/` | Alongside tag JSON exports |

**Template for script resources** (scope `A` = script module):
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

**Template for Perspective views** (scope `G` = general):
```json
{
  "scope": "G",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": ["view.json", "thumbnail.png"],
  "attributes": {
    "lastModification": {
      "actor": "external",
      "timestamp": "2026-01-01T00:00:00Z"
    },
    "lastModificationSignature": "unknown"
  }
}
```

### Perspective View Parameters (propConfig)

**CRITICAL:** Every view parameter MUST have an explicit `propConfig` entry with `paramDirection`. Without it, the runtime silently fails to propagate parameter values from embedding parent views.

The Designer shows "input" as the default direction arrow in the UI, but this is NOT serialized to the view JSON unless the user explicitly sets it. **Missing propConfig ≠ default propConfig.**

**paramDirection values:**
- `"input"` — parent sets this param; child reads it (most common for embedded views)
- `"output"` — child sets this param; parent reads it
- `"inout"` — bidirectional; both parent and child can read/write

**Correct view.json pattern:**
```json
{
  "params": {
    "itemId": 0,
    "mode": "view"
  },
  "propConfig": {
    "params.itemId": {
      "paramDirection": "input",
      "persistent": true
    },
    "params.mode": {
      "paramDirection": "input",
      "persistent": true
    }
  }
}
```

**Template for WebDev endpoints**:
```json
{
  "scope": "G",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": ["config.json", "doGet.py", "doPost.py"],
  "attributes": {
    "lastModification": {
      "actor": "external",
      "timestamp": "2026-01-01T00:00:00Z"
    }
  }
}
```

**The `files` array must list every file in the directory that Ignition should load.** If you add a file but don't list it in `files`, Ignition ignores it.

**When creating any new resource in an Ignition project: ALWAYS create the `resource.json` at the same time.** Never create a `code.py`, `view.json`, or any other Ignition resource file without its accompanying `resource.json`.

## Ignition Script Library Structure

Ignition's script library (`ignition/script-python/`) has a strict structure. Each directory is either a **leaf module** or a **package node** — never both.

**Leaf module** — has `code.py` with real code, NO child directories with code:
```text
core/util/secrets/
├── code.py          ← actual functions live here
└── resource.json
```

**Package node** — has child directories, NO `code.py` (or only an empty placeholder):
```text
core/util/
├── secrets/         ← child module
│   ├── code.py
│   └── resource.json
├── csv/             ← child module
│   ├── code.py
│   └── resource.json
└── resource.json    ← resource.json still required, but NO code.py
```

**NEVER put a `code.py` in a directory that also contains child packages.** Ignition treats a directory with `code.py` as a leaf module. If you also put subdirectories in it, the behavior is undefined and the child modules may not be importable.

**Exception:** `__tests__/` directories are special — Ignition's script runtime ignores directories whose names start with `__`, so they do not conflict with a sibling `code.py`. The testing framework relies on this convention.

```text
WRONG:
my_package/
├── code.py          ← has real code
├── resource.json
└── utils/           ← real child package — conflicts with code.py above
    ├── code.py
    └── resource.json

OK (special case):
my_package/
├── code.py          ← has real code
├── resource.json
└── __tests__/       ← ignored by Ignition runtime, used by test framework
    ├── code.py
    └── resource.json

CORRECT (general pattern):
my_package/
├── resource.json    ← package node, no code.py
├── logic/
│   ├── code.py      ← real code lives in a leaf
│   └── resource.json
└── __tests__/
    ├── code.py      ← tests live in a leaf
    └── resource.json
```

When `resource.json` exists without `code.py`, Ignition recognizes the directory as a package node. The `files` array in `resource.json` should be empty or omit `code.py`:
```json
{
  "scope": "A",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": [],
  "attributes": {
    "lastModification": {
      "actor": "external",
      "timestamp": "2026-01-01T00:00:00Z"
    }
  }
}
```

## Linting

This project uses [`ignition-lint`](https://pypi.org/project/ignition-lint-toolkit/) to catch Ignition-specific issues. The auto-lint hook runs on every file write, but you should also be aware of what it checks so you write clean code from the start:

- **JYTHON_PRINT_STATEMENT** — Use `print()` function form, not `print x`
- **JYTHON_IMPORT_STAR** — Never use `from module import *`
- **IGNITION_UNKNOWN_SYSTEM_CALL** — Verify `system.*` function names are correct
- **IGNITION_SYSTEM_OVERRIDE** — Never shadow `system.*` with local variables
- **LONG_LINE** — Keep lines under 120 characters
- **MISSING_DOCSTRING** — Add docstrings to public functions
- **EXPR_NOW_DEFAULT_POLLING** — Expression `now()` defaults to 1-second polling; use `now(5000)` or higher
- **EMPTY_COMPONENT_NAME / GENERIC_COMPONENT_NAME** — Perspective components need meaningful names

If `ignition-lint` is installed, the plugin's auto-lint hook catches these automatically after every file edit. If it's not installed, the hook silently exits — nothing breaks, but you lose automatic feedback.

## Jython Conventions
- Use `print()` function form (not `print x`)
- Java classes are directly importable: `from java.util import ArrayList`
- No f-strings, no walrus operator, no type hints
- Use `system.util.getLogger()` for logging, not `print()`
- Avoid mutable globals in script modules (they persist across calls)
- ALWAYS use `runPrepQuery`/`runPrepUpdate` with `?` params — NEVER string-format SQL

## API Modules

### system.alarm (10)
`acknowledge`, `cancel`, `createRoster`, `getRosters`, `getShelvedPaths`, `listPipelines`, `queryJournal`, `queryStatus`, `shelve`, `unshelve`

### system.dataset (22)
`addColumn`, `addRow`, `addRows`, `appendDataset`, `clearDataset`, `dataSetToHTML`, `deleteRow`, `deleteRows`, `exportCSV`, `exportExcel`, `exportHTML`, `filterColumns`, `formatDates`, `fromCSV`, `getColumnHeaders`, `setValue`, `sort`, `toCSV`, `toDataSet`, `toExcel`, `toPyDataSet`, `updateRow`

### system.date (41)
`now`, `parse`, `format`, `midnight`, `setTime`, `addHours`, `addMinutes`, `addSeconds`, `addMillis`, `addDays`, `addWeeks`, `addMonths`, `addYears`, `getHour12`, `getHour24`, `getMinute`, `getSecond`, `getMillis`, `getYear`, `getMonth`, `getDayOfMonth`, `getDayOfWeek`, `getDayOfYear`, `getAMorPM`, `getDate`, `getTimezone`, `getTimezoneOffset`, `getTimezoneRawOffset`, `hoursBetween`, `minutesBetween`, `secondsBetween`, `millisBetween`, `daysBetween`, `monthsBetween`, `yearsBetween`, `toMillis`, `fromMillis`, `isAfter`, `isBefore`, `isBetween`, `isDaylightTime`

### system.db (10)
`runQuery`, `runPrepQuery`, `runUpdateQuery`, `runPrepUpdate`, `beginTransaction`, `commitTransaction`, `rollbackTransaction`, `closeTransaction`, `createSProcCall`, `execSProcCall`

### system.file (8)
`fileExists`, `getTempFile`, `openFile`, `openFiles`, `readFileAsBytes`, `readFileAsString`, `saveFile`, `writeFile`

### system.gui (32)
`messageBox`, `warningBox`, `errorBox`, `confirm`, `inputBox`, `passwordBox`, `chooseColor`, `color`, `openDesktop`, `closeDesktop`, `desktop`, `getCurrentDesktop`, `getDesktopHandles`, `getWindow`, `findWindow`, `getWindowNames`, `getOpenedWindows`, `getOpenedWindowNames`, `getParentWindow`, `getSibling`, `getQuality`, `transform`, `convertPointToScreen`, `createPopupMenu`, `getScreenIndex`, `setScreenIndex`, `getScreens`, `isTouchscreenModeEnabled`, `setTouchscreenModeEnabled`, `showNumericKeypad`, `showTouchscreenKeyboard`, `openDiagnostics`

### system.nav (12)
`centerWindow`, `closeParentWindow`, `closeWindow`, `desktop`, `getCurrentWindow`, `goBack`, `goForward`, `goHome`, `openWindow`, `openWindowInstance`, `swapTo`, `swapWindow`

### system.net (10)
`httpGet`, `httpPost`, `httpPut`, `httpDelete`, `httpClient`, `openURL`, `sendEmail`, `getHostName`, `getIpAddress`, `getRemoteServers`

### system.opc (11)
`browse`, `browseServer`, `browseSimple`, `getServers`, `getServerState`, `isServerEnabled`, `readValue`, `readValues`, `setServerEnabled`, `writeValue`, `writeValues`

### system.perspective (17)
`sendMessage`, `print`, `navigate`, `openPopup`, `closePopup`, `togglePopup`, `getSessionInfo`, `getProjectInfo`, `openDock`, `closeDock`, `toggleDock`, `refresh`, `setTheme`, `vibrate`, `navigateForward`, `navigateBack`, `download`

### system.security (9)
`getRoles`, `getUsername`, `getUserRoles`, `isScreenLocked`, `lockScreen`, `logout`, `switchUser`, `unlockScreen`, `validateUser`

### system.tag (20)
`readBlocking`, `readAsync`, `writeBlocking`, `writeAsync`, `exists`, `queryTagHistory`, `browse`, `configure`, `getConfiguration`, `deleteTags`, `copy`, `move`, `rename`, `exportTags`, `importTags`, `query`, `browseHistoricalTags`, `queryTagCalculations`, `storeTagHistory`, `requestGroupExecution`

### system.user (27)
`addCompositeSchedule`, `addHoliday`, `addRole`, `addSchedule`, `addUser`, `createScheduleAdjustment`, `editHoliday`, `editRole`, `editSchedule`, `editUser`, `getHoliday`, `getHolidayNames`, `getHolidays`, `getNewUser`, `getRoles`, `getSchedule`, `getScheduledUsers`, `getScheduleNames`, `getSchedules`, `getUser`, `getUsers`, `getUserSources`, `isUserScheduled`, `removeHoliday`, `removeRole`, `removeSchedule`, `removeUser`

### system.util (10)
`getLogger`, `jsonDecode`, `jsonEncode`, `sendMessage`, `invokeAsynchronous`, `invokeLater`, `execute`, `getSystemFlags`, `getGlobals`, `setGlobals`

## Common Patterns

```python
# Tag reads — always list form, returns QualifiedValue list
values = system.tag.readBlocking(["[default]Path/To/Tag"])
val = values[0].value

# Parameterized queries — ALWAYS use runPrepQuery
results = system.db.runPrepQuery(
    "SELECT * FROM table WHERE id = ? AND status = ?",
    [myId, myStatus], "DatabaseName"
)

# Dataset iteration
for row in range(ds.getRowCount()):
    name = ds.getValueAt(row, "name")

# Logging
logger = system.util.getLogger("MyModule")
logger.info("Processing %s items" % count)

# Perspective messaging
system.perspective.sendMessage("updateChart", {"tagPath": path}, scope="page")
```

## Jython Module Cache & Script Reloading

Ignition's Jython runtime caches compiled script modules in `sys.modules`. This cache is **separate from the project scan**. Understanding the distinction is critical when editing scripts via git/filesystem:

### What a project scan does
- Tells Ignition "files changed on disk"
- Updates Ignition's internal resource index
- Notifies connected Designers to refresh

### What a project scan does NOT do
- Flush the Jython `sys.modules` bytecode cache
- Force re-import of already-loaded script modules
- Guarantee that the next function call uses the new code

### Symptom
You edit `code.py`, trigger a project scan (succeeds), call a function — and get `AttributeError` for a function you just added, or the old behavior persists. The scan succeeded but Jython is still running the cached bytecode.

### How to force script reload

> **Safety first:** Before bumping versions or triggering scans, **commit or stash your work**. The Git module handles project files well now, but a force scan can trigger the Designer or Git module to write back to disk — protecting your uncommitted changes avoids surprises.

**1. Bump `resource.json` version** — strongest signal to Ignition's change detection:
```json
{
  "scope": "A",
  "version": 2,
  ...
}
```
Increment the `version` field every time you modify `code.py`. This tells Ignition the resource has a new revision, not just a new file timestamp.

**2. Use `forceUpdate=true` on the scan** — forces Ignition to re-process all resources:
```bash
curl -k -X POST -H "X-Ignition-API-Token: $TOKEN" \
  "<gateway>/data/project-scan-endpoint/scan?updateDesigners=true&forceUpdate=true"
```

**3. Save from Designer** — triggers a full script recompile (not just a file scan).

**4. Restart the gateway** — nuclear option, always works.

### IMPORTANT: Always bump version when editing scripts

When you modify any `code.py` in `ignition/script-python/`, you MUST also increment the `version` field in the adjacent `resource.json`. Without this, the gateway may continue running stale bytecode even after a successful project scan.

**Before bumping versions:** commit or stash all pending changes. A force scan can cause the Designer or Git module to write back to the project directory, and uncommitted work could be overwritten.

## Anti-Patterns
- NEVER use string formatting in SQL — always `?` params
- NEVER shadow the `system` variable
- NEVER hardcode gateway URLs (localhost:8088)
- NEVER use `import *`
- NEVER use `getSibling()`/`getParent()` for component references
- NEVER edit `code.py` without bumping the adjacent `resource.json` version
- NEVER define view params without a corresponding `propConfig` entry with `paramDirection` — the runtime silently ignores parameters without it
