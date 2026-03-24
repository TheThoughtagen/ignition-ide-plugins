#!/usr/bin/env bash
# scaffold-testing.sh — Scaffold Jython test framework + WebDev endpoints + type stubs.
# Part of the Ignition Dev Tools Claude Code plugin.
#
# Creates ~25 files across 3 directories:
#   1. Jython test framework  (ignition/script-python/testing/)
#   2. WebDev test endpoints   (com.inductiveautomation.webdev/resources/testing/)
#   3. Type stubs              (.ignition-stubs/testing/)
#
# Usage:
#   scaffold-testing.sh --project-root /path/to/project --project-name MyProject \
#     [--gateway-url https://localhost:9043] [--tag-provider default] \
#     [--force] [--dry-run]

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

PROJECT_ROOT="" PROJECT_NAME="" GATEWAY_URL="" TAG_PROVIDER=""
FORCE=false DRY_RUN=false SKIP_SCRIPTS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root)  PROJECT_ROOT="$2";  shift 2 ;;
    --project-name)  PROJECT_NAME="$2";  shift 2 ;;
    --gateway-url)   GATEWAY_URL="$2";   shift 2 ;;
    --tag-provider)  TAG_PROVIDER="$2";  shift 2 ;;
    --force)         FORCE=true;         shift ;;
    --dry-run)       DRY_RUN=true;       shift ;;
    --skip-scripts)  SKIP_SCRIPTS=true;  shift ;;
    -h|--help)
      sed -n '2,14s/^# //p' "$0"
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

# Verify project root exists
[[ -d "$PROJECT_ROOT" ]] || { echo "Error: project root does not exist: $PROJECT_ROOT" >&2; exit 1; }

CREATED=0 SKIPPED=0

# ---------------------------------------------------------------------------
# Helper: write a file with existence check
# ---------------------------------------------------------------------------

write_file() {
  local filepath="$1"
  local content="$2"
  local full_path="$PROJECT_ROOT/$filepath"

  if [[ "$DRY_RUN" = true ]]; then
    echo "  Would create: $filepath"
    return
  fi

  if [[ -f "$full_path" ]] && [[ "$FORCE" != true ]]; then
    echo "  Skipped (exists): $filepath"
    SKIPPED=$((SKIPPED + 1))
    return
  fi

  mkdir -p "$(dirname "$full_path")"
  printf '%s' "$content" > "$full_path"
  CREATED=$((CREATED + 1))
  echo "  Created: $filepath"
}

# ---------------------------------------------------------------------------
# Shared resource.json (identical for all 5 script modules)
# ---------------------------------------------------------------------------

RESOURCE_JSON=$(cat <<'RJEOF'
{
  "scope": "A",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": [
    "code.py"
  ],
  "attributes": {
    "lastModification": {
      "actor": "external",
      "timestamp": "2026-02-20T00:00:00Z"
    },
    "hintScope": 2
  }
}
RJEOF
)

# ---------------------------------------------------------------------------
# Shared WebDev config.json
# ---------------------------------------------------------------------------

WEBDEV_CONFIG_JSON=$(cat <<'WCEOF'
{
  "resource-type": "python-resource",
  "doGet": {
    "enabled": true,
    "max-retry-attempts": 3,
    "require-auth": false,
    "require-https": false,
    "required-roles": "",
    "user-source": ""
  },
  "doPost": {
    "enabled": true,
    "max-retry-attempts": 3,
    "require-auth": false,
    "require-https": false,
    "required-roles": "",
    "user-source": ""
  },
  "doPut": {
    "enabled": false,
    "max-retry-attempts": 3,
    "require-auth": false,
    "require-https": false,
    "required-roles": "",
    "user-source": ""
  },
  "doDelete": {
    "enabled": false,
    "max-retry-attempts": 3,
    "require-auth": false,
    "require-https": false,
    "required-roles": "",
    "user-source": ""
  },
  "doHead": {
    "enabled": false,
    "max-retry-attempts": 3,
    "require-auth": false,
    "require-https": false,
    "required-roles": "",
    "user-source": ""
  },
  "doOptions": {
    "enabled": false,
    "max-retry-attempts": 3,
    "require-auth": false,
    "require-https": false,
    "required-roles": "",
    "user-source": ""
  },
  "doTrace": {
    "enabled": false,
    "max-retry-attempts": 3,
    "require-auth": false,
    "require-https": false,
    "required-roles": "",
    "user-source": ""
  },
  "doPatch": {
    "enabled": false,
    "max-retry-attempts": 3,
    "require-auth": false,
    "require-https": false,
    "required-roles": "",
    "user-source": ""
  }
}
WCEOF
)

echo "Scaffolding test framework for project: $PROJECT_NAME"
echo "  Project root:  $PROJECT_ROOT"
echo "  Gateway URL:   $GATEWAY_URL"
echo "  Tag provider:  $TAG_PROVIDER"
echo ""

# ===================================================================
# 1. Jython Test Framework — ignition/script-python/testing/
# ===================================================================

if [[ "$SKIP_SCRIPTS" = true ]]; then
  echo "--- Jython Test Framework (skipped — inherited from parent project) ---"
else
echo "--- Jython Test Framework ---"

# --- runner/code.py (genericized) ---

RUNNER_CODE=$(cat <<'PYEOF'
"""
Test runner: discovers and executes @test-decorated functions.

Location: testing.runner

Usage from Script Console:
	print testing.runner.run_all()
	print testing.runner.run_module("core.mes.changeover.__tests__")

Usage from WebDev:
	results = testing.runner.run_all()
	return {'json': results}
"""

import time
import traceback

from java.io import File


# ---------------------------------------------------------------------------
# Configuration — set PROJECT_NAME to your Ignition project folder name.
# The scaffold script replaces PLACEHOLDER_PROJECT_NAME automatically.
# ---------------------------------------------------------------------------

PROJECT_NAME = "PLACEHOLDER_PROJECT_NAME"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_all(base_package=""):
	"""Discover and run all test modules under the script library.

	Args:
		base_package: Dotted package prefix to filter (e.g. "core.mes").
		              Empty string means run everything.

	Returns:
		dict: {passed, failed, skipped, errors, duration_ms, results: [...]}
	"""
	modules = _discover_test_modules()

	if base_package:
		modules = [m for m in modules if m.startswith(base_package)]

	all_results = []
	t0 = time.time()

	for module_path in sorted(modules):
		module_results = run_module(module_path)
		all_results.append(module_results)

	elapsed = int((time.time() - t0) * 1000)

	passed = sum(m["passed"] for m in all_results)
	failed = sum(m["failed"] for m in all_results)
	skipped = sum(m["skipped"] for m in all_results)
	errors = sum(m["errors"] for m in all_results)

	return {
		"passed": passed,
		"failed": failed,
		"skipped": skipped,
		"errors": errors,
		"total": passed + failed + skipped + errors,
		"duration_ms": elapsed,
		"modules": all_results,
	}


def run_module(module_path):
	"""Import a specific test module and run all @test functions in it.

	Args:
		module_path: Dotted module path (e.g. "core.mes.changeover.__tests__")

	Returns:
		dict: {module, passed, failed, skipped, errors, duration_ms, results: [...]}
	"""
	result = {
		"module": module_path,
		"passed": 0,
		"failed": 0,
		"skipped": 0,
		"errors": 0,
		"duration_ms": 0,
		"results": [],
	}

	t0 = time.time()

	# Import the module
	try:
		mod = _import_module(module_path)
	except Exception as e:
		result["errors"] = 1
		result["results"].append({
			"name": "(module import)",
			"status": "error",
			"message": "Failed to import %s: %s" % (module_path, str(e)),
			"traceback": traceback.format_exc(),
			"duration_ms": 0,
		})
		result["duration_ms"] = int((time.time() - t0) * 1000)
		return result

	# Find setup/teardown and test functions
	setup_fn = None
	teardown_fn = None
	test_fns = []

	for name in dir(mod):
		obj = getattr(mod, name)
		if not callable(obj):
			continue
		if getattr(obj, "_is_setup", False):
			setup_fn = obj
		elif getattr(obj, "_is_teardown", False):
			teardown_fn = obj
		elif getattr(obj, "_is_test", False):
			test_fns.append((name, obj))

	# Sort tests by name for deterministic ordering
	test_fns.sort(key=lambda pair: pair[0])

	# Run setup
	if setup_fn is not None:
		try:
			setup_fn()
		except Exception as e:
			result["errors"] = 1
			result["results"].append({
				"name": "(setup)",
				"status": "error",
				"message": "Setup failed: %s" % str(e),
				"traceback": traceback.format_exc(),
				"duration_ms": 0,
			})
			result["duration_ms"] = int((time.time() - t0) * 1000)
			return result

	# Run tests
	for name, func in test_fns:
		test_result = _run_single_test(name, func)
		result["results"].append(test_result)
		status = test_result["status"]
		if status == "passed":
			result["passed"] += 1
		elif status == "failed":
			result["failed"] += 1
		elif status == "skipped":
			result["skipped"] += 1
		elif status == "error":
			result["errors"] += 1

	# Run teardown
	if teardown_fn is not None:
		try:
			teardown_fn()
		except Exception as e:
			result["results"].append({
				"name": "(teardown)",
				"status": "error",
				"message": "Teardown failed: %s" % str(e),
				"traceback": traceback.format_exc(),
				"duration_ms": 0,
			})
			result["errors"] += 1

	result["duration_ms"] = int((time.time() - t0) * 1000)
	return result


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _discover_test_modules():
	"""Walk the script library filesystem to find __tests__/code.py modules.

	Looks for both __tests__ (lowercase, new convention) and __TESTS__
	(uppercase, legacy convention) directories containing code.py.

	Dynamically discovers all project script-python directories by scanning
	the gateway's projects folder. This means tests are found in both the
	current project and any parent/sibling projects — matching how Ignition's
	project inheritance makes scripts available at runtime.

	Returns:
		list[str]: Dotted module paths (e.g. ["core.mes.changeover.__tests__"])
	"""
	# Discover project directories dynamically.
	# The gateway stores projects at /usr/local/bin/ignition/data/projects/.
	# We scan all projects that have a script-python directory, so tests in
	# parent projects (inherited via project inheritance) are also found.
	project_dirs = []

	gateway_projects_root = File("/usr/local/bin/ignition/data/projects")
	if gateway_projects_root.exists():
		for project_dir in (gateway_projects_root.listFiles() or []):
			if not project_dir.isDirectory():
				continue
			script_path = File(project_dir, "ignition/script-python")
			if script_path.exists():
				project_dirs.append(script_path.getAbsolutePath())

	# Fallback: if no gateway path found, try the configured project name
	if not project_dirs:
		fallback = "/usr/local/bin/ignition/data/projects/" + PROJECT_NAME + "/ignition/script-python"
		project_dirs.append(fallback)

	modules = []
	seen = set()

	for base_dir in project_dirs:
		base_file = File(base_dir)
		if not base_file.exists():
			continue

		_walk_for_tests(base_file, base_dir, modules, seen)

	return sorted(modules)


def _walk_for_tests(directory, base_dir, modules, seen):
	"""Recursively walk directory to find __tests__/code.py files.

	Args:
		directory: java.io.File directory to search
		base_dir: Root script-python path for computing module names
		modules: List to append discovered module paths to
		seen: Set of already-seen module paths (avoids duplicates)
	"""
	children = directory.listFiles()
	if children is None:
		return

	for child in children:
		if not child.isDirectory():
			continue

		name = child.getName()

		# Check if this is a test directory
		if name in ("__tests__", "__TESTS__"):
			code_file = File(child, "code.py")
			if code_file.exists():
				# Convert filesystem path to dotted module path
				rel_path = child.getAbsolutePath()[len(base_dir) + 1:]
				module_path = rel_path.replace("/", ".").replace("\\", ".")
				if module_path not in seen:
					seen.add(module_path)
					modules.append(module_path)
		else:
			# Recurse into subdirectories
			_walk_for_tests(child, base_dir, modules, seen)


# ---------------------------------------------------------------------------
# Import & Execution
# ---------------------------------------------------------------------------

def _import_module(module_path):
	"""Import a dotted module path and return the module object.

	Uses Jython's __import__ to load script library modules by their
	dotted path (e.g. "core.mes.changeover.__tests__").

	Args:
		module_path: Dotted module path

	Returns:
		module object
	"""
	parts = module_path.split(".")
	mod = __import__(module_path)
	# __import__ returns the top-level module; traverse to the leaf
	for part in parts[1:]:
		mod = getattr(mod, part)
	return mod


def _run_single_test(name, func):
	"""Execute a single test function and return its result.

	Handles @skip, @expected_error decorators, and captures exceptions.

	Args:
		name: Test function name
		func: The test function

	Returns:
		dict: {name, status, message, traceback, duration_ms}
	"""
	# Check for skip
	if getattr(func, "_skip", False):
		reason = getattr(func, "_skip_reason", "")
		return {
			"name": name,
			"status": "skipped",
			"message": reason,
			"traceback": None,
			"duration_ms": 0,
		}

	expected_error = getattr(func, "_expected_error", None)

	t0 = time.time()
	try:
		func()
		elapsed = int((time.time() - t0) * 1000)

		if expected_error is not None:
			# Expected an exception but none was raised
			return {
				"name": name,
				"status": "failed",
				"message": "Expected %s to be raised" % expected_error.__name__,
				"traceback": None,
				"duration_ms": elapsed,
			}

		return {
			"name": name,
			"status": "passed",
			"message": None,
			"traceback": None,
			"duration_ms": elapsed,
		}

	except Exception as e:
		elapsed = int((time.time() - t0) * 1000)

		if expected_error is not None and isinstance(e, expected_error):
			return {
				"name": name,
				"status": "passed",
				"message": "Raised expected %s" % expected_error.__name__,
				"traceback": None,
				"duration_ms": elapsed,
			}

		# Determine if this is an assertion failure or an unexpected error
		from testing.assertions import TestAssertionError
		if isinstance(e, (TestAssertionError, AssertionError)):
			status = "failed"
		else:
			status = "error"

		return {
			"name": name,
			"status": status,
			"message": str(e),
			"traceback": traceback.format_exc(),
			"duration_ms": elapsed,
		}
PYEOF
)
# Replace placeholder with actual project name
RUNNER_CODE="${RUNNER_CODE//PLACEHOLDER_PROJECT_NAME/$PROJECT_NAME}"
write_file "ignition/script-python/testing/runner/code.py" "$RUNNER_CODE"
write_file "ignition/script-python/testing/runner/resource.json" "$RESOURCE_JSON"

# --- assertions/code.py (generic, used as-is) ---

ASSERTIONS_CODE=$(cat <<'PYEOF'
"""
Test assertion functions with descriptive failure messages.

Location: testing.assertions

Usage:
	from testing.assertions import assert_equal, assert_true, assert_raises

	assert_equal(actual, expected)
	assert_true(value, "should be truthy")
	assert_raises(lambda: int("abc"), ValueError)
"""


class TestAssertionError(AssertionError):
	"""Assertion error with structured context for test reporting."""

	def __init__(self, message, actual=None, expected=None):
		self.actual = actual
		self.expected = expected
		super(TestAssertionError, self).__init__(message)


def assert_equal(actual, expected, msg=None):
	"""Assert actual == expected."""
	if actual != expected:
		text = msg or "Expected %r but got %r" % (expected, actual)
		raise TestAssertionError(text, actual=actual, expected=expected)


def assert_not_equal(actual, expected, msg=None):
	"""Assert actual != expected."""
	if actual == expected:
		text = msg or "Expected values to differ but both are %r" % (actual,)
		raise TestAssertionError(text, actual=actual, expected=expected)


def assert_true(val, msg=None):
	"""Assert val is truthy."""
	if not val:
		text = msg or "Expected truthy value but got %r" % (val,)
		raise TestAssertionError(text, actual=val, expected=True)


def assert_false(val, msg=None):
	"""Assert val is falsy."""
	if val:
		text = msg or "Expected falsy value but got %r" % (val,)
		raise TestAssertionError(text, actual=val, expected=False)


def assert_none(val, msg=None):
	"""Assert val is None."""
	if val is not None:
		text = msg or "Expected None but got %r" % (val,)
		raise TestAssertionError(text, actual=val, expected=None)


def assert_not_none(val, msg=None):
	"""Assert val is not None."""
	if val is None:
		text = msg or "Expected a value but got None"
		raise TestAssertionError(text, actual=None, expected="not None")


def assert_close(actual, expected, tolerance=0.001, msg=None):
	"""Assert actual is within tolerance of expected (for floating point).

	Args:
		actual: Actual numeric value
		expected: Expected numeric value
		tolerance: Maximum allowed absolute difference (default 0.001)
		msg: Optional failure message
	"""
	diff = abs(actual - expected)
	if diff > tolerance:
		text = msg or "Expected %r within %s of %r (diff=%s)" % (
			actual, tolerance, expected, diff
		)
		raise TestAssertionError(text, actual=actual, expected=expected)


def assert_raises(callable_fn, exception_type, msg=None):
	"""Assert that calling callable_fn raises the given exception type.

	Args:
		callable_fn: Zero-argument callable to invoke
		exception_type: Expected exception class
		msg: Optional failure message

	Returns:
		The caught exception instance (for further inspection)
	"""
	try:
		callable_fn()
	except exception_type as e:
		return e
	except Exception as e:
		text = msg or "Expected %s but got %s: %s" % (
			exception_type.__name__, type(e).__name__, str(e)
		)
		raise TestAssertionError(text, actual=type(e).__name__, expected=exception_type.__name__)
	else:
		text = msg or "Expected %s to be raised but nothing was raised" % (
			exception_type.__name__,
		)
		raise TestAssertionError(text, actual="no exception", expected=exception_type.__name__)


def assert_tag_value(tag_path, expected, msg=None):
	"""Read a real gateway tag and assert its value equals expected.

	Args:
		tag_path: Full tag path (e.g. '[default]Path/To/Tag')
		expected: Expected value
		msg: Optional failure message
	"""
	qv = system.tag.readBlocking([tag_path])[0]
	actual = qv.value
	if actual != expected:
		text = msg or "Tag '%s' expected %r but got %r (quality=%s)" % (
			tag_path, expected, actual, qv.quality
		)
		raise TestAssertionError(text, actual=actual, expected=expected)


def assert_contains(container, item, msg=None):
	"""Assert that item is in container."""
	if item not in container:
		text = msg or "Expected %r to contain %r" % (container, item)
		raise TestAssertionError(text, actual=container, expected=item)


def assert_isinstance(obj, expected_type, msg=None):
	"""Assert that obj is an instance of expected_type."""
	if not isinstance(obj, expected_type):
		text = msg or "Expected instance of %s but got %s" % (
			expected_type.__name__, type(obj).__name__
		)
		raise TestAssertionError(text, actual=type(obj).__name__, expected=expected_type.__name__)
PYEOF
)
write_file "ignition/script-python/testing/assertions/code.py" "$ASSERTIONS_CODE"
write_file "ignition/script-python/testing/assertions/resource.json" "$RESOURCE_JSON"

# --- decorators/code.py (generic, used as-is) ---

DECORATORS_CODE=$(cat <<'PYEOF'
"""
Test decorators for marking functions as tests.

Location: testing.decorators

Usage:
	from testing.decorators import test, skip, setup, teardown, expected_error

	@test
	def my_test():
		assert_equal(1 + 1, 2)

	@skip("not implemented yet")
	@test
	def future_test():
		pass

	@expected_error(ValueError)
	@test
	def test_bad_input():
		int("abc")
"""


def test(func):
	"""Mark a function as a test case.

	Sets _is_test = True on the function so the runner can discover it.
	"""
	func._is_test = True
	return func


def skip(reason=""):
	"""Mark a test to be skipped during execution.

	Args:
		reason: Optional explanation for why the test is skipped

	Usage:
		@skip("waiting on tag config")
		@test
		def test_something():
			pass
	"""
	def decorator(func):
		func._skip = True
		func._skip_reason = reason
		return func
	return decorator


def setup(func):
	"""Mark a function as module-level setup (runs before all tests)."""
	func._is_setup = True
	return func


def teardown(func):
	"""Mark a function as module-level teardown (runs after all tests)."""
	func._is_teardown = True
	return func


def expected_error(exception_type):
	"""Mark a test that should raise a specific exception type.

	The test passes if the expected exception is raised, fails otherwise.

	Args:
		exception_type: The exception class expected (e.g. ValueError, KeyError)

	Usage:
		@expected_error(ValueError)
		@test
		def test_bad_parse():
			int("not a number")
	"""
	def decorator(func):
		func._expected_error = exception_type
		return func
	return decorator
PYEOF
)
write_file "ignition/script-python/testing/decorators/code.py" "$DECORATORS_CODE"
write_file "ignition/script-python/testing/decorators/resource.json" "$RESOURCE_JSON"

# --- helpers/code.py (stripped: keep only write_dataset_tag + clear_dataset_tag) ---

HELPERS_CODE=$(cat <<'PYEOF'
"""
Helper functions callable from E2E tests via the callScript endpoint.

These bridge the gap between the testing/tags WebDev endpoint (which writes
raw JSON values) and Ignition tag types that need native objects (DataSets,
etc.).
"""
import system


def write_dataset_tag(tag_path, columns, types, rows):
	"""Write a real Ignition DataSet to a tag.

	The testing/tags endpoint writes raw JSON which doesn't produce a native
	DataSet object.  This helper uses system.dataset.toDataSet() to create
	a proper DataSet, then writes it via system.tag.writeBlocking().

	Args:
		tag_path (str): Full tag path, e.g. "[default]Path/To/Tag".
		columns (list[str]): Column header names.
		types (list[str]): Column type names matching Ignition types
			(String, Float8, Int4, Boolean, DateTime, etc.).
		rows (list[list]): Row data — each inner list matches column order.

	Returns:
		dict: {"success": True/False, "rowCount": int, "error": str or None}
	"""
	try:
		# Coerce row values to match declared types
		type_coerce = {
			"String": str,
			"Float8": float,
			"Float4": float,
			"Int4": int,
			"Int8": int,
			"Boolean": bool,
		}
		coerced_rows = []
		for row in rows:
			new_row = []
			for j, val in enumerate(row):
				t = types[j] if j < len(types) else "String"
				fn = type_coerce.get(t)
				new_row.append(fn(val) if fn and val is not None else val)
			coerced_rows.append(new_row)

		ds = system.dataset.toDataSet(columns, coerced_rows)

		# Try writing the DataSet directly first.
		results = system.tag.writeBlocking([tag_path], [ds])
		success = results[0].isGood()

		if success:
			# Verify the read-back is actually a DataSet (not a toString'd string)
			readback = system.tag.readBlocking([tag_path])[0].value
			if readback is not None and hasattr(readback, 'getRowCount'):
				return {
					"success": True,
					"rowCount": ds.getRowCount(),
					"error": None,
				}

			# Tag is String type — Ignition stored the DataSet's toString().
			# Re-configure the tag as DataSet type and retry.
			base_path = tag_path[:tag_path.rfind('/')]
			tag_name = tag_path[tag_path.rfind('/') + 1:]
			system.tag.configure(base_path, [{
				"name": tag_name,
				"dataType": "DataSet",
				"valueSource": "memory",
			}], "o")

			# Retry write with DataSet type
			results = system.tag.writeBlocking([tag_path], [ds])
			success = results[0].isGood()

		return {
			"success": success,
			"rowCount": ds.getRowCount(),
			"error": None if success else str(results[0]),
		}
	except:
		import traceback
		return {
			"success": False,
			"rowCount": 0,
			"error": traceback.format_exc(),
		}


def clear_dataset_tag(tag_path, columns, types):
	"""Write an empty DataSet to a tag.

	Args:
		tag_path (str): Full tag path.
		columns (list[str]): Column header names.
		types (list[str]): Column type names.

	Returns:
		dict: {"success": True/False, "error": str or None}
	"""
	return write_dataset_tag(tag_path, columns, types, [])
PYEOF
)
write_file "ignition/script-python/testing/helpers/code.py" "$HELPERS_CODE"
write_file "ignition/script-python/testing/helpers/resource.json" "$RESOURCE_JSON"

# --- reporter/code.py (generic, used as-is) ---

REPORTER_CODE=$(cat <<'PYEOF'
"""
Test result formatters: JSON, JUnit XML, and console output.

Location: testing.reporter

Usage:
	results = testing.runner.run_all()
	print testing.reporter.to_console(results)
	xml = testing.reporter.to_junit_xml(results)
	json_str = testing.reporter.to_json(results)
"""

import json
import time


def to_json(results):
	"""Serialize test results to a JSON string.

	Args:
		results: Dict from testing.runner.run_all() or run_module()

	Returns:
		str: JSON string
	"""
	return json.dumps(results, indent=2)


def to_console(results):
	"""Format test results as human-readable text for the Script Console.

	Args:
		results: Dict from testing.runner.run_all()

	Returns:
		str: Formatted text output
	"""
	lines = []
	lines.append("=" * 60)
	lines.append("TEST RESULTS")
	lines.append("=" * 60)

	modules = results.get("modules", [])
	if not modules:
		# Single module result (from run_module)
		modules = [results]

	for mod in modules:
		module_name = mod.get("module", "unknown")
		lines.append("")
		lines.append("--- %s ---" % module_name)

		for r in mod.get("results", []):
			status = r["status"].upper()
			name = r["name"]

			if status == "PASSED":
				marker = "  PASS"
			elif status == "FAILED":
				marker = "  FAIL"
			elif status == "SKIPPED":
				marker = "  SKIP"
			else:
				marker = " ERROR"

			line = "%s  %s" % (marker, name)
			if r.get("duration_ms", 0) > 0:
				line += "  (%dms)" % r["duration_ms"]
			lines.append(line)

			if r.get("message") and status in ("FAILED", "ERROR"):
				lines.append("         %s" % r["message"])

	lines.append("")
	lines.append("=" * 60)
	lines.append(
		"Total: %d  Passed: %d  Failed: %d  Skipped: %d  Errors: %d  (%dms)" % (
			results.get("total", 0),
			results.get("passed", 0),
			results.get("failed", 0),
			results.get("skipped", 0),
			results.get("errors", 0),
			results.get("duration_ms", 0),
		)
	)
	lines.append("=" * 60)

	return "\n".join(lines)


def to_junit_xml(results):
	"""Format test results as JUnit XML for CI integration.

	Args:
		results: Dict from testing.runner.run_all()

	Returns:
		str: JUnit XML string
	"""
	modules = results.get("modules", [])
	if not modules:
		modules = [results]

	xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
	xml_parts.append('<testsuites tests="%d" failures="%d" errors="%d" skipped="%d" time="%.3f">' % (
		results.get("total", 0),
		results.get("failed", 0),
		results.get("errors", 0),
		results.get("skipped", 0),
		results.get("duration_ms", 0) / 1000.0,
	))

	for mod in modules:
		module_name = mod.get("module", "unknown")
		test_results = mod.get("results", [])

		mod_failures = mod.get("failed", 0)
		mod_errors = mod.get("errors", 0)
		mod_skipped = mod.get("skipped", 0)
		mod_tests = len(test_results)
		mod_time = mod.get("duration_ms", 0) / 1000.0

		xml_parts.append(
			'  <testsuite name="%s" tests="%d" failures="%d" errors="%d" skipped="%d" time="%.3f">'
			% (_escape_xml(module_name), mod_tests, mod_failures, mod_errors, mod_skipped, mod_time)
		)

		for r in test_results:
			name = r.get("name", "unknown")
			t = r.get("duration_ms", 0) / 1000.0
			status = r.get("status", "error")

			xml_parts.append(
				'    <testcase name="%s" classname="%s" time="%.3f">'
				% (_escape_xml(name), _escape_xml(module_name), t)
			)

			if status == "failed":
				msg = _escape_xml(r.get("message", ""))
				tb = _escape_xml(r.get("traceback", "") or "")
				xml_parts.append('      <failure message="%s">%s</failure>' % (msg, tb))
			elif status == "error":
				msg = _escape_xml(r.get("message", ""))
				tb = _escape_xml(r.get("traceback", "") or "")
				xml_parts.append('      <error message="%s">%s</error>' % (msg, tb))
			elif status == "skipped":
				reason = _escape_xml(r.get("message", ""))
				xml_parts.append('      <skipped message="%s" />' % reason)

			xml_parts.append('    </testcase>')

		xml_parts.append('  </testsuite>')

	xml_parts.append('</testsuites>')

	return "\n".join(xml_parts)


def _escape_xml(text):
	"""Escape special XML characters."""
	if text is None:
		return ""
	text = str(text)
	text = text.replace("&", "&amp;")
	text = text.replace("<", "&lt;")
	text = text.replace(">", "&gt;")
	text = text.replace('"', "&quot;")
	return text
PYEOF
)
write_file "ignition/script-python/testing/reporter/code.py" "$REPORTER_CODE"
write_file "ignition/script-python/testing/reporter/resource.json" "$RESOURCE_JSON"


# ===================================================================
fi  # end SKIP_SCRIPTS guard

# 2. WebDev Test Endpoints — com.inductiveautomation.webdev/resources/testing/
# ===================================================================

echo ""
echo "--- WebDev Test Endpoints ---"

# --- run/doGet.py (genericized project name) ---

RUN_DOGET=$(cat <<'PYEOF'
def doGet(request, session):
	"""Return usage information for the test runner endpoint.

	GET /data/testing/run - shows this help
	GET /data/testing/run?discover=true - lists discovered test modules
	"""
	params = request.get("params", {})
	discover = "discover" in params

	if discover:
		try:
			modules = testing.runner._discover_test_modules()
			return {"json": {
				"discovered_modules": modules,
				"count": len(modules),
			}}
		except Exception as e:
			import traceback
			return {"json": {
				"error": str(e),
				"traceback": traceback.format_exc(),
			}}

	return {"json": {
		"name": "PLACEHOLDER_PROJECT_NAME — Test Runner",
		"usage": {
			"run_all": "POST /data/testing/run",
			"run_module": "POST /data/testing/run?module=core.mes.changeover.__tests__",
			"run_package": "POST /data/testing/run?package=core.mes",
			"formats": "Add ?format=json|junit|text",
			"discover": "GET /data/testing/run?discover=true",
		},
	}}
PYEOF
)
RUN_DOGET="${RUN_DOGET//PLACEHOLDER_PROJECT_NAME/$PROJECT_NAME}"
write_file "com.inductiveautomation.webdev/resources/testing/run/doGet.py" "$RUN_DOGET"

# --- run/doPost.py (generic, used as-is) ---

RUN_DOPOST=$(cat <<'PYEOF'
def doPost(request, session):
	"""Run tests and return JSON results.

	Query params:
		module  - Dotted module path to run specific tests
		         (e.g. "core.mes.changeover.__tests__")
		package - Dotted package prefix to filter
		         (e.g. "core.mes")
		format  - Output format: "json" (default), "junit", "text"

	POST body (JSON, optional):
		{"module": "...", "package": "...", "format": "..."}

	Returns:
		200 if all tests pass
		207 if there are failures or errors
		500 on runner error
	"""
	import json

	# Parse params from query string or POST body
	module = None
	package = ""
	fmt = "json"

	params = request.get("params", {})
	if params:
		module = _get_param(params, "module")
		package = _get_param(params, "package") or ""
		fmt = _get_param(params, "format") or "json"

	# Also check POST body
	body = request.get("data", None)
	if body:
		try:
			if hasattr(body, 'read'):
				body = body.read()
			body_data = json.loads(body)
			if isinstance(body_data, dict):
				module = body_data.get("module", module)
				package = body_data.get("package", package)
				fmt = body_data.get("format", fmt)
		except Exception:
			pass

	try:
		if module:
			results = testing.runner.run_module(module)
			# Wrap single module in the run_all structure
			results = {
				"passed": results["passed"],
				"failed": results["failed"],
				"skipped": results["skipped"],
				"errors": results["errors"],
				"total": results["passed"] + results["failed"] + results["skipped"] + results["errors"],
				"duration_ms": results["duration_ms"],
				"modules": [results],
			}
		else:
			results = testing.runner.run_all(base_package=package)

		if fmt == "junit":
			xml = testing.reporter.to_junit_xml(results)
			return {
				"html": xml,
				"content-type": "application/xml",
			}
		elif fmt == "text":
			text = testing.reporter.to_console(results)
			return {
				"html": "<pre>%s</pre>" % text,
				"content-type": "text/plain",
			}

		# Default JSON
		status = 200 if results["failed"] == 0 and results["errors"] == 0 else 207
		return {"json": results}

	except Exception as e:
		import traceback
		return {"json": {
			"error": str(e),
			"traceback": traceback.format_exc(),
		}}


def _get_param(params, key):
	"""Extract a single query param value from Ignition WebDev params.

	Ignition WebDev params are Java String[] arrays. Indexing [0] on a
	plain string returns the first character, so we must check the type.
	"""
	val = params.get(key)
	if val is None:
		return None
	# Convert to string first — handles Java String and Python str
	s = str(val)
	# Java String[] arrays stringify as '[value]', plain strings don't
	# The safest check: if it looks like an array, use .toString() on element
	try:
		# Try treating as a Java array — getClass().isArray() works in Jython
		if hasattr(val, 'getClass') and val.getClass().isArray():
			from java.lang.reflect import Array
			if Array.getLength(val) > 0:
				return str(Array.get(val, 0))
			return None
	except Exception:
		pass
	# If it's a Python list/tuple, take first element
	if isinstance(val, (list, tuple)):
		return str(val[0]) if val else None
	# Already a string
	return s
PYEOF
)
write_file "com.inductiveautomation.webdev/resources/testing/run/doPost.py" "$RUN_DOPOST"

# --- run/config.json ---

write_file "com.inductiveautomation.webdev/resources/testing/run/config.json" "$WEBDEV_CONFIG_JSON"

# --- run/resource.json (Ignition resource descriptor — required for WebDev to discover the endpoint) ---

WEBDEV_RUN_RESOURCE=$(cat <<'JSONEOF'
{
  "scope": "G",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": [
    "config.json",
    "doPost.py",
    "doGet.py"
  ],
  "attributes": {
    "lastModification": {
      "actor": "external",
      "timestamp": "2026-01-01T00:00:00Z"
    }
  }
}
JSONEOF
)
write_file "com.inductiveautomation.webdev/resources/testing/run/resource.json" "$WEBDEV_RUN_RESOURCE"

# --- tags/doGet.py (genericized tag provider + CSV filename) ---

TAGS_DOGET=$(cat <<'PYEOF'
def doGet(request, session):
	params = request.get('params', {})

	# Simulator CSV download
	simulatorCsv = params.get('simulatorCsv', None)
	if simulatorCsv is not None:
		csv_qv = system.tag.readBlocking(['[PLACEHOLDER_TAG_PROVIDER]WH/Systems/Simulation/DeviceCSV'])[0]
		if csv_qv.quality.isGood() and csv_qv.value:
			# Write CSV directly to servlet response for proper Content-Type
			response = request['servletResponse']
			response.setContentType('text/csv')
			response.setHeader('Content-Disposition', 'attachment; filename="PLACEHOLDER_PROJECT_NAME_Sim_program.csv"')
			writer = response.getWriter()
			writer.print(csv_qv.value)
			writer.flush()
			return
		return {'json': {'error': 'No CSV generated. Run controller.enable(mode="device") first.'}}

	# Browse mode: list tag providers or browse a path
	browse = params.get('browse', None)
	if browse is not None:
		# Handle Java String[] from query params
		from java.lang.reflect import Array
		if hasattr(browse, '__len__') and not isinstance(browse, (str, unicode)):
			browse = Array.get(browse, 0)

		if browse == '' or browse == 'providers':
			# List top-level tag providers
			results = system.tag.browse('')
			providers = []
			for r in results.getResults():
				providers.append(str(r))
			return {'json': {'providers': providers}}
		else:
			# Browse a specific path
			results = system.tag.browse(browse)
			tags = []
			for r in results.getResults():
				tags.append(str(r))
			return {'json': {'path': browse, 'tags': tags}}

	return {'json': {
		'endpoint': 'testing/tags',
		'description': 'Read/write tags for E2E testing',
		'usage': {
			'GET': {
				'browse': '?browse=providers or ?browse=[default]Path',
				'simulatorCsv': '?simulatorCsv=true - download device simulator CSV program'
			},
			'POST': {
				'writes': [{'path': '[default]Tag/Path', 'value': 'someValue'}],
				'reads': ['[default]Tag/Path']
			}
		}
	}}
PYEOF
)
TAGS_DOGET="${TAGS_DOGET//PLACEHOLDER_TAG_PROVIDER/$TAG_PROVIDER}"
TAGS_DOGET="${TAGS_DOGET//PLACEHOLDER_PROJECT_NAME/$PROJECT_NAME}"
write_file "com.inductiveautomation.webdev/resources/testing/tags/doGet.py" "$TAGS_DOGET"

# --- tags/doPost.py (genericized paths + mirror comment) ---

TAGS_DOPOST=$(cat <<'PYEOF'
def doPost(request, session):
	"""Read/write tags for E2E testing. Auto-creates missing tags.

	POST body: { "writes": [{"path": "[default]Tag/Path", "value": "someValue"}, ...] }
	Response:  { "results": [{"path": "...", "success": true}, ...] }

	Also supports reading: { "reads": ["[default]Tag/Path", ...] }
	Response:  { "values": {"[default]Tag/Path": {"value": ..., "quality": ...}} }

	Mirror OPC tags to memory (for testing without PLC):
	  { "mirror": {"source": "[provider]Path/To/Folder", "dest": "[provider]Path/To/Folder_MEM"} }
	  Response: { "mirror": {"success": true, "dest": "..."} }

	Delete mirrored tags:
	  { "deleteTags": "[provider]Path/To/Folder_MEM" }
	  Response: { "deleteTags": {"success": true} }

	Call a gateway script function (for testing real scripts end-to-end):
	  { "script": {"path": "core.mes.mashing.enzyme_entry.validate_and_submit", "args": [1, 1, 5.0, "gal", "LOT-001"]} }
	  Response: { "script": {"success": true, "result": {...}} }
	"""
	import json

	data = request['data']
	if isinstance(data, (str, unicode)):
		data = system.util.jsonDecode(data)

	response = {}

	# Handle mirror — clone OPC subtree as memory tags.
	# NOTE: This requires a `convert_to_memory_tags(source, dest)` function in
	# your project's script library.  The function should browse the source OPC
	# tag tree and recreate it under dest with valueSource="memory".
	# If you don't need mirror functionality, you can safely remove this block.
	if 'mirror' in data:
		mirrorCfg = data['mirror']
		source = mirrorCfg['source']
		dest = mirrorCfg.get('dest', source + '_MEM')
		try:
			# TODO: Replace with your project's convert_to_memory_tags function.
			# Example: your_project.tools.conversions.convert_to_memory_tags(source, dest)
			raise NotImplementedError(
				"Mirror requires a convert_to_memory_tags(source, dest) function. "
				"Implement one in your script library and update this endpoint."
			)
			response['mirror'] = {'success': True, 'dest': dest}
		except:
			import traceback
			response['mirror'] = {'success': False, 'error': traceback.format_exc()}

	# Handle deleteTags — remove a tag tree (for cleanup after mirror)
	if 'deleteTags' in data:
		delPath = data['deleteTags']
		try:
			system.tag.deleteTags([delPath])
			response['deleteTags'] = {'success': True}
		except:
			response['deleteTags'] = {'success': False}

	# Handle script — call a gateway script function by dotted path
	if 'script' in data:
		scriptCfg = data['script']
		scriptPath = scriptCfg['path']
		scriptArgs = scriptCfg.get('args', [])
		scriptKwargs = scriptCfg.get('kwargs', {})
		try:
			# Resolve the function from dotted path, e.g. "core.mes.mashing.enzyme_entry.validate_and_submit"
			parts = scriptPath.split('.')
			funcName = parts[-1]
			modulePath = '.'.join(parts[:-1])
			# Navigate the module hierarchy
			mod = __import__(modulePath)
			for comp in parts[1:-1]:
				mod = getattr(mod, comp)
			func = getattr(mod, funcName)
			result = func(*scriptArgs, **scriptKwargs)
			response['script'] = {'success': True, 'result': result}
		except:
			import traceback
			response['script'] = {'success': False, 'error': traceback.format_exc()}

	# Handle writes — auto-create tags if they don't exist
	if 'writes' in data:
		paths = []
		values = []
		for w in data['writes']:
			paths.append(w['path'])
			values.append(w['value'])

		# First attempt: write directly
		writeResults = system.tag.writeBlocking(paths, values)
		results = []
		needCreate = []

		for i, qc in enumerate(writeResults):
			if qc.isGood():
				results.append({
					'path': paths[i],
					'success': True,
					'quality': str(qc)
				})
			else:
				# Tag probably doesn't exist — queue for creation
				needCreate.append(i)
				results.append(None)  # placeholder

		# Create missing tags and retry writes
		if needCreate:
			for idx in needCreate:
				tagPath = paths[idx]
				tagValue = values[idx]
				_ensureTag(tagPath, tagValue)

			# Retry writes for created tags
			retryPaths = [paths[i] for i in needCreate]
			retryValues = [values[i] for i in needCreate]
			retryResults = system.tag.writeBlocking(retryPaths, retryValues)

			for j, idx in enumerate(needCreate):
				qc = retryResults[j]
				results[idx] = {
					'path': paths[idx],
					'success': qc.isGood(),
					'quality': str(qc)
				}

		response['results'] = results

	# Handle importTags — import tag JSON file into the provider via system.tag.configure
	if 'importTags' in data:
		importCfg = data['importTags']
		filePath = importCfg['filePath']
		basePath = importCfg['basePath']
		tagName = importCfg.get('tagName', None)
		collisionPolicy = importCfg.get('collisionPolicy', 'o')
		try:
			import os
			projectRoot = '/usr/local/bin/ignition/data/projects/PLACEHOLDER_PROJECT_NAME'
			fullPath = os.path.join(projectRoot, filePath)
			with open(fullPath, 'r') as f:
				tagJson = f.read()
			tagObj = system.util.jsonDecode(tagJson)
			if tagName:
				tagObj['name'] = tagName
			results = system.tag.configure(basePath, [tagObj], collisionPolicy)
			response['importTags'] = {'success': True, 'results': str(results)}
		except:
			import traceback
			response['importTags'] = {'success': False, 'error': traceback.format_exc()}

	# Handle reads
	if 'reads' in data:
		tagPaths = data['reads']
		tagValues = system.tag.readBlocking(tagPaths)
		values = {}
		for i, qv in enumerate(tagValues):
			values[tagPaths[i]] = {
				'value': qv.value,
				'quality': str(qv.quality),
				'good': qv.quality.isGood()
			}
		response['values'] = values

	return {'json': response}


def _ensureTag(tagPath, value):
	"""Create a memory tag at the given path if it doesn't exist.

	Parses the path to extract provider, folder structure, and tag name.
	Creates the full folder hierarchy and a memory tag of the appropriate type.
	"""
	# Parse "[provider]Folder/SubFolder/TagName"
	providerEnd = tagPath.index(']') + 1
	provider = tagPath[1:providerEnd - 1]  # e.g. "default"
	remainingPath = tagPath[providerEnd:]   # e.g. "Changeover/cooker/state"

	parts = remainingPath.split('/')
	tagName = parts[-1]
	folderParts = parts[:-1]

	# Determine tag data type from value
	dataType = _inferDataType(value)

	# Build the base path for system.tag.configure
	basePath = tagPath[:tagPath.rfind('/')]

	# Create tag configuration
	tagConfig = {
		'name': tagName,
		'tagType': 'AtomicTag',
		'dataType': dataType,
		'value': value
	}

	# system.tag.configure creates parent folders automatically
	result = system.tag.configure(basePath, [tagConfig], 'o')  # 'o' = overwrite if exists
	return result


def _inferDataType(value):
	"""Infer Ignition tag data type from a Python value."""
	if isinstance(value, bool):
		return 'Boolean'
	elif isinstance(value, int):
		return 'Int4'
	elif isinstance(value, float):
		return 'Float8'
	else:
		return 'String'
PYEOF
)
TAGS_DOPOST="${TAGS_DOPOST//PLACEHOLDER_PROJECT_NAME/$PROJECT_NAME}"
write_file "com.inductiveautomation.webdev/resources/testing/tags/doPost.py" "$TAGS_DOPOST"

# --- tags/config.json ---

write_file "com.inductiveautomation.webdev/resources/testing/tags/config.json" "$WEBDEV_CONFIG_JSON"

# --- tags/resource.json ---

WEBDEV_TAGS_RESOURCE=$(cat <<'JSONEOF'
{
  "scope": "G",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": [
    "config.json",
    "doPost.py",
    "doGet.py"
  ],
  "attributes": {
    "lastModification": {
      "actor": "external",
      "timestamp": "2026-01-01T00:00:00Z"
    }
  }
}
JSONEOF
)
write_file "com.inductiveautomation.webdev/resources/testing/tags/resource.json" "$WEBDEV_TAGS_RESOURCE"


# ===================================================================
# 3. Type Stubs — .ignition-stubs/testing/
# ===================================================================

echo ""
echo "--- Type Stubs ---"

# --- __init__.pyi ---

write_file ".ignition-stubs/testing/__init__.pyi" ""

# --- assertions.pyi ---

ASSERTIONS_PYI=$(cat <<'PYIEOF'
from typing import Any

def assert_equal(actual, expected, msg=...) -> Any: ...

def assert_not_equal(actual, expected, msg=...) -> Any: ...

def assert_true(val, msg=...) -> Any: ...

def assert_false(val, msg=...) -> Any: ...

def assert_none(val, msg=...) -> Any: ...

def assert_not_none(val, msg=...) -> Any: ...

def assert_close(actual, expected, tolerance=..., msg=...) -> Any: ...

def assert_raises(callable_fn, exception_type, msg=...) -> Any: ...

def assert_tag_value(tag_path, expected, msg=...) -> Any: ...

def assert_contains(container, item, msg=...) -> Any: ...

def assert_isinstance(obj, expected_type, msg=...) -> Any: ...

class TestAssertionError(AssertionError):
    def __init__(self, message, actual=..., expected=...) -> Any: ...
PYIEOF
)
write_file ".ignition-stubs/testing/assertions.pyi" "$ASSERTIONS_PYI"

# --- decorators.pyi ---

DECORATORS_PYI=$(cat <<'PYIEOF'
from typing import Any

def test(func) -> Any: ...

def skip(reason=...) -> Any: ...

def setup(func) -> Any: ...

def teardown(func) -> Any: ...

def expected_error(exception_type) -> Any: ...
PYIEOF
)
write_file ".ignition-stubs/testing/decorators.pyi" "$DECORATORS_PYI"

# --- helpers.pyi (stripped: no run_process_queue or _run_process_queue_direct) ---

HELPERS_PYI=$(cat <<'PYIEOF'
from typing import Any

def write_dataset_tag(tag_path, columns, types, rows) -> Any: ...

def clear_dataset_tag(tag_path, columns, types) -> Any: ...
PYIEOF
)
write_file ".ignition-stubs/testing/helpers.pyi" "$HELPERS_PYI"

# --- reporter.pyi ---

REPORTER_PYI=$(cat <<'PYIEOF'
from typing import Any

def to_json(results) -> Any: ...

def to_console(results) -> Any: ...

def to_junit_xml(results) -> Any: ...

def _escape_xml(text) -> Any: ...
PYIEOF
)
write_file ".ignition-stubs/testing/reporter.pyi" "$REPORTER_PYI"

# --- runner.pyi ---

RUNNER_PYI=$(cat <<'PYIEOF'
from typing import Any

def run_all(base_package=...) -> Any: ...

def run_module(module_path) -> Any: ...

def _discover_test_modules() -> Any: ...

def _walk_for_tests(directory, base_dir, modules, seen) -> Any: ...

def _import_module(module_path) -> Any: ...

def _run_single_test(name, func) -> Any: ...
PYIEOF
)
write_file ".ignition-stubs/testing/runner.pyi" "$RUNNER_PYI"


# ===================================================================
# Summary
# ===================================================================

echo ""
if [[ "$DRY_RUN" = true ]]; then
  echo "Dry run complete. No files were written."
else
  echo "Scaffold complete: $CREATED created, $SKIPPED skipped."
fi
