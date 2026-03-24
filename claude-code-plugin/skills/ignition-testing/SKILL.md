---
description: Ignition testing framework reference — writing and running Jython gateway tests. Use when writing tests, debugging test failures, or working with the testing.* modules.
user-invocable: false
---

# Ignition Testing Framework Reference

This project uses a custom Jython test framework that runs on the Ignition gateway. Tests execute in the gateway's script context with full access to `system.*` APIs, real tags, and database connections.

## Architecture

- **Test scripts** live in `ignition/script-python/` as `__tests__/code.py` inside any package
- **Test framework** (`testing.*` modules) may live in this project or be inherited from a parent project
- **WebDev endpoints** (`testing/run`, `testing/tags`) are always project-scoped — each project has its own
- **Test runner** discovers `__tests__/code.py` files by walking the filesystem, imports them, and executes `@test`-decorated functions

## Writing Tests

Create `ignition/script-python/<package>/__tests__/code.py` with a matching `resource.json`:

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
    from testing.assertions import assert_tag_value
    assert_tag_value("[WHK01]Path/To/Tag", expected_value)

@test
def test_system_call():
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

The `resource.json` alongside `code.py`:
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

## testing.decorators

| Decorator | Purpose |
|-----------|---------|
| `@test` | Marks a function as a test case. Runner discovers functions with `_is_test = True`. |
| `@skip(reason="")` | Skips the test. Apply BEFORE `@test`: `@skip("reason") @test def ...` |
| `@setup` | Module-level setup — runs once before all tests. Only one per module. |
| `@teardown` | Module-level teardown — runs once after all tests. Only one per module. |
| `@expected_error(ExceptionType)` | Test passes if the given exception is raised, fails otherwise. |

## testing.assertions

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

All raise `TestAssertionError` (subclass of `AssertionError`) with `actual` and `expected` attributes for structured reporting.

## testing.helpers

| Function | Purpose |
|----------|---------|
| `write_dataset_tag(tag_path, columns, types, rows)` | Create a real Ignition `DataSet` via `system.dataset.toDataSet()` and write to tag. Auto-reconfigures tag type if needed. Types: `String`, `Float8`, `Int4`, `Boolean`, `DateTime`. |
| `clear_dataset_tag(tag_path, columns, types)` | Write an empty DataSet to a tag (cleanup). |

## testing.runner

| Function | Purpose |
|----------|---------|
| `run_all(base_package="")` | Discover and run all `__tests__` modules. Optional `base_package` filter (e.g., `"core.mes"`). |
| `run_module(module_path)` | Run a specific module (e.g., `"core.mes.changeover.__tests__"`). |

Returns structured dict:
```python
{
    "passed": int, "failed": int, "skipped": int, "errors": int,
    "total": int, "duration_ms": int,
    "modules": [{"module": "...", "results": [{"name": "...", "status": "passed|failed|skipped|error", "message": "...", "duration_ms": int}]}]
}
```

## testing.reporter

| Function | Purpose |
|----------|---------|
| `to_json(results)` | JSON string |
| `to_console(results)` | Human-readable text for Script Console |
| `to_junit_xml(results)` | JUnit XML for CI integration |

## Running Tests

**From Script Console:**
```python
print testing.runner.run_all()
print testing.runner.run_module("core.mes.changeover.__tests__")
print testing.reporter.to_console(testing.runner.run_all())
```

**Via HTTP (WebDev endpoints):**
```bash
# Discover modules
curl -k -s "https://localhost:9043/system/webdev/<PROJECT>/testing/run?discover=true"

# Run all
curl -k -s -X POST "https://localhost:9043/system/webdev/<PROJECT>/testing/run"

# Run specific module
curl -k -s -X POST "https://localhost:9043/system/webdev/<PROJECT>/testing/run?module=core.mes.changeover.__tests__"

# Run by package prefix
curl -k -s -X POST "https://localhost:9043/system/webdev/<PROJECT>/testing/run?package=core.mes"

# Output formats: json (default), junit, text
curl -k -s -X POST "https://localhost:9043/system/webdev/<PROJECT>/testing/run?format=text"
```

**HTTP response codes:** 200 = all passed, 207 = failures/errors, 500 = runner error.

## testing/tags Endpoint

Read/write tags from E2E tests or external tools:

```bash
# Read tags
curl -k -s -X POST "https://localhost:9043/system/webdev/<PROJECT>/testing/tags" \
  -H "Content-Type: application/json" \
  -d '{"reads": ["[WHK01]Path/To/Tag"]}'

# Write tags (auto-creates if missing)
curl -k -s -X POST "https://localhost:9043/system/webdev/<PROJECT>/testing/tags" \
  -H "Content-Type: application/json" \
  -d '{"writes": [{"path": "[default]Test/Tag", "value": 42}]}'

# Call a gateway script function
curl -k -s -X POST "https://localhost:9043/system/webdev/<PROJECT>/testing/tags" \
  -H "Content-Type: application/json" \
  -d '{"script": {"path": "core.util.secrets.get_secret", "args": ["mes-host"]}}'

# Delete tags (cleanup)
curl -k -s -X POST "https://localhost:9043/system/webdev/<PROJECT>/testing/tags" \
  -H "Content-Type: application/json" \
  -d '{"deleteTags": "[default]Test/Tag"}'
```

## Test Discovery Convention

The runner walks `ignition/script-python/` looking for directories named `__tests__` or `__TESTS__` containing `code.py`. The dotted module path is derived from the filesystem path:

```
ignition/script-python/core/mes/changeover/__tests__/code.py
→ module path: core.mes.changeover.__tests__
```

## CRITICAL: resource.json Required for Every Package

**Every directory** in `ignition/script-python/` MUST have a `resource.json` alongside `code.py`. Without it, Ignition does not load the module and imports will fail with `No module named ...`.

When creating a new test module, you must create `resource.json` for BOTH the package directory AND the `__tests__` directory:

```
ignition/script-python/my_package/
├── code.py           # Package code
├── resource.json     # ← REQUIRED
└── __tests__/
    ├── code.py       # Test code
    └── resource.json # ← REQUIRED
```

The `resource.json` content is always the same:
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

**If a test module import fails with `No module named ...`**, the first thing to check is whether `resource.json` exists in every directory in the module path. This is the most common cause of "module not found" errors in Ignition projects managed via git.

## Project Inheritance

In projects that inherit from a parent:
- **Test framework** (`testing.*`) — inherited automatically, lives in parent only
- **Test modules** (`__tests__/code.py`) — can exist in both parent and child; runner discovers all
- **WebDev endpoints** — NOT inherited, each project needs its own `testing/run` and `testing/tags`

### Runner discovery and child project tests

The test runner discovers `__tests__` modules by walking the gateway filesystem. The **scaffolded runner** (from this plugin) dynamically scans all projects in the gateway's data directory, so it finds tests in both parent and child projects automatically.

**However**, if the parent project has an **older runner** (pre-scaffold, hardcoded paths), it will only find tests in its own project. Child project tests won't be discovered.

**When a user adds tests to a child project and they aren't discovered, ASK THE USER:**

> "The test runner in your parent project (*{parent_name}*) only scans its own script library. Your child project's `__tests__` modules won't be discovered. Two options:
>
> 1. **Update the parent runner** — Replace `testing/runner/code.py` in *{parent_name}* with the updated version that dynamically discovers all projects. This fixes it for every child project.
> 2. **Override the runner in this project** — Create `testing/runner/code.py` here with dynamic discovery. This project gets its own runner without touching the parent.
>
> Which do you prefer?"

If they choose option 2, scaffold the runner locally (don't use `--skip-scripts`, or copy just the runner module). If they choose option 1, update the parent's runner code.

## Common Patterns

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
    write_dataset_tag("[default]Test/Queue", ["Id", "Value"], ["String", "Int4"], [["A", 1], ["B", 2]])

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
