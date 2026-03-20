"""Find embedded scripts in Ignition JSON resource files.

Port of lua/ignition/json_parser.lua. Reads files from disk (not editor
buffers), making it usable from any editor via LSP custom methods.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ignition_lsp.encoding import decode, is_encoded_script

# JSON keys that contain embedded scripts in Ignition resources.
# Must stay in sync with lua/ignition/json_parser.lua SCRIPT_KEYS.
SCRIPT_KEYS = [
    "script",
    "code",
    "eventScript",
    "transform",
    "onActionPerformed",
    "onChange",
    "onStartup",
    "onShutdown",
    "expression",
]

# Human-readable labels for script key types
_CONTEXT_LABELS = {
    "script": "Script",
    "code": "Transform Code",
    "eventScript": "Event Script",
    "transform": "Script Transform",
    "onActionPerformed": "Action Script",
    "onChange": "Change Script",
    "onStartup": "Startup Script",
    "onShutdown": "Shutdown Script",
    "expression": "Expression",
}


@dataclass
class ScriptLocation:
    """A script found embedded in an Ignition JSON file."""

    key: str
    line: int  # 1-based line number
    content: str  # Raw encoded content
    context: str  # Human-readable description (e.g. "MyTag/valueChanged")
    decoded_preview: str = field(default="")  # First ~80 chars of decoded content


def find_scripts(file_path: str) -> List[ScriptLocation]:
    """Find all embedded scripts in an Ignition JSON file.

    Args:
        file_path: Path to the JSON file (or raw text lines).

    Returns:
        List of ScriptLocation objects for each script found.
    """
    path = Path(file_path)
    if not path.is_file():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    return find_scripts_in_lines(lines)


def find_scripts_in_lines(lines: List[str]) -> List[ScriptLocation]:
    """Find all embedded scripts in a list of text lines.

    This is the core scanning logic, separated from file I/O for testability.
    """
    scripts: List[ScriptLocation] = []

    for line_num_0, line_text in enumerate(lines):
        line_num = line_num_0 + 1  # 1-based

        for key in SCRIPT_KEYS:
            # Build a pattern: "key" : "  (with optional whitespace)
            match = re.search(rf'"({re.escape(key)})"\s*:\s*"', line_text)
            if not match:
                continue

            captured_key = match.group(1)
            value_start = match.end()  # Position right after the opening quote

            content = _extract_json_string_value(line_text, value_start)
            if content is None or content == "":
                continue

            # Expressions are always valid; scripts need encoded markers
            if captured_key == "expression" or is_encoded_script(content):
                context = _get_context(lines, line_num_0, captured_key)
                decoded = decode(content)
                preview = decoded[:80] + ("..." if len(decoded) > 80 else "")

                scripts.append(
                    ScriptLocation(
                        key=captured_key,
                        line=line_num,
                        content=content,
                        context=context,
                        decoded_preview=preview,
                    )
                )

    return scripts


def _extract_json_string_value(text: str, start: int) -> Optional[str]:
    """Extract a JSON string value starting at position, handling escapes.

    Args:
        text: The full line of text.
        start: Index right after the opening quote character.

    Returns:
        The raw string content (without quotes), or None if malformed.
    """
    result: list[str] = []
    i = start

    while i < len(text):
        char = text[i]

        if char == "\\" and i + 1 < len(text):
            # Escape sequence — include both characters verbatim
            result.append(char)
            result.append(text[i + 1])
            i += 2
        elif char == '"':
            # Unescaped quote — end of string
            return "".join(result)
        else:
            result.append(char)
            i += 1

    # String didn't close
    return None


def replace_script_in_line(
    line_text: str, key: str, new_encoded_content: str
) -> str:
    """Replace the script content for a given key in a JSON line.

    Args:
        line_text: The original line.
        key: The script key (e.g. "eventScript").
        new_encoded_content: The new encoded script content.

    Returns:
        The modified line, or the original line if the key wasn't found.
    """
    match = re.search(rf'"({re.escape(key)})"\s*:\s*"', line_text)
    if not match:
        return line_text

    value_start = match.end()
    old_content = _extract_json_string_value(line_text, value_start)
    if old_content is None:
        return line_text

    # Reconstruct: everything before value + new content + closing quote + rest
    before = line_text[:value_start]
    after_old = value_start + len(old_content)
    # Skip the closing quote of the old value
    rest = line_text[after_old + 1:] if after_old < len(line_text) else ""

    return before + new_encoded_content + '"' + rest


def _get_context(lines: List[str], line_idx: int, key: str) -> str:
    """Get a human-readable context string for a script.

    For eventScript entries, scans backward to find tag name + event name.
    For expression entries, scans backward to find the tag name.
    """
    if key == "eventScript":
        ctx = _get_tag_context(lines, line_idx)
        if ctx:
            return ctx
    elif key == "expression":
        ctx = _get_expression_context(lines, line_idx)
        if ctx:
            return ctx

    return _CONTEXT_LABELS.get(key, f"Script ({key})")


def _get_tag_context(lines: List[str], script_line_idx: int) -> Optional[str]:
    """Scan backward from the script line to find event name and tag name."""
    event_name: Optional[str] = None
    tag_name: Optional[str] = None

    start = max(0, script_line_idx - 20)
    for i in range(script_line_idx - 1, start - 1, -1):
        line = lines[i]

        if event_name is None:
            m = re.search(r'"(\w+)"\s*:\s*\{', line)
            if m and m.group(1) != "eventScripts":
                event_name = m.group(1)

        if tag_name is None:
            m = re.search(r'"name"\s*:\s*"([^"]*)"', line)
            if m:
                tag_name = m.group(1)

        if event_name and tag_name:
            break

    if tag_name and event_name:
        return f"{tag_name}/{event_name}"
    if tag_name:
        return f"{tag_name}/Event Script"
    if event_name:
        return event_name
    return None


def _get_expression_context(
    lines: List[str], script_line_idx: int
) -> Optional[str]:
    """Scan backward from the expression line to find the tag name."""
    start = max(0, script_line_idx - 15)
    for i in range(script_line_idx - 1, start - 1, -1):
        m = re.search(r'"name"\s*:\s*"([^"]*)"', lines[i])
        if m:
            return f"{m.group(1)}/Expression"
    return None
