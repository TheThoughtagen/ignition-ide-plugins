---
description: Ignition system.* API reference — 14 modules, 239 functions. Use when writing Ignition Jython scripts.
user-invocable: false
---

# Ignition System API Reference

You are writing code for **Ignition SCADA** by Inductive Automation. Scripts run in **Jython 2.7** (Python 2.7 on JVM). The scripting API is `system.*`.

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

## Anti-Patterns
- NEVER use string formatting in SQL — always `?` params
- NEVER shadow the `system` variable
- NEVER hardcode gateway URLs (localhost:8088)
- NEVER use `import *`
- NEVER use `getSibling()`/`getParent()` for component references
