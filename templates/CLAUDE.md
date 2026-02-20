# CLAUDE.md — Ignition Project

> Copy the `templates/` contents into the root of your Ignition project to give
> Claude Code full domain awareness when writing scripts, expressions, and views.
>
> **What you get:**
> - `CLAUDE.md` — This file. API reference, expression language, coding conventions.
> - `.claude/settings.json` — Hook that auto-runs ignition-lint after every file edit.
> - `.claude/hooks/ignition-lint.sh` — Lint script that feeds diagnostics back to Claude.
>
> **Prerequisite:** `pip install ignition-lint-toolkit`

## What is Ignition?

Ignition is a SCADA/ICS platform by Inductive Automation. Projects are stored as JSON files containing embedded Python (Jython 2.7) scripts and expression language bindings. The scripting API is accessed via `system.*` functions (e.g., `system.tag.readBlocking()`, `system.db.runPrepQuery()`).

## Project Structure

```text
project.json              # Project metadata (name, version, description)
com.inductiveautomation.perspective/
  views/
    MyView/
      view.json           # Perspective view definition (components, bindings)
      resource.json       # View metadata
    ...
com.inductiveautomation.ignition.common.script/
  script-python/
    project/              # Project-scoped scripts
      library/
        code.py           # Callable via project.library.functionName()
    shared/               # Gateway-scoped shared scripts
      utils/
        code.py           # Callable via shared.utils.functionName()
ignition/tags/
  default/
    tags.json             # Tag definitions with expressions and event scripts
```

## Jython Conventions

Scripts run in **Jython 2.7** (Python 2.7 syntax on the JVM). Key differences from Python 3:

- Use `print()` as a function (works in both Jython 2.7 and 3)
- `str` is Java String; use `unicode` for Unicode-safe operations
- Java classes are directly importable: `from java.util import ArrayList`
- No f-strings, no walrus operator, no type hints at runtime
- Use `system.util.getLogger()` instead of `print()` for production logging
- Global scope in script modules persists across calls — avoid mutable globals

## Ignition System API Reference

14 modules, 239 functions. These are the primary scripting APIs.

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

### Common Patterns

```python
# Tag reads — always use list form, returns QualifiedValue list
values = system.tag.readBlocking(["[default]Path/To/Tag"])
val = values[0].value
quality = values[0].quality

# Parameterized queries — ALWAYS use runPrepQuery, never string formatting
results = system.db.runPrepQuery(
    "SELECT * FROM table WHERE id = ? AND status = ?",
    [myId, myStatus],
    "DatabaseName"
)

# Dataset iteration
ds = system.db.runPrepQuery("SELECT name, value FROM config", [], "DB")
for row in range(ds.getRowCount()):
    name = ds.getValueAt(row, "name")
    value = ds.getValueAt(row, "value")

# Perspective message handlers
system.perspective.sendMessage("updateChart", {"tagPath": path}, scope="page")

# Logging (preferred over print)
logger = system.util.getLogger("MyModule")
logger.info("Processing %s items" % count)
```

## Expression Language Reference

Ignition expressions are used in tag expression bindings and Perspective property bindings. They are NOT Python — they use a distinct function-based syntax.

**Syntax:** `if({[.]value} > 100, "High", "Normal")`, `dateFormat(now(5000), "HH:mm:ss")`, `tag("[default]Path/To/Tag")`

**Property references:** `{this.props.value}`, `{view.custom.myProp}`, `{[.]tagProperty}`

### Functions by Category (104 total)

**Math:** `abs`, `ceil`, `floor`, `log`, `max`, `min`, `mod`, `pow`, `rand`, `round`, `signum`, `sqrt`

**String:** `concat`, `endsWith`, `indexOf`, `left`, `len`, `lower`, `ltrim`, `mid`, `numberFormat`, `regexExtract`, `repeat`, `replace`, `reverse`, `right`, `rtrim`, `split`, `startsWith`, `substring`, `toStr`, `trim`, `unicodeNormalize`, `upper`, `urlDecode`, `urlEncode`

**Date/Time:** `dateArith`, `dateDiff`, `dateExtract`, `dateFormat`, `dateParse`, `daysBetween`, `hoursBetween`, `millisBetween`, `minutesBetween`, `monthsBetween`, `now`, `secondsBetween`, `setTime`, `toDate`, `weeksBetween`, `yearsBetween`

**Logic:** `choose`, `coalesce`, `hasChanged`, `if`, `isNull`, `previousValue`, `qualify`, `switch`

**Type Casting:** `toBool`, `toColor`, `toDataSet`, `toDouble`, `toFloat`, `toInt`, `toLong`

**Dataset:** `avg`, `columnCount`, `dataSetToJSON`, `forEach`, `getColumn`, `hasRows`, `jsonToDataSet`, `lookup`, `rowCount`, `sum`

**JSON:** `jsonDecode`, `jsonDelete`, `jsonEncode`, `jsonKeys`, `jsonLength`, `jsonMerge`, `jsonSet`, `jsonValueByKey`

**Tag Quality:** `hasQuality`, `isBad`, `isGood`, `isNotGood`, `isUncertain`, `tag`, `tagCount`

**Color:** `chooseColor`, `colorMix`

**Advanced:** `binDecode`, `binEncode`, `forceQuality`, `getMillis`, `htmlToPlain`, `isAuthorized`, `mapLat`, `mapLng`, `runScript`, `typeOf`

### Expression Tips
- `now()` defaults to 1000ms polling — always specify a rate: `now(5000)` or `now(0)` for event-driven
- `runScript("project.library.myFunc", 5000, arg1, arg2)` calls project scripts from expressions
- Property refs use `{this.props.X}` (own), `{view.custom.X}` (view-level), `{view.params.X}` (params)
- Avoid `getSibling()`, `getParent()`, `getChild()`, `getComponent()` in expressions — they break on structural changes

## Linting with ignition-lint

### Installation

```bash
pip install ignition-lint-toolkit
```

### Automatic Linting (Claude Code Hook)

This project includes a `.claude/hooks/ignition-lint.sh` hook that **automatically runs ignition-lint** after every Write/Edit operation. Claude sees the diagnostics and can fix issues immediately.

The hook runs:
- `scripts-only` profile on `.py` files
- `perspective-only` profile on `view.json` files
- `full` profile on `tags.json` files

If ignition-lint is not installed, the hook silently exits. No action needed.

### Manual Usage

```bash
# Lint the entire project
ignition-lint --project . --profile full

# Lint specific targets
ignition-lint --target com.inductiveautomation.perspective/views/
ignition-lint --target ignition/tags/

# Profiles: default, perspective-only, scripts-only, naming-only, full
ignition-lint --project . --profile scripts-only

# JSON output for CI
ignition-lint --project . --report-format json

# Fail CI on warnings or worse
ignition-lint --project . --fail-on warning
```

### Diagnostic Codes

**Script diagnostics** (Jython/Python files):
- `JYTHON_SYNTAX_ERROR` — Syntax error in script
- `JYTHON_PRINT_STATEMENT` — Use `print()` function form
- `JYTHON_IMPORT_STAR` — Avoid `from X import *`
- `JYTHON_DEPRECATED_ITERITEMS` — Use `.items()` not `.iteritems()`
- `JYTHON_MIXED_INDENTATION` — Tabs and spaces mixed
- `JYTHON_BAD_COMPONENT_REF` — Fragile `getSibling`/`getParent` calls
- `JYTHON_HARDCODED_LOCALHOST` — Hardcoded localhost/127.0.0.1
- `JYTHON_HTTP_WITHOUT_EXCEPTION_HANDLING` — HTTP calls need try/except
- `IGNITION_SYSTEM_OVERRIDE` — Don't shadow the `system` variable
- `IGNITION_HARDCODED_GATEWAY` — Hardcoded gateway URL
- `IGNITION_HARDCODED_DB` — Hardcoded database URL
- `IGNITION_DEBUG_PRINT` — Use logger instead of print
- `IGNITION_UNKNOWN_SYSTEM_CALL` — Unknown `system.*` function
- `LONG_LINE` — Line exceeds 120 characters
- `MISSING_DOCSTRING` — Public function missing docstring

**Expression diagnostics** (bindings in views and tags):
- `EXPR_NOW_DEFAULT_POLLING` — `now()` without explicit poll rate
- `EXPR_NOW_LOW_POLLING` — `now()` with rate < 5000ms
- `EXPR_UNKNOWN_FUNCTION` — Unrecognized expression function
- `EXPR_INVALID_PROPERTY_REF` — Property reference contains spaces
- `EXPR_BAD_COMPONENT_REF` — Component traversal in expression

**Perspective diagnostics** (view.json files):
- `EMPTY_COMPONENT_NAME` — Component has no name
- `GENERIC_COMPONENT_NAME` — Name like "Button" or "Label"
- `MISSING_TAG_PATH` — Tag binding missing tagPath
- `MISSING_TAG_FALLBACK` — Tag binding should have fallback value
- `MISSING_EXPRESSION` — Expression binding has no expression
- `INVALID_BINDING_TYPE` — Unrecognized binding type
- `MISSING_SCRIPT_CODE` — Script transform has no code
- `UNUSED_CUSTOM_PROPERTY` — Custom property appears unreferenced
- `UNUSED_PARAM_PROPERTY` — Param property appears unreferenced
- `PERFORMANCE_CONSIDERATION` — Heavy component (flex-repeater, table)
- `ACCESSIBILITY_LABELING` — Interactive component needs labeling

**Tag diagnostics** (tags.json files):
- `INVALID_TAG_TYPE` — Invalid tagType value
- `MISSING_DATA_TYPE` — AtomicTag missing dataType
- `MISSING_VALUE_SOURCE` — AtomicTag missing valueSource
- `MISSING_TYPE_ID` — UdtInstance missing typeId
- `OPC_MISSING_CONFIG` — OPC tag missing opcServer/opcItemPath
- `EXPR_MISSING_EXPRESSION` — Expression tag with no expression
- `HISTORY_NO_PROVIDER` — History enabled without historyProvider

### Inline Suppression

```python
# ignition-lint: disable-line=JYTHON_PRINT_STATEMENT
print "legacy code"
```

## Anti-Patterns to Avoid

1. **Never use string formatting in SQL** — Always `runPrepQuery` with `?` params
2. **Never shadow `system`** — `system = something` breaks all API calls
3. **Never hardcode gateway URLs** — Use gateway network functions or config tags
4. **Never use `getSibling()`/`getParent()` in expressions** — Breaks on view restructuring
5. **Never use `import *`** — Pollutes namespace, hides dependencies
6. **Never rely on `now()` default polling** — Specify `now(5000)` or `now(0)` explicitly
7. **Avoid mutable globals in script modules** — They persist across calls and cause race conditions
