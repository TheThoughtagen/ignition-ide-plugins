"""Diagnostics provider integrating ignition-lint validation."""

from __future__ import annotations

import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import List, Union

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from pygls.workspace import TextDocument

from .uri_utils import is_expression_buffer, is_virtual_buffer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import strategy: prefer installed ignition-lint-toolkit package, fall back
# to sibling repo checkout for local development.
# ---------------------------------------------------------------------------
_LINT_AVAILABLE = False
_PERSPECTIVE_AVAILABLE = False

try:
    from ignition_lint.validators.jython import JythonValidator
    from ignition_lint.reporting import LintIssue, LintSeverity

    _LINT_AVAILABLE = True
except ImportError:
    # Fallback: sibling repo checkout (dev only)
    _SIBLING_PATH = Path(__file__).parent.parent.parent.parent / "ignition-lint" / "src"
    if _SIBLING_PATH.exists():
        sys.path.insert(0, str(_SIBLING_PATH))
        try:
            from ignition_lint.validators.jython import JythonValidator
            from ignition_lint.reporting import LintIssue, LintSeverity

            _LINT_AVAILABLE = True
            logger.info(f"Loaded ignition-lint from sibling path: {_SIBLING_PATH}")
        except ImportError as e:
            logger.warning(f"Could not import ignition-lint from sibling path: {e}")
    else:
        logger.warning("ignition-lint not installed and sibling path not found")

if _LINT_AVAILABLE:
    try:
        from ignition_lint.perspective import IgnitionPerspectiveLinter

        _PERSPECTIVE_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Perspective linter not available: {e}")

_TAG_LINTER_AVAILABLE = False
if _LINT_AVAILABLE:
    try:
        from ignition_lint.tags import IgnitionTagLinter

        _TAG_LINTER_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Tag linter not available: {e}")

# ---------------------------------------------------------------------------
# Shared severity mapping
# ---------------------------------------------------------------------------


def _map_severity(lint_severity: "LintSeverity") -> DiagnosticSeverity:
    """Map ignition-lint severity to LSP severity."""
    if not _LINT_AVAILABLE:
        return DiagnosticSeverity.Warning
    _MAP = {
        LintSeverity.ERROR: DiagnosticSeverity.Error,
        LintSeverity.WARNING: DiagnosticSeverity.Warning,
        LintSeverity.INFO: DiagnosticSeverity.Information,
    }
    # STYLE maps to Hint if present, otherwise Information
    if hasattr(LintSeverity, "STYLE"):
        _MAP[LintSeverity.STYLE] = DiagnosticSeverity.Hint
    return _MAP.get(lint_severity, DiagnosticSeverity.Warning)


def _issue_to_diagnostic(issue: "LintIssue", content: str) -> Diagnostic:
    """Convert a single LintIssue to an LSP Diagnostic."""
    line_num = (issue.line_number or 1) - 1  # Convert to 0-indexed
    line_num = max(0, line_num)

    lines = content.split("\n")
    if line_num < len(lines):
        line_length = len(lines[line_num])
    else:
        line_length = 0

    col_start = 0
    col_end = line_length
    if issue.column is not None and issue.column > 0:
        col_start = issue.column - 1  # 0-indexed
        # Narrow the range so the diagnostic doesn't span to end of line.
        # This keeps virtual text visible on long single-line expressions.
        end_col = issue.metadata.get("end_column") if issue.metadata else None
        if end_col is not None:
            col_end = int(end_col)
        else:
            col_end = min(col_start + 20, line_length)

    message = issue.message
    if issue.suggestion:
        message += f"\n💡 {issue.suggestion}"

    return Diagnostic(
        range=Range(
            start=Position(line=line_num, character=col_start),
            end=Position(line=line_num, character=col_end),
        ),
        severity=_map_severity(issue.severity),
        code=issue.code,
        source="ignition-lint",
        message=message,
    )


# ---------------------------------------------------------------------------
# Jython script diagnostics (virtual buffers, .py files)
# ---------------------------------------------------------------------------


def _get_jython_diagnostics(
    content: str, uri: str, standalone: bool = False
) -> List[Diagnostic]:
    """Run JythonValidator on script content."""
    if not _LINT_AVAILABLE:
        return []

    diagnostics = []
    try:
        validator = JythonValidator()
        issues = validator.validate_script(content, context=uri, standalone=standalone)
        for issue in issues:
            diagnostics.append(_issue_to_diagnostic(issue, content))
    except Exception as e:
        logger.error(f"Error in Jython diagnostics: {e}", exc_info=True)

    return diagnostics


# ---------------------------------------------------------------------------
# Expression diagnostics (virtual expression buffers)
# ---------------------------------------------------------------------------


_EXPRESSION_LINT_AVAILABLE = False
if _LINT_AVAILABLE:
    try:
        from ignition_lint.validators.expression import ExpressionValidator

        _EXPRESSION_LINT_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Expression validator not available: {e}")


def _get_expression_diagnostics(content: str, uri: str) -> List[Diagnostic]:
    """Run ExpressionValidator on expression content."""
    if not _EXPRESSION_LINT_AVAILABLE:
        return []

    diagnostics = []
    try:
        validator = ExpressionValidator()
        issues = validator.validate_expression(
            content,
            context="",
            file_path=uri,
            component_path="",
            component_type="expression",
        )
        for issue in issues:
            diagnostics.append(_issue_to_diagnostic(issue, content))
    except Exception as e:
        logger.error(f"Error in expression diagnostics: {e}", exc_info=True)

    return diagnostics


# ---------------------------------------------------------------------------
# Perspective view diagnostics (.json files)
# ---------------------------------------------------------------------------


def _get_perspective_diagnostics(document: TextDocument) -> List[Diagnostic]:
    """Run IgnitionPerspectiveLinter on a Perspective view.json file."""
    if not _PERSPECTIVE_AVAILABLE:
        return []

    diagnostics = []
    try:
        # Write current buffer content to a temp file so we lint the
        # in-memory state, not whatever is on disk (important for did_change).
        content = document.source
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            linter = IgnitionPerspectiveLinter()
            linter.issues.clear()
            linter.lint_file(tmp_path)

            for issue in linter.issues:
                diagnostics.append(_issue_to_diagnostic(issue, content))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Error in Perspective diagnostics: {e}", exc_info=True)

    return diagnostics


def _is_perspective_view(content: str) -> bool:
    """Quick check if JSON content looks like a Perspective view."""
    # Lightweight heuristic: check for root.type starting with "ia."
    # without fully parsing JSON (fast enough for gating).
    try:
        data = json.loads(content)
        root = data.get("root", {})
        root_type = root.get("type", "")
        return isinstance(root_type, str) and root_type.startswith("ia.")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Tag / UDT diagnostics (.json files with tagType or tags)
# ---------------------------------------------------------------------------


def _is_tag_json(content: str) -> bool:
    """Quick check if JSON content looks like a tag or UDT definition."""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return "tagType" in data or "tags" in data
        return False
    except (json.JSONDecodeError, TypeError):
        return False


def _find_script_line(raw_text: str, key: str, value_prefix: str) -> int:
    """Find the 0-indexed line number of a script key in raw JSON text.

    Searches for the pattern "key": "value_start..." to locate the line.
    Returns 0-indexed line number for LSP diagnostics, or 0 if not found.
    """
    search_key = f'"{key}"'
    # JSON-escape value_prefix to match the raw JSON text
    # Use the first 30 chars for matching
    value_slice = value_prefix[:30]
    # json.dumps adds surrounding quotes, so strip them
    escaped_value = json.dumps(value_slice)[1:-1]

    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        if search_key in line and escaped_value[:20] in line:
            return i

    # Fallback: just find the key
    for i, line in enumerate(lines):
        if search_key in line:
            return i

    return 0


def _walk_tag_scripts(
    node: Union[dict, list],
    raw_text: str,
    diagnostics: List[Diagnostic],
    uri: str,
    tag_name: str = "",
) -> None:
    """Recursively walk a tag JSON structure finding eventScript and expression entries."""
    if isinstance(node, dict):
        # Track tag name for context
        current_name = node.get("name", tag_name)

        # NOTE: Expression fields (expression tags, derived tags) are NOT
        # validated inline in the JSON — expressions are typically single-line
        # and inline diagnostics just highlight the whole line red with no
        # useful context. Expression diagnostics run in the virtual buffer
        # instead, where the user can see and interact with the content.

        # Check for eventScripts block
        event_scripts = node.get("eventScripts")
        if isinstance(event_scripts, dict):
            for event_name, event_data in event_scripts.items():
                if not isinstance(event_data, dict):
                    continue
                script = event_data.get("eventScript", "")
                if not script or not script.strip():
                    continue

                # json.loads already decoded Flint encoding, so `script` is
                # ready for Jython validation
                script_diags = _get_jython_diagnostics(script, uri)

                # Find where this eventScript appears in the raw JSON
                json_line = _find_script_line(raw_text, "eventScript", script)

                # Remap diagnostics to point at the JSON line with context
                context = f"{current_name}/{event_name}" if current_name else event_name
                for diag in script_diags:
                    script_line = diag.range.start.line
                    diag.message = f"[{context}] Line {script_line + 1}: {diag.message}"
                    diag.range = Range(
                        start=Position(line=json_line, character=0),
                        end=Position(line=json_line, character=1),
                    )
                    diagnostics.append(diag)

        # Recurse into nested tags
        tags = node.get("tags")
        if isinstance(tags, list):
            for child in tags:
                _walk_tag_scripts(child, raw_text, diagnostics, uri, current_name)

    elif isinstance(node, list):
        for item in node:
            _walk_tag_scripts(item, raw_text, diagnostics, uri, tag_name)


def _get_tag_structural_diagnostics(document: "TextDocument") -> List[Diagnostic]:
    """Run IgnitionTagLinter on a tag/UDT JSON file for structural validation."""
    if not _TAG_LINTER_AVAILABLE:
        return []

    diagnostics = []
    try:
        content = document.source
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            linter = IgnitionTagLinter()
            linter.issues.clear()
            linter.lint_file(tmp_path)

            for issue in linter.issues:
                diagnostics.append(_issue_to_diagnostic(issue, content))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Error in tag structural diagnostics: {e}", exc_info=True)

    return diagnostics


def _get_tag_diagnostics(document: "TextDocument") -> List[Diagnostic]:
    """Run structural + Jython validation on a tag/UDT JSON file."""
    content = document.source
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return []

    diagnostics: List[Diagnostic] = []

    # Structural validation via IgnitionTagLinter
    diagnostics.extend(_get_tag_structural_diagnostics(document))

    # Jython script validation (existing walk)
    _walk_tag_scripts(data, content, diagnostics, document.uri)
    return diagnostics


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def get_diagnostics(document: TextDocument) -> List[Diagnostic]:
    """Get diagnostics for a document using ignition-lint."""
    uri = document.uri
    content = document.source

    # Virtual buffers ([Ignition: prefix or ignition-script: scheme)
    if is_virtual_buffer(uri):
        if is_expression_buffer(uri):
            logger.debug(f"Running expression diagnostics on virtual buffer: {uri}")
            return _get_expression_diagnostics(content, uri)
        logger.debug(f"Running Jython diagnostics on virtual buffer: {uri}")
        return _get_jython_diagnostics(content, uri, standalone=True)

    # JSON files → check syntax first, then if Perspective view
    if uri.endswith(".json"):
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            # Surface the parse error as a diagnostic so the user sees it
            line = max(0, (e.lineno or 1) - 1)
            col = max(0, (e.colno or 1) - 1)
            return [
                Diagnostic(
                    range=Range(
                        start=Position(line=line, character=col),
                        end=Position(line=line, character=col + 1),
                    ),
                    severity=DiagnosticSeverity.Error,
                    code="JSON_SYNTAX_ERROR",
                    source="ignition-lint",
                    message=f"JSON syntax error: {e.msg}",
                )
            ]

        if _is_perspective_view(content):
            logger.debug(f"Running Perspective diagnostics on: {uri}")
            return _get_perspective_diagnostics(document)

        if _is_tag_json(content):
            logger.debug(f"Running tag diagnostics on: {uri}")
            return _get_tag_diagnostics(document)

        logger.debug(f"Skipping unrecognized JSON file: {uri}")
        return []

    # Python / other files → Jython validation
    return _get_jython_diagnostics(content, uri)


def get_diagnostics_for_file(file_path: str, content: str) -> List[Diagnostic]:
    """Get diagnostics for a file path and content."""

    class MockDocument:
        def __init__(self, uri: str, source: str):
            self.uri = uri
            self.source = source

    doc = MockDocument(file_path, content)
    return get_diagnostics(doc)
