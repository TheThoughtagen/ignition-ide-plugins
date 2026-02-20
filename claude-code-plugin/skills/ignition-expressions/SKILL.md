---
description: Ignition expression language reference — 104 functions. Use when writing tag expressions or Perspective binding expressions.
user-invocable: false
---

# Ignition Expression Language Reference

Ignition expressions are used in tag expression bindings and Perspective property bindings. They are **NOT Python** — they use a distinct function-based syntax.

## Syntax

```
if({[.]value} > 100, "High", "Normal")
dateFormat(now(5000), "HH:mm:ss")
tag("[default]Path/To/Tag")
runScript("project.library.myFunc", 5000, arg1)
```

**Property references:** `{this.props.value}`, `{view.custom.myProp}`, `{view.params.x}`, `{[.]tagProperty}`

## Functions (104 total)

### Math (12)
- `abs(value)` — Absolute value
- `ceil(value)` — Round up
- `floor(value)` — Round down
- `log(value)` — Natural logarithm
- `max(a, b)` — Greater of two values
- `min(a, b)` — Lesser of two values
- `mod(dividend, divisor)` — Remainder
- `pow(base, exponent)` — Exponentiation
- `rand()` — Random double 0.0-1.0
- `round(value)` — Round to nearest integer
- `signum(value)` — Sign (-1, 0, 1)
- `sqrt(value)` — Square root

### String (24)
- `concat(str1, str2, ...)` — Concatenate strings
- `endsWith(string, suffix)` — Suffix check
- `indexOf(string, substring)` — First occurrence index (-1 if not found)
- `left(string, count)` — Leftmost characters
- `len(string)` — String length
- `lower(string)` — To lowercase
- `ltrim(string)` — Remove leading whitespace
- `mid(string, start, length)` — Substring by position and length
- `numberFormat(value, format)` — Format number (Java DecimalFormat)
- `regexExtract(string, pattern)` — Extract regex match
- `repeat(string, count)` — Repeat string
- `replace(string, search, replacement)` — Replace all occurrences
- `reverse(string)` — Reverse characters
- `right(string, count)` — Rightmost characters
- `rtrim(string)` — Remove trailing whitespace
- `split(string, delimiter)` — Split into array
- `startsWith(string, prefix)` — Prefix check
- `substring(string, start, end)` — Substring by indices
- `toStr(value)` — Convert to string
- `trim(string)` — Remove surrounding whitespace
- `unicodeNormalize(string, form)` — Unicode normalization (NFC, NFD, NFKC, NFKD)
- `upper(string)` — To uppercase
- `urlDecode(string)` — URL decode
- `urlEncode(string)` — URL encode

### Date/Time (16)
- `dateArith(date, field, amount)` — Add/subtract from date field ("hour", "day", "month")
- `dateDiff(date1, date2, field)` — Difference in field units
- `dateExtract(date, field)` — Extract field ("year", "month", "day", "hour")
- `dateFormat(date, format)` — Format date (Java SimpleDateFormat)
- `dateParse(string, format)` — Parse string to date
- `daysBetween(date1, date2)` — Days between dates
- `hoursBetween(date1, date2)` — Hours between dates
- `millisBetween(date1, date2)` — Millis between dates
- `minutesBetween(date1, date2)` — Minutes between dates
- `monthsBetween(date1, date2)` — Months between dates
- `now(pollRate)` — Current date/time. **Always specify rate:** `now(5000)` or `now(0)`
- `secondsBetween(date1, date2)` — Seconds between dates
- `setTime(date, hour, minute, second)` — Set time components
- `toDate(value)` — Convert to date (epoch millis or string)
- `weeksBetween(date1, date2)` — Weeks between dates
- `yearsBetween(date1, date2)` — Years between dates

### Logic (8)
- `choose(index, value0, value1, ...)` — Select by 0-based index
- `coalesce(value1, value2, ...)` — First non-null value
- `hasChanged(value)` — True if value changed since last evaluation
- `if(condition, trueValue, falseValue)` — Conditional
- `isNull(value)` — Null check
- `previousValue(value)` — Previous evaluation's value
- `qualify(tagPath)` — Qualify tag path with current provider
- `switch(value, case1, result1, ..., default)` — Case matching

### Type Casting (7)
`toBool`, `toColor(r,g,b)`, `toDataSet`, `toDouble`, `toFloat`, `toInt`, `toLong`

### Dataset (10)
- `avg(values...)` — Average
- `columnCount(dataset)` — Column count
- `dataSetToJSON(dataset)` — Dataset to JSON string
- `forEach(dataset, expression)` — Evaluate per row
- `getColumn(dataset, columnIndex)` — Column as array
- `hasRows(dataset)` — Has at least one row
- `jsonToDataSet(json)` — JSON to dataset
- `lookup(dataset, lookupCol, lookupVal, resultCol)` — Column lookup
- `rowCount(dataset)` — Row count
- `sum(values...)` — Sum

### JSON (8)
- `jsonDecode(json)` — Parse JSON
- `jsonDelete(json, path)` — Remove at path
- `jsonEncode(value)` — Serialize to JSON
- `jsonKeys(json)` — Object keys
- `jsonLength(json)` — Array/object length
- `jsonMerge(json1, json2)` — Deep merge (json2 wins)
- `jsonSet(json, path, value)` — Set at path
- `jsonValueByKey(json, key)` — Get by key

### Tag Quality (7)
- `hasQuality(value, quality)` — Check quality code
- `isBad(value)` — Bad quality
- `isGood(value)` — Good quality
- `isNotGood(value)` — Not good quality
- `isUncertain(value)` — Uncertain quality
- `tag(tagPath)` — Read tag value
- `tagCount(folderPath)` — Count tags in folder

### Color (2)
- `chooseColor(index, color0, color1, ...)` — Select color by index
- `colorMix(color1, color2, bias)` — Blend colors (0.0=color1, 1.0=color2)

### Advanced (10)
- `binDecode(string, encoding)` — Decode binary (Base64, Hex)
- `binEncode(data, encoding)` — Encode binary
- `forceQuality(value, qualityCode)` — Set quality code
- `getMillis()` — Current epoch millis
- `htmlToPlain(html)` — Strip HTML tags
- `isAuthorized(requiredRoles...)` — Security role check
- `mapLat(value)` — Latitude from map coordinate
- `mapLng(value)` — Longitude from map coordinate
- `runScript(scriptPath, pollRate, args...)` — Call project script
- `typeOf(value)` — Type name string

## Key Tips
- `now()` defaults to 1000ms polling — always use `now(5000)` or `now(0)`
- `runScript("project.library.func", 5000, arg1)` calls project scripts from expressions
- Avoid `getSibling()`, `getParent()`, `getChild()`, `getComponent()` — break on restructure
- Property refs: `{this.props.X}` (own), `{view.custom.X}` (view), `{view.params.X}` (params)
