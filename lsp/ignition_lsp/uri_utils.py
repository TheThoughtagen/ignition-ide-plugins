"""Utilities for classifying virtual buffer URIs."""

import re

# Matches both forms of expression buffer names:
#   [Ignition:tags.json:MyTag/Expression:L42]  (context variant)
#   [Ignition:tags.json:expression:L42]         (plain key variant)
_EXPRESSION_RE = re.compile(
    r"\[Ignition:[^\]]*[/:]expression:L\d+\]", re.IGNORECASE
)


def is_expression_buffer(uri: str) -> bool:
    """Return True if *uri* belongs to a virtual expression buffer."""
    return bool(_EXPRESSION_RE.search(uri))


def is_virtual_buffer(uri: str) -> bool:
    """Return True if *uri* belongs to any Ignition virtual buffer."""
    return "[Ignition:" in uri
