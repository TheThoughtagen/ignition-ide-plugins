"""Utilities for classifying virtual buffer URIs."""

import re
from urllib.parse import unquote

# Matches expression buffer names:
#   [Ignition:tags.json:MyTag>Expression:L42]  (context variant, '>' separator)
#   [Ignition:tags.json:expression:L42]         (plain key variant)
#   [Ignition:tags.json:MyTag/Expression:L42]   (legacy '/' separator)
_EXPRESSION_RE = re.compile(
    r"\[Ignition:[^\]]*[/>:]expression:L\d+\]", re.IGNORECASE
)


def _decode_uri(uri: str) -> str:
    """Percent-decode a URI so bracket buffer names can be matched.

    Neovim sends virtual buffer names as file:// URIs with percent-encoding
    (e.g. ``[`` → ``%5b``, ``>`` → ``%3e``).  Decode once so the regex and
    literal checks below work on the original buffer name characters.
    """
    return unquote(uri)


def is_expression_buffer(uri: str) -> bool:
    """Return True if *uri* belongs to a virtual expression buffer."""
    return bool(_EXPRESSION_RE.search(_decode_uri(uri)))


def is_virtual_buffer(uri: str) -> bool:
    """Return True if *uri* belongs to any Ignition virtual buffer."""
    return "[Ignition:" in _decode_uri(uri)
