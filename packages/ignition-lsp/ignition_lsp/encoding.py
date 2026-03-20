"""Ignition Flint encoding/decoding for embedded scripts.

Direct port of lua/ignition/encoding.lua. The encoding used by Ignition
when storing Python scripts inside JSON resource files.

IMPORTANT: Round-trip fidelity is sacred — encode(decode(x)) == x must
always hold. See tests/fixtures/encoding_test_vectors.json for shared
test cases validated by both the Lua and Python implementations.
"""

from typing import List, Tuple

# Character replacement map — same order as encoding.lua.
# Backslash MUST be first to avoid double-escaping.
REPLACEMENT_CHARS: List[Tuple[str, str]] = [
    ("\\", "\\\\"),      # Backslash (must be first!)
    ('"', '\\"'),        # Double quote
    ("\t", "\\t"),       # Tab
    ("\b", "\\b"),       # Backspace
    ("\n", "\\n"),       # Newline
    ("\r", "\\r"),       # Carriage return
    ("\f", "\\f"),       # Form feed
    ("<", "\\u003c"),    # Less than (Unicode escape)
    (">", "\\u003e"),    # Greater than (Unicode escape)
    ("&", "\\u0026"),    # Ampersand (Unicode escape)
    ("=", "\\u003d"),    # Equals (Unicode escape)
    ("'", "\\u0027"),    # Single quote (Unicode escape)
]

# Single-char escape map for decoding (after a backslash)
_ESCAPE_MAP = {
    "\\": "\\",
    '"': '"',
    "t": "\t",
    "b": "\b",
    "n": "\n",
    "r": "\r",
    "f": "\f",
}

# Unicode escape map for decoding (\uXXXX)
_UNICODE_MAP = {
    "003c": "<",
    "003e": ">",
    "0026": "&",
    "003d": "=",
    "0027": "'",
}


def encode(decoded: str) -> str:
    """Encode a Python script for storage in Ignition JSON.

    Multi-pass replacement in order. Backslash is replaced first to
    prevent double-escaping subsequent replacements.
    """
    if not decoded:
        return ""

    result = decoded
    for raw, escaped in REPLACEMENT_CHARS:
        result = result.replace(raw, escaped)
    return result


def decode(encoded: str) -> str:
    """Decode an Ignition-encoded script back to plain Python.

    Single-pass parser to correctly distinguish \\\\t (literal backslash + t)
    from \\t (tab escape). Multi-pass replacement cannot handle this safely.
    """
    if not encoded:
        return ""

    result: list[str] = []
    i = 0
    length = len(encoded)

    while i < length:
        if encoded[i] == "\\" and i + 1 < length:
            next_char = encoded[i + 1]

            if next_char == "u" and i + 5 < length:
                # Potential unicode escape: \uXXXX
                code = encoded[i + 2 : i + 6]
                if code in _UNICODE_MAP:
                    result.append(_UNICODE_MAP[code])
                    i += 6
                    continue
                # Unknown unicode escape — keep the backslash
                result.append("\\")
                i += 1
            elif next_char in _ESCAPE_MAP:
                result.append(_ESCAPE_MAP[next_char])
                i += 2
            else:
                # Unknown escape — keep the backslash
                result.append("\\")
                i += 1
        else:
            result.append(encoded[i])
            i += 1

    return "".join(result)


def dedent(text: str) -> tuple:
    """Strip common leading whitespace from all lines.

    Ignition stores scripts with leading tab indentation. This strips the
    common prefix so the script is at the correct indentation level for editing.
    Handles mixed whitespace (e.g. stray spaces alongside tabs) by finding
    the minimum indentation level in tabs.

    Returns (dedented_text, indent_prefix) so the indent can be restored on save.
    """
    if not text:
        return ("", "")

    lines = text.split("\n")

    # Find the minimum leading-tab count across non-empty lines.
    # Ignition uses tab indentation. Some lines may have stray spaces
    # before or mixed with tabs — we count the tabs at any position
    # in the leading whitespace to determine the indent level.
    min_tabs: int | None = None
    for line in lines:
        if not line.strip():
            continue
        # Count tabs in leading whitespace (ignore interspersed spaces)
        leading = len(line) - len(line.lstrip())
        tab_count = line[:leading].count("\t")
        if min_tabs is None:
            min_tabs = tab_count
        else:
            min_tabs = min(min_tabs, tab_count)

    if not min_tabs:
        return (text, "")

    # Strip min_tabs worth of tabs from the leading whitespace of each line.
    # Handles stray spaces by removing them alongside the tabs.
    result = []
    for line in lines:
        if not line.strip():
            result.append("")
            continue
        # Remove min_tabs tabs from the front (plus any interspersed spaces)
        stripped = line
        tabs_removed = 0
        while tabs_removed < min_tabs and stripped:
            if stripped[0] == "\t":
                stripped = stripped[1:]
                tabs_removed += 1
            elif stripped[0] == " ":
                stripped = stripped[1:]  # Skip stray spaces
            else:
                break
        result.append(stripped)

    return ("\n".join(result), "\t" * min_tabs)


def reindent(text: str, indent: str) -> str:
    """Re-add leading indentation stripped by dedent().

    Only indents non-empty lines.
    """
    if not indent:
        return text
    return "\n".join(
        indent + line if line.strip() else ""
        for line in text.split("\n")
    )


def is_encoded_script(text: str) -> bool:
    """Test if a string appears to be an Ignition-encoded script."""
    if not text:
        return False

    markers = ("\\n", "\\t", '\\"', "\\u00")
    return any(marker in text for marker in markers)
