"""Sidecar files for editing scripts embedded in Ignition JSON resources.

Editors like Neovim and VS Code decode an embedded script into an in-memory
virtual buffer. Editors without a virtual-document API — Zed, Helix, and any
other plain LSP client — cannot do that, so this module backs the same
workflow with a real file on disk.

A decoded script is written to ``.ignition-scripts/`` under the project root
with a comment header recording where it came from. Saving it back parses that
header and writes the re-encoded script into the original JSON line.

This module is pure logic — path building, header formatting, and parsing. All
file I/O lives in ``server.py`` so the rules here stay directly testable.
"""

import base64
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Directory (relative to the project root) holding decoded sidecar scripts.
SCRIPTS_DIR_NAME = ".ignition-scripts"

# Sentinels bracketing the metadata header. Distinctive enough that a decoded
# script's own comments can never be mistaken for a header.
HEADER_BEGIN = "# >>> ignition-lsp:begin"
HEADER_END = "# <<< ignition-lsp:end"

_FIELD_RE = re.compile(r"^#\s*(source|key|line|indent|digest):\s*(.*)$")


@dataclass
class ScriptRef:
    """Where a decoded sidecar script came from."""

    source_uri: str
    key: str
    line: int  # 1-based line number in the source JSON
    indent: str  # Leading indentation stripped by dedent(), restored on save
    digest: str  # Digest of the encoded script as it was at decode time


def content_digest(encoded: str) -> str:
    """Fingerprint an encoded script so a stale sidecar can be detected.

    A sidecar outlives the editing session that produced it, so by the time it
    is saved the source JSON may have been edited, reordered, or regenerated.
    Comparing this digest against the script currently at (line, key) is what
    stops a save from overwriting a *different* script that has since moved
    into that position.
    """
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def sidecar_filename(source_path: str, key: str, line: int) -> str:
    """Build a flat, collision-resistant filename for a decoded script.

    The source path is flattened into the filename (rather than mirrored as
    nested directories) so every sidecar sits directly in one folder that is
    easy to inspect and to delete. Flattening alone is ambiguous — both
    ``views/Main__view.json`` and ``views__Main/view.json`` flatten to the same
    string — so a short digest of the original path disambiguates them.

    Args:
        source_path: Path to the JSON file, relative to the project root.
        key: The script key (e.g. "eventScript").
        line: 1-based line number of the script in the source file.
    """
    normalized = source_path.replace("\\", "/").strip("/")
    flat = normalized.replace("/", "__")
    path_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{flat}__{key}__L{line}__{path_hash}.py"


def sidecar_path(project_root: str, source_path: str, key: str, line: int) -> Path:
    """Full path to the sidecar file for a script.

    Args:
        project_root: Ignition project root (the directory holding project.json).
        source_path: Absolute path to the source JSON file.
        key: The script key.
        line: 1-based line number of the script in the source file.
    """
    root = Path(project_root)
    try:
        relative = str(Path(source_path).relative_to(root))
    except ValueError:
        # Source lives outside the project root — fall back to the bare filename
        # so the sidecar still lands somewhere predictable.
        relative = Path(source_path).name

    return root / SCRIPTS_DIR_NAME / sidecar_filename(relative, key, line)


def build_header(ref: ScriptRef) -> str:
    """Render the metadata header prepended to a decoded sidecar script.

    The indent is stored base64-encoded: it is whitespace, which would
    otherwise be invisible in — and stripped by — the comment line.
    """
    encoded_indent = base64.b64encode(ref.indent.encode("utf-8")).decode("ascii")
    return "\n".join(
        [
            HEADER_BEGIN,
            "# Decoded from an Ignition JSON resource. Do not edit this header.",
            f"# source: {ref.source_uri}",
            f"# key: {ref.key}",
            f"# line: {ref.line}",
            f"# indent: {encoded_indent}",
            f"# digest: {ref.digest}",
            "# Run the 'Ignition: Save script back to JSON' code action to write",
            "# your changes into the source file.",
            HEADER_END,
            "",
        ]
    )


def parse_header(text: str) -> Optional[ScriptRef]:
    """Parse the metadata header from a sidecar script.

    Returns None unless a complete, well-formed header is present — a partial
    or hand-mangled header must never be guessed at, because the result decides
    which bytes get written back into a project file.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != HEADER_BEGIN:
        return None

    fields = {}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == HEADER_END:
            break
        match = _FIELD_RE.match(stripped)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    else:
        # No terminator found.
        return None

    if not {"source", "key", "line", "indent", "digest"}.issubset(fields):
        return None

    if not fields["digest"]:
        return None

    try:
        line_num = int(fields["line"])
    except ValueError:
        return None

    try:
        indent = base64.b64decode(fields["indent"].encode("ascii")).decode("utf-8")
    except Exception:
        return None

    return ScriptRef(
        source_uri=fields["source"],
        key=fields["key"],
        line=line_num,
        indent=indent,
        digest=fields["digest"],
    )


def strip_header(text: str) -> str:
    """Remove the metadata header, returning the script body alone.

    Returns the text unchanged when no complete header is present.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != HEADER_BEGIN:
        return text

    for index, line in enumerate(lines):
        if line.strip() == HEADER_END:
            body: List[str] = lines[index + 1 :]
            return "\n".join(body)

    return text


def build_sidecar_content(ref: ScriptRef, decoded: str) -> str:
    """Combine the metadata header and a decoded script body."""
    return build_header(ref) + decoded
