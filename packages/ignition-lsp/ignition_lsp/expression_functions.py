"""Expression function catalog for Ignition expression language completions and hover.

Provides signatures, descriptions, parameter info, and completion snippets
for all known Ignition expression functions. The function names are imported
from ignition-lint's KNOWN_EXPRESSION_FUNCTIONS to keep the sets in sync.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Detailed catalog of expression functions with signatures and docs.
# Each entry: signature, description, category, params, return_type, snippet.
EXPRESSION_FUNCTIONS: dict[str, dict] = {
    # ── Math ──────────────────────────────────────────────────────────
    "abs": {
        "signature": "abs(value)",
        "description": "Returns the absolute value of a number.",
        "category": "Math",
        "params": [{"name": "value", "type": "Number"}],
        "return_type": "Number",
        "snippet": "abs(${1:value})$0",
    },
    "ceil": {
        "signature": "ceil(value)",
        "description": "Rounds a number up to the nearest integer.",
        "category": "Math",
        "params": [{"name": "value", "type": "Number"}],
        "return_type": "Integer",
        "snippet": "ceil(${1:value})$0",
    },
    "floor": {
        "signature": "floor(value)",
        "description": "Rounds a number down to the nearest integer.",
        "category": "Math",
        "params": [{"name": "value", "type": "Number"}],
        "return_type": "Integer",
        "snippet": "floor(${1:value})$0",
    },
    "max": {
        "signature": "max(a, b)",
        "description": "Returns the greater of two values.",
        "category": "Math",
        "params": [
            {"name": "a", "type": "Number"},
            {"name": "b", "type": "Number"},
        ],
        "return_type": "Number",
        "snippet": "max(${1:a}, ${2:b})$0",
    },
    "min": {
        "signature": "min(a, b)",
        "description": "Returns the lesser of two values.",
        "category": "Math",
        "params": [
            {"name": "a", "type": "Number"},
            {"name": "b", "type": "Number"},
        ],
        "return_type": "Number",
        "snippet": "min(${1:a}, ${2:b})$0",
    },
    "round": {
        "signature": "round(value)",
        "description": "Rounds a number to the nearest integer.",
        "category": "Math",
        "params": [{"name": "value", "type": "Number"}],
        "return_type": "Integer",
        "snippet": "round(${1:value})$0",
    },
    "sqrt": {
        "signature": "sqrt(value)",
        "description": "Returns the square root of a number.",
        "category": "Math",
        "params": [{"name": "value", "type": "Number"}],
        "return_type": "Double",
        "snippet": "sqrt(${1:value})$0",
    },
    "pow": {
        "signature": "pow(base, exponent)",
        "description": "Returns the value of base raised to the power of exponent.",
        "category": "Math",
        "params": [
            {"name": "base", "type": "Number"},
            {"name": "exponent", "type": "Number"},
        ],
        "return_type": "Double",
        "snippet": "pow(${1:base}, ${2:exponent})$0",
    },
    "log": {
        "signature": "log(value)",
        "description": "Returns the natural logarithm (base e) of a number.",
        "category": "Math",
        "params": [{"name": "value", "type": "Number"}],
        "return_type": "Double",
        "snippet": "log(${1:value})$0",
    },
    "mod": {
        "signature": "mod(dividend, divisor)",
        "description": "Returns the remainder of dividing dividend by divisor.",
        "category": "Math",
        "params": [
            {"name": "dividend", "type": "Number"},
            {"name": "divisor", "type": "Number"},
        ],
        "return_type": "Number",
        "snippet": "mod(${1:dividend}, ${2:divisor})$0",
    },
    "rand": {
        "signature": "rand()",
        "description": "Returns a random double between 0.0 (inclusive) and 1.0 (exclusive).",
        "category": "Math",
        "params": [],
        "return_type": "Double",
        "snippet": "rand()$0",
    },
    "signum": {
        "signature": "signum(value)",
        "description": "Returns the sign of a number: -1, 0, or 1.",
        "category": "Math",
        "params": [{"name": "value", "type": "Number"}],
        "return_type": "Integer",
        "snippet": "signum(${1:value})$0",
    },
    # ── String ────────────────────────────────────────────────────────
    "concat": {
        "signature": "concat(str1, str2, ...)",
        "description": "Concatenates two or more strings together.",
        "category": "String",
        "params": [
            {"name": "str1", "type": "String"},
            {"name": "str2", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "concat(${1:str1}, ${2:str2})$0",
    },
    "endsWith": {
        "signature": "endsWith(string, suffix)",
        "description": "Returns true if the string ends with the specified suffix.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "suffix", "type": "String"},
        ],
        "return_type": "Boolean",
        "snippet": "endsWith(${1:string}, ${2:suffix})$0",
    },
    "indexOf": {
        "signature": "indexOf(string, substring)",
        "description": (
            "Returns the index of the first occurrence of substring,"
            " or -1 if not found."
        ),
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "substring", "type": "String"},
        ],
        "return_type": "Integer",
        "snippet": "indexOf(${1:string}, ${2:substring})$0",
    },
    "left": {
        "signature": "left(string, count)",
        "description": "Returns the leftmost count characters of the string.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "count", "type": "Integer"},
        ],
        "return_type": "String",
        "snippet": "left(${1:string}, ${2:count})$0",
    },
    "len": {
        "signature": "len(string)",
        "description": "Returns the length of a string.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "Integer",
        "snippet": "len(${1:string})$0",
    },
    "lower": {
        "signature": "lower(string)",
        "description": "Converts a string to lowercase.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "String",
        "snippet": "lower(${1:string})$0",
    },
    "ltrim": {
        "signature": "ltrim(string)",
        "description": "Removes leading whitespace from a string.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "String",
        "snippet": "ltrim(${1:string})$0",
    },
    "mid": {
        "signature": "mid(string, start, length)",
        "description": (
            "Returns a substring starting at the given position"
            " with the specified length."
        ),
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "start", "type": "Integer"},
            {"name": "length", "type": "Integer"},
        ],
        "return_type": "String",
        "snippet": "mid(${1:string}, ${2:start}, ${3:length})$0",
    },
    "numberFormat": {
        "signature": "numberFormat(value, format)",
        "description": "Formats a number using the specified format pattern (Java DecimalFormat).",
        "category": "String",
        "params": [
            {"name": "value", "type": "Number"},
            {"name": "format", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "numberFormat(${1:value}, ${2:\"#,##0.00\"})$0",
    },
    "regexExtract": {
        "signature": "regexExtract(string, pattern)",
        "description": "Extracts the first match of a regex pattern from the string.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "pattern", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "regexExtract(${1:string}, ${2:pattern})$0",
    },
    "repeat": {
        "signature": "repeat(string, count)",
        "description": "Repeats a string the specified number of times.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "count", "type": "Integer"},
        ],
        "return_type": "String",
        "snippet": "repeat(${1:string}, ${2:count})$0",
    },
    "replace": {
        "signature": "replace(string, search, replacement)",
        "description": "Replaces all occurrences of search with replacement in the string.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "search", "type": "String"},
            {"name": "replacement", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "replace(${1:string}, ${2:search}, ${3:replacement})$0",
    },
    "reverse": {
        "signature": "reverse(string)",
        "description": "Reverses the characters in a string.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "String",
        "snippet": "reverse(${1:string})$0",
    },
    "right": {
        "signature": "right(string, count)",
        "description": "Returns the rightmost count characters of the string.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "count", "type": "Integer"},
        ],
        "return_type": "String",
        "snippet": "right(${1:string}, ${2:count})$0",
    },
    "rtrim": {
        "signature": "rtrim(string)",
        "description": "Removes trailing whitespace from a string.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "String",
        "snippet": "rtrim(${1:string})$0",
    },
    "split": {
        "signature": "split(string, delimiter)",
        "description": "Splits a string by the delimiter and returns an array.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "delimiter", "type": "String"},
        ],
        "return_type": "Array",
        "snippet": "split(${1:string}, ${2:delimiter})$0",
    },
    "startsWith": {
        "signature": "startsWith(string, prefix)",
        "description": "Returns true if the string starts with the specified prefix.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "prefix", "type": "String"},
        ],
        "return_type": "Boolean",
        "snippet": "startsWith(${1:string}, ${2:prefix})$0",
    },
    "substring": {
        "signature": "substring(string, start, end)",
        "description": "Returns a substring from start index to end index.",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "start", "type": "Integer"},
            {"name": "end", "type": "Integer"},
        ],
        "return_type": "String",
        "snippet": "substring(${1:string}, ${2:start}, ${3:end})$0",
    },
    "toStr": {
        "signature": "toStr(value)",
        "description": "Converts a value to its string representation.",
        "category": "String",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "String",
        "snippet": "toStr(${1:value})$0",
    },
    "trim": {
        "signature": "trim(string)",
        "description": "Removes leading and trailing whitespace from a string.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "String",
        "snippet": "trim(${1:string})$0",
    },
    "upper": {
        "signature": "upper(string)",
        "description": "Converts a string to uppercase.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "String",
        "snippet": "upper(${1:string})$0",
    },
    "urlEncode": {
        "signature": "urlEncode(string)",
        "description": "URL-encodes a string for safe use in URLs.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "String",
        "snippet": "urlEncode(${1:string})$0",
    },
    "urlDecode": {
        "signature": "urlDecode(string)",
        "description": "Decodes a URL-encoded string.",
        "category": "String",
        "params": [{"name": "string", "type": "String"}],
        "return_type": "String",
        "snippet": "urlDecode(${1:string})$0",
    },
    "unicodeNormalize": {
        "signature": "unicodeNormalize(string, form)",
        "description": "Normalizes a Unicode string to the specified form (NFC, NFD, NFKC, NFKD).",
        "category": "String",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "form", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "unicodeNormalize(${1:string}, ${2:\"NFC\"})$0",
    },
    # ── Date/Time ─────────────────────────────────────────────────────
    "dateArith": {
        "signature": "dateArith(date, field, amount)",
        "description": (
            "Adds or subtracts an amount from a date field"
            " (e.g., 'hour', 'day', 'month')."
        ),
        "category": "Date/Time",
        "params": [
            {"name": "date", "type": "Date"},
            {"name": "field", "type": "String"},
            {"name": "amount", "type": "Integer"},
        ],
        "return_type": "Date",
        "snippet": "dateArith(${1:date}, ${2:\"day\"}, ${3:amount})$0",
    },
    "dateDiff": {
        "signature": "dateDiff(date1, date2, field)",
        "description": "Returns the difference between two dates in the specified field units.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
            {"name": "field", "type": "String"},
        ],
        "return_type": "Long",
        "snippet": "dateDiff(${1:date1}, ${2:date2}, ${3:\"day\"})$0",
    },
    "dateExtract": {
        "signature": "dateExtract(date, field)",
        "description": "Extracts a field value from a date (e.g., 'year', 'month', 'day', 'hour').",
        "category": "Date/Time",
        "params": [
            {"name": "date", "type": "Date"},
            {"name": "field", "type": "String"},
        ],
        "return_type": "Integer",
        "snippet": "dateExtract(${1:date}, ${2:\"year\"})$0",
    },
    "dateFormat": {
        "signature": "dateFormat(date, format)",
        "description": "Formats a date using the specified format pattern (Java SimpleDateFormat).",
        "category": "Date/Time",
        "params": [
            {"name": "date", "type": "Date"},
            {"name": "format", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "dateFormat(${1:date}, ${2:\"yyyy-MM-dd HH:mm:ss\"})$0",
    },
    "dateParse": {
        "signature": "dateParse(string, format)",
        "description": "Parses a string into a Date using the specified format pattern.",
        "category": "Date/Time",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "format", "type": "String"},
        ],
        "return_type": "Date",
        "snippet": "dateParse(${1:string}, ${2:\"yyyy-MM-dd\"})$0",
    },
    "daysBetween": {
        "signature": "daysBetween(date1, date2)",
        "description": "Returns the number of days between two dates.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
        ],
        "return_type": "Long",
        "snippet": "daysBetween(${1:date1}, ${2:date2})$0",
    },
    "hoursBetween": {
        "signature": "hoursBetween(date1, date2)",
        "description": "Returns the number of hours between two dates.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
        ],
        "return_type": "Long",
        "snippet": "hoursBetween(${1:date1}, ${2:date2})$0",
    },
    "millisBetween": {
        "signature": "millisBetween(date1, date2)",
        "description": "Returns the number of milliseconds between two dates.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
        ],
        "return_type": "Long",
        "snippet": "millisBetween(${1:date1}, ${2:date2})$0",
    },
    "minutesBetween": {
        "signature": "minutesBetween(date1, date2)",
        "description": "Returns the number of minutes between two dates.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
        ],
        "return_type": "Long",
        "snippet": "minutesBetween(${1:date1}, ${2:date2})$0",
    },
    "monthsBetween": {
        "signature": "monthsBetween(date1, date2)",
        "description": "Returns the number of months between two dates.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
        ],
        "return_type": "Long",
        "snippet": "monthsBetween(${1:date1}, ${2:date2})$0",
    },
    "now": {
        "signature": "now(pollRate)",
        "description": (
            "Returns the current date/time. Polls at the specified"
            " rate in milliseconds. Defaults to 1000ms if no"
            " argument given. Use now(0) for event-driven updates."
        ),
        "category": "Date/Time",
        "params": [{"name": "pollRate", "type": "Integer", "optional": True}],
        "return_type": "Date",
        "snippet": "now(${1:5000})$0",
    },
    "secondsBetween": {
        "signature": "secondsBetween(date1, date2)",
        "description": "Returns the number of seconds between two dates.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
        ],
        "return_type": "Long",
        "snippet": "secondsBetween(${1:date1}, ${2:date2})$0",
    },
    "setTime": {
        "signature": "setTime(date, hour, minute, second)",
        "description": "Returns a new date with the time set to the specified values.",
        "category": "Date/Time",
        "params": [
            {"name": "date", "type": "Date"},
            {"name": "hour", "type": "Integer"},
            {"name": "minute", "type": "Integer"},
            {"name": "second", "type": "Integer"},
        ],
        "return_type": "Date",
        "snippet": "setTime(${1:date}, ${2:0}, ${3:0}, ${4:0})$0",
    },
    "toDate": {
        "signature": "toDate(value)",
        "description": (
            "Converts a value to a Date. Accepts epoch millis"
            " (long) or formatted strings."
        ),
        "category": "Date/Time",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Date",
        "snippet": "toDate(${1:value})$0",
    },
    "weeksBetween": {
        "signature": "weeksBetween(date1, date2)",
        "description": "Returns the number of weeks between two dates.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
        ],
        "return_type": "Long",
        "snippet": "weeksBetween(${1:date1}, ${2:date2})$0",
    },
    "yearsBetween": {
        "signature": "yearsBetween(date1, date2)",
        "description": "Returns the number of years between two dates.",
        "category": "Date/Time",
        "params": [
            {"name": "date1", "type": "Date"},
            {"name": "date2", "type": "Date"},
        ],
        "return_type": "Long",
        "snippet": "yearsBetween(${1:date1}, ${2:date2})$0",
    },
    # ── Logic / Comparison ────────────────────────────────────────────
    "if": {
        "signature": "if(condition, trueValue, falseValue)",
        "description": "Returns trueValue if condition is true, falseValue otherwise.",
        "category": "Logic",
        "params": [
            {"name": "condition", "type": "Boolean"},
            {"name": "trueValue", "type": "Any"},
            {"name": "falseValue", "type": "Any"},
        ],
        "return_type": "Any",
        "snippet": "if(${1:condition}, ${2:trueValue}, ${3:falseValue})$0",
    },
    "switch": {
        "signature": "switch(value, case1, result1, ..., default)",
        "description": (
            "Compares value against cases and returns the"
            " matching result. Falls back to default."
        ),
        "category": "Logic",
        "params": [
            {"name": "value", "type": "Any"},
            {"name": "case1", "type": "Any"},
            {"name": "result1", "type": "Any"},
            {"name": "default", "type": "Any"},
        ],
        "return_type": "Any",
        "snippet": "switch(${1:value}, ${2:case1}, ${3:result1}, ${4:default})$0",
    },
    "coalesce": {
        "signature": "coalesce(value1, value2, ...)",
        "description": "Returns the first non-null value from the arguments.",
        "category": "Logic",
        "params": [
            {"name": "value1", "type": "Any"},
            {"name": "value2", "type": "Any"},
        ],
        "return_type": "Any",
        "snippet": "coalesce(${1:value1}, ${2:value2})$0",
    },
    "choose": {
        "signature": "choose(index, value0, value1, ...)",
        "description": "Returns the value at the specified 0-based index from the argument list.",
        "category": "Logic",
        "params": [
            {"name": "index", "type": "Integer"},
            {"name": "value0", "type": "Any"},
            {"name": "value1", "type": "Any"},
        ],
        "return_type": "Any",
        "snippet": "choose(${1:index}, ${2:value0}, ${3:value1})$0",
    },
    "isNull": {
        "signature": "isNull(value)",
        "description": "Returns true if the value is null.",
        "category": "Logic",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Boolean",
        "snippet": "isNull(${1:value})$0",
    },
    "hasChanged": {
        "signature": "hasChanged(value)",
        "description": "Returns true if the value has changed since the last evaluation.",
        "category": "Logic",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Boolean",
        "snippet": "hasChanged(${1:value})$0",
    },
    "previousValue": {
        "signature": "previousValue(value)",
        "description": "Returns the previous value from the last evaluation cycle.",
        "category": "Logic",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Any",
        "snippet": "previousValue(${1:value})$0",
    },
    "qualify": {
        "signature": "qualify(tagPath)",
        "description": "Qualifies a tag path with the current provider, resolving relative paths.",
        "category": "Logic",
        "params": [{"name": "tagPath", "type": "String"}],
        "return_type": "String",
        "snippet": "qualify(${1:tagPath})$0",
    },
    # ── Type Casting ──────────────────────────────────────────────────
    "toBool": {
        "signature": "toBool(value)",
        "description": "Converts a value to a Boolean.",
        "category": "Type Casting",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Boolean",
        "snippet": "toBool(${1:value})$0",
    },
    "toColor": {
        "signature": "toColor(red, green, blue)",
        "description": "Creates a Color from red, green, blue components (0-255) or a hex string.",
        "category": "Type Casting",
        "params": [
            {"name": "red", "type": "Integer"},
            {"name": "green", "type": "Integer"},
            {"name": "blue", "type": "Integer"},
        ],
        "return_type": "Color",
        "snippet": "toColor(${1:red}, ${2:green}, ${3:blue})$0",
    },
    "toDataSet": {
        "signature": "toDataSet(value)",
        "description": "Converts a value to a DataSet.",
        "category": "Type Casting",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "DataSet",
        "snippet": "toDataSet(${1:value})$0",
    },
    "toDouble": {
        "signature": "toDouble(value)",
        "description": "Converts a value to a Double.",
        "category": "Type Casting",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Double",
        "snippet": "toDouble(${1:value})$0",
    },
    "toFloat": {
        "signature": "toFloat(value)",
        "description": "Converts a value to a Float.",
        "category": "Type Casting",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Float",
        "snippet": "toFloat(${1:value})$0",
    },
    "toInt": {
        "signature": "toInt(value)",
        "description": "Converts a value to an Integer.",
        "category": "Type Casting",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Integer",
        "snippet": "toInt(${1:value})$0",
    },
    "toLong": {
        "signature": "toLong(value)",
        "description": "Converts a value to a Long.",
        "category": "Type Casting",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "Long",
        "snippet": "toLong(${1:value})$0",
    },
    # ── Aggregate / Dataset ───────────────────────────────────────────
    "avg": {
        "signature": "avg(values...)",
        "description": "Returns the average of the given numeric values.",
        "category": "Aggregate",
        "params": [{"name": "values", "type": "Number..."}],
        "return_type": "Double",
        "snippet": "avg(${1:value1}, ${2:value2})$0",
    },
    "columnCount": {
        "signature": "columnCount(dataset)",
        "description": "Returns the number of columns in a dataset.",
        "category": "Dataset",
        "params": [{"name": "dataset", "type": "DataSet"}],
        "return_type": "Integer",
        "snippet": "columnCount(${1:dataset})$0",
    },
    "forEach": {
        "signature": "forEach(dataset, expression)",
        "description": (
            "Evaluates an expression for each row in the dataset"
            " and returns the results."
        ),
        "category": "Dataset",
        "params": [
            {"name": "dataset", "type": "DataSet"},
            {"name": "expression", "type": "String"},
        ],
        "return_type": "Array",
        "snippet": "forEach(${1:dataset}, ${2:expression})$0",
    },
    "getColumn": {
        "signature": "getColumn(dataset, columnIndex)",
        "description": "Returns a column from a dataset as an array.",
        "category": "Dataset",
        "params": [
            {"name": "dataset", "type": "DataSet"},
            {"name": "columnIndex", "type": "Integer"},
        ],
        "return_type": "Array",
        "snippet": "getColumn(${1:dataset}, ${2:0})$0",
    },
    "hasRows": {
        "signature": "hasRows(dataset)",
        "description": "Returns true if the dataset has at least one row.",
        "category": "Dataset",
        "params": [{"name": "dataset", "type": "DataSet"}],
        "return_type": "Boolean",
        "snippet": "hasRows(${1:dataset})$0",
    },
    "lookup": {
        "signature": "lookup(dataset, lookupColumn, lookupValue, resultColumn)",
        "description": (
            "Searches a dataset column for a value and returns"
            " the corresponding value from another column."
        ),
        "category": "Dataset",
        "params": [
            {"name": "dataset", "type": "DataSet"},
            {"name": "lookupColumn", "type": "Integer"},
            {"name": "lookupValue", "type": "Any"},
            {"name": "resultColumn", "type": "Integer"},
        ],
        "return_type": "Any",
        "snippet": "lookup(${1:dataset}, ${2:0}, ${3:value}, ${4:1})$0",
    },
    "rowCount": {
        "signature": "rowCount(dataset)",
        "description": "Returns the number of rows in a dataset.",
        "category": "Dataset",
        "params": [{"name": "dataset", "type": "DataSet"}],
        "return_type": "Integer",
        "snippet": "rowCount(${1:dataset})$0",
    },
    "sum": {
        "signature": "sum(values...)",
        "description": "Returns the sum of the given numeric values.",
        "category": "Aggregate",
        "params": [{"name": "values", "type": "Number..."}],
        "return_type": "Number",
        "snippet": "sum(${1:value1}, ${2:value2})$0",
    },
    "dataSetToJSON": {
        "signature": "dataSetToJSON(dataset)",
        "description": "Converts a DataSet to a JSON string representation.",
        "category": "Dataset",
        "params": [{"name": "dataset", "type": "DataSet"}],
        "return_type": "String",
        "snippet": "dataSetToJSON(${1:dataset})$0",
    },
    "jsonToDataSet": {
        "signature": "jsonToDataSet(json)",
        "description": "Converts a JSON string to a DataSet.",
        "category": "Dataset",
        "params": [{"name": "json", "type": "String"}],
        "return_type": "DataSet",
        "snippet": "jsonToDataSet(${1:json})$0",
    },
    # ── Color ─────────────────────────────────────────────────────────
    "chooseColor": {
        "signature": "chooseColor(index, color0, color1, ...)",
        "description": "Returns the color at the specified index from the argument list.",
        "category": "Color",
        "params": [
            {"name": "index", "type": "Integer"},
            {"name": "color0", "type": "Color"},
            {"name": "color1", "type": "Color"},
        ],
        "return_type": "Color",
        "snippet": "chooseColor(${1:index}, ${2:color0}, ${3:color1})$0",
    },
    "colorMix": {
        "signature": "colorMix(color1, color2, bias)",
        "description": "Blends two colors together. Bias 0.0 = color1, 1.0 = color2.",
        "category": "Color",
        "params": [
            {"name": "color1", "type": "Color"},
            {"name": "color2", "type": "Color"},
            {"name": "bias", "type": "Double"},
        ],
        "return_type": "Color",
        "snippet": "colorMix(${1:color1}, ${2:color2}, ${3:0.5})$0",
    },
    # ── JSON ──────────────────────────────────────────────────────────
    "jsonDecode": {
        "signature": "jsonDecode(json)",
        "description": "Parses a JSON string and returns the resulting object.",
        "category": "JSON",
        "params": [{"name": "json", "type": "String"}],
        "return_type": "Any",
        "snippet": "jsonDecode(${1:json})$0",
    },
    "jsonEncode": {
        "signature": "jsonEncode(value)",
        "description": "Converts a value to its JSON string representation.",
        "category": "JSON",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "String",
        "snippet": "jsonEncode(${1:value})$0",
    },
    "jsonMerge": {
        "signature": "jsonMerge(json1, json2)",
        "description": "Deep-merges two JSON objects. Values in json2 override json1.",
        "category": "JSON",
        "params": [
            {"name": "json1", "type": "String"},
            {"name": "json2", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "jsonMerge(${1:json1}, ${2:json2})$0",
    },
    "jsonDelete": {
        "signature": "jsonDelete(json, path)",
        "description": "Removes the value at the specified path from a JSON string.",
        "category": "JSON",
        "params": [
            {"name": "json", "type": "String"},
            {"name": "path", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "jsonDelete(${1:json}, ${2:path})$0",
    },
    "jsonKeys": {
        "signature": "jsonKeys(json)",
        "description": "Returns the keys of a JSON object as an array.",
        "category": "JSON",
        "params": [{"name": "json", "type": "String"}],
        "return_type": "Array",
        "snippet": "jsonKeys(${1:json})$0",
    },
    "jsonSet": {
        "signature": "jsonSet(json, path, value)",
        "description": "Sets a value at the specified path in a JSON string.",
        "category": "JSON",
        "params": [
            {"name": "json", "type": "String"},
            {"name": "path", "type": "String"},
            {"name": "value", "type": "Any"},
        ],
        "return_type": "String",
        "snippet": "jsonSet(${1:json}, ${2:path}, ${3:value})$0",
    },
    "jsonLength": {
        "signature": "jsonLength(json)",
        "description": "Returns the number of elements in a JSON array or keys in a JSON object.",
        "category": "JSON",
        "params": [{"name": "json", "type": "String"}],
        "return_type": "Integer",
        "snippet": "jsonLength(${1:json})$0",
    },
    "jsonValueByKey": {
        "signature": "jsonValueByKey(json, key)",
        "description": "Returns the value associated with a key in a JSON object.",
        "category": "JSON",
        "params": [
            {"name": "json", "type": "String"},
            {"name": "key", "type": "String"},
        ],
        "return_type": "Any",
        "snippet": "jsonValueByKey(${1:json}, ${2:key})$0",
    },
    # ── Tag Quality ───────────────────────────────────────────────────
    "hasQuality": {
        "signature": "hasQuality(value, quality)",
        "description": "Returns true if the qualified value has the specified quality code.",
        "category": "Tag Quality",
        "params": [
            {"name": "value", "type": "QualifiedValue"},
            {"name": "quality", "type": "String"},
        ],
        "return_type": "Boolean",
        "snippet": "hasQuality(${1:value}, ${2:quality})$0",
    },
    "isGood": {
        "signature": "isGood(value)",
        "description": "Returns true if the qualified value has Good quality.",
        "category": "Tag Quality",
        "params": [{"name": "value", "type": "QualifiedValue"}],
        "return_type": "Boolean",
        "snippet": "isGood(${1:value})$0",
    },
    "isBad": {
        "signature": "isBad(value)",
        "description": "Returns true if the qualified value has Bad quality.",
        "category": "Tag Quality",
        "params": [{"name": "value", "type": "QualifiedValue"}],
        "return_type": "Boolean",
        "snippet": "isBad(${1:value})$0",
    },
    "isUncertain": {
        "signature": "isUncertain(value)",
        "description": "Returns true if the qualified value has Uncertain quality.",
        "category": "Tag Quality",
        "params": [{"name": "value", "type": "QualifiedValue"}],
        "return_type": "Boolean",
        "snippet": "isUncertain(${1:value})$0",
    },
    "isNotGood": {
        "signature": "isNotGood(value)",
        "description": "Returns true if the qualified value does not have Good quality.",
        "category": "Tag Quality",
        "params": [{"name": "value", "type": "QualifiedValue"}],
        "return_type": "Boolean",
        "snippet": "isNotGood(${1:value})$0",
    },
    "tag": {
        "signature": "tag(tagPath)",
        "description": "Reads the value of a tag at the specified path.",
        "category": "Tag",
        "params": [{"name": "tagPath", "type": "String"}],
        "return_type": "QualifiedValue",
        "snippet": "tag(${1:tagPath})$0",
    },
    "tagCount": {
        "signature": "tagCount(folderPath)",
        "description": "Returns the number of tags in the specified folder.",
        "category": "Tag",
        "params": [{"name": "folderPath", "type": "String"}],
        "return_type": "Integer",
        "snippet": "tagCount(${1:folderPath})$0",
    },
    # ── Advanced / Perspective ────────────────────────────────────────
    "binEncode": {
        "signature": "binEncode(data, encoding)",
        "description": (
            "Encodes binary data to a string using the specified"
            " encoding (e.g., 'Base64', 'Hex')."
        ),
        "category": "Advanced",
        "params": [
            {"name": "data", "type": "ByteArray"},
            {"name": "encoding", "type": "String"},
        ],
        "return_type": "String",
        "snippet": "binEncode(${1:data}, ${2:\"Base64\"})$0",
    },
    "binDecode": {
        "signature": "binDecode(string, encoding)",
        "description": "Decodes a string to binary data using the specified encoding.",
        "category": "Advanced",
        "params": [
            {"name": "string", "type": "String"},
            {"name": "encoding", "type": "String"},
        ],
        "return_type": "ByteArray",
        "snippet": "binDecode(${1:string}, ${2:\"Base64\"})$0",
    },
    "forceQuality": {
        "signature": "forceQuality(value, qualityCode)",
        "description": "Returns a new qualified value with the specified quality code.",
        "category": "Advanced",
        "params": [
            {"name": "value", "type": "Any"},
            {"name": "qualityCode", "type": "Integer"},
        ],
        "return_type": "QualifiedValue",
        "snippet": "forceQuality(${1:value}, ${2:192})$0",
    },
    "getMillis": {
        "signature": "getMillis()",
        "description": "Returns the current system time in milliseconds since epoch.",
        "category": "Advanced",
        "params": [],
        "return_type": "Long",
        "snippet": "getMillis()$0",
    },
    "htmlToPlain": {
        "signature": "htmlToPlain(html)",
        "description": "Strips HTML tags from a string and returns plain text.",
        "category": "Advanced",
        "params": [{"name": "html", "type": "String"}],
        "return_type": "String",
        "snippet": "htmlToPlain(${1:html})$0",
    },
    "isAuthorized": {
        "signature": "isAuthorized(requiredRoles)",
        "description": "Returns true if the current user has one of the required security roles.",
        "category": "Advanced",
        "params": [{"name": "requiredRoles", "type": "String..."}],
        "return_type": "Boolean",
        "snippet": "isAuthorized(${1:\"Administrator\"})$0",
    },
    "mapLat": {
        "signature": "mapLat(value)",
        "description": "Returns the latitude component of a map coordinate value.",
        "category": "Advanced",
        "params": [{"name": "value", "type": "MapCoordinate"}],
        "return_type": "Double",
        "snippet": "mapLat(${1:value})$0",
    },
    "mapLng": {
        "signature": "mapLng(value)",
        "description": "Returns the longitude component of a map coordinate value.",
        "category": "Advanced",
        "params": [{"name": "value", "type": "MapCoordinate"}],
        "return_type": "Double",
        "snippet": "mapLng(${1:value})$0",
    },
    "runScript": {
        "signature": "runScript(scriptPath, pollRate, args...)",
        "description": (
            "Executes a project script function and returns its"
            " result. Polls at the specified rate (ms)."
        ),
        "category": "Advanced",
        "params": [
            {"name": "scriptPath", "type": "String"},
            {"name": "pollRate", "type": "Integer"},
            {"name": "args", "type": "Any..."},
        ],
        "return_type": "Any",
        "snippet": "runScript(${1:\"project.library.function\"}, ${2:5000})$0",
    },
    "typeOf": {
        "signature": "typeOf(value)",
        "description": "Returns a string representation of the value's type.",
        "category": "Advanced",
        "params": [{"name": "value", "type": "Any"}],
        "return_type": "String",
        "snippet": "typeOf(${1:value})$0",
    },
}


def _verify_catalog_sync() -> None:
    """Log a warning if the catalog drifts from ignition-lint's known functions.

    Called once at import time. Non-fatal — the LSP still works even if
    ignition-lint is not installed.
    """
    try:
        from ignition_lint.validators.expression import KNOWN_EXPRESSION_FUNCTIONS
    except ImportError:
        return

    catalog_names = set(EXPRESSION_FUNCTIONS.keys())
    lint_names = set(KNOWN_EXPRESSION_FUNCTIONS)
    missing = lint_names - catalog_names
    if missing:
        logger.warning(
            "Expression catalog is missing functions from ignition-lint: %s",
            ", ".join(sorted(missing)),
        )


_verify_catalog_sync()
