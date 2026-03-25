---
description: Run ignition-lint on files or the whole project. Usage — /ignition-scada:ignition-lint [file|directory|profile]
user-invocable: true
---

# Run ignition-lint

Run `ignition-lint` to validate Ignition project files. The linter checks Jython scripts, Perspective views, tag definitions, and expression bindings.

If `$ARGUMENTS` specifies a file or directory, lint that target. If it specifies a profile name (`full`, `scripts-only`, `perspective-only`, `naming-only`), use that profile on the project. If empty, lint the whole project with the `default` profile.

## Steps

1. Check that `ignition-lint` is installed. If not, tell the user to run `pip install ignition-lint-toolkit`.
2. Determine the target and profile from `$ARGUMENTS`.
3. Run the linter via Bash:

```bash
# Whole project
ignition-lint --project . --profile default

# Specific target
ignition-lint --target <path> --profile scripts-only

# Available profiles: default, full, scripts-only, perspective-only, naming-only
```

4. Review the output. For each issue found:
   - Explain what the diagnostic code means
   - Show the fix
   - Apply the fix if it's straightforward

## Diagnostic Code Reference

**Script issues:** `JYTHON_SYNTAX_ERROR`, `JYTHON_PRINT_STATEMENT`, `JYTHON_IMPORT_STAR`, `JYTHON_DEPRECATED_ITERITEMS`, `JYTHON_MIXED_INDENTATION`, `JYTHON_BAD_COMPONENT_REF`, `JYTHON_HARDCODED_LOCALHOST`, `JYTHON_HTTP_WITHOUT_EXCEPTION_HANDLING`, `IGNITION_SYSTEM_OVERRIDE`, `IGNITION_HARDCODED_GATEWAY`, `IGNITION_HARDCODED_DB`, `IGNITION_DEBUG_PRINT`, `IGNITION_UNKNOWN_SYSTEM_CALL`, `LONG_LINE`, `MISSING_DOCSTRING`

**Expression issues:** `EXPR_NOW_DEFAULT_POLLING`, `EXPR_NOW_LOW_POLLING`, `EXPR_UNKNOWN_FUNCTION`, `EXPR_INVALID_PROPERTY_REF`, `EXPR_BAD_COMPONENT_REF`

**Perspective issues:** `EMPTY_COMPONENT_NAME`, `GENERIC_COMPONENT_NAME`, `MISSING_TAG_PATH`, `MISSING_TAG_FALLBACK`, `MISSING_EXPRESSION`, `INVALID_BINDING_TYPE`, `UNUSED_CUSTOM_PROPERTY`, `UNUSED_PARAM_PROPERTY`, `PERFORMANCE_CONSIDERATION`, `ACCESSIBILITY_LABELING`

**Tag issues:** `INVALID_TAG_TYPE`, `MISSING_DATA_TYPE`, `MISSING_VALUE_SOURCE`, `MISSING_TYPE_ID`, `OPC_MISSING_CONFIG`, `EXPR_MISSING_EXPRESSION`, `HISTORY_NO_PROVIDER`
