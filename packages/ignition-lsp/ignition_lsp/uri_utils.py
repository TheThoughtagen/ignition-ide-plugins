"""Utilities for classifying virtual buffer URIs.

Supports two URI formats:
- Neovim:  [Ignition:tags.json:MyTag>Expression:L42]
- VS Code: ignition-script:///{base64-source}/{key}/{line}
"""

import re
from urllib.parse import unquote

# Matches Neovim expression buffer names:
#   [Ignition:tags.json:MyTag>Expression:L42]  (context variant, '>' separator)
#   [Ignition:tags.json:expression:L42]         (plain key variant)
#   [Ignition:tags.json:MyTag/Expression:L42]   (legacy '/' separator)
_EXPRESSION_RE = re.compile(
    r"\[Ignition:[^\]]*[/>:]expression:L\d+\]", re.IGNORECASE
)

# VS Code URI scheme for decoded scripts (single slash — VS Code LSP client
# normalizes ignition-script:///path to ignition-script:/path)
_VSCODE_SCHEME = "ignition-script:"

# Script keys that are expressions (not Python)
_EXPRESSION_KEYS = {"expression"}


def _decode_uri(uri: str) -> str:
    """Percent-decode a URI so bracket buffer names can be matched.

    Neovim sends virtual buffer names as file:// URIs with percent-encoding
    (e.g. ``[`` → ``%5b``, ``>`` → ``%3e``).  Decode once so the regex and
    literal checks below work on the original buffer name characters.
    """
    return unquote(uri)


def _parse_vscode_uri(uri: str) -> tuple:
    """Parse a VS Code ignition-script URI into (source, key, line).

    Handles both forms the URI may take:
    - ignition-script:///base64/key/line  (from Uri.parse)
    - ignition-script:/base64/key/line    (after LSP client normalization)

    Returns ("", "", 0) if the URI doesn't match the expected format.
    """
    decoded = _decode_uri(uri)
    if not decoded.startswith(_VSCODE_SCHEME):
        return ("", "", 0)
    path = decoded[len(_VSCODE_SCHEME):]
    parts = [p for p in path.split("/") if p]  # Split and drop empty segments
    if len(parts) >= 3:
        return (parts[0], parts[1], parts[2])
    return ("", "", 0)


def is_expression_buffer(uri: str) -> bool:
    """Return True if *uri* belongs to a virtual expression buffer."""
    decoded = _decode_uri(uri)

    # Neovim format
    if _EXPRESSION_RE.search(decoded):
        return True

    # VS Code format: ignition-script:///{base64}/{key}/{line}
    _, key, _ = _parse_vscode_uri(decoded)
    if key.lower() in _EXPRESSION_KEYS:
        return True

    return False


def is_virtual_buffer(uri: str) -> bool:
    """Return True if *uri* belongs to any Ignition virtual buffer."""
    decoded = _decode_uri(uri)
    return "[Ignition:" in decoded or decoded.startswith(_VSCODE_SCHEME)
