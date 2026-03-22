"""JSON completion provider for Perspective view.json files.

Offers context-aware completions for component types, structural keys,
prop names, and event handlers when editing Perspective views.
"""

import json
import logging
from typing import List, Optional, Tuple

from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionList,
)
from pygls.workspace import TextDocument

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────

COMPONENT_TYPES = [
    "ia.container.flex",
    "ia.container.coord",
    "ia.container.column",
    "ia.container.row",
    "ia.container.tab",
    "ia.container.carousel",
    "ia.container.split",
    "ia.display.label",
    "ia.display.icon",
    "ia.display.image",
    "ia.display.markdown",
    "ia.display.progress-bar",
    "ia.display.led-display",
    "ia.display.cylindrical-tank",
    "ia.display.thermometer",
    "ia.display.linear-scale",
    "ia.display.gauge",
    "ia.display.flex-repeater",
    "ia.display.table",
    "ia.display.pdf-viewer",
    "ia.display.video-player",
    "ia.input.button",
    "ia.input.toggle-switch",
    "ia.input.checkbox",
    "ia.input.radio-group",
    "ia.input.dropdown",
    "ia.input.text-field",
    "ia.input.text-area",
    "ia.input.numeric-entry",
    "ia.input.slider",
    "ia.input.range-slider",
    "ia.input.date-time-input",
    "ia.input.file-upload",
    "ia.input.color-picker",
    "ia.chart.xy",
    "ia.chart.pie",
    "ia.chart.bar",
    "ia.map.map",
    "ia.navigation.link",
    "ia.navigation.tab-strip",
    "ia.navigation.breadcrumb",
    "ia.navigation.menu-tree",
    "ia.display.alarm-journal",
    "ia.display.alarm-status-table",
    "ia.display.power-chart",
    "ia.display.equipment-schedule",
    "ia.display.sparkline",
    "ia.display.symbols",
    "ia.display.inline-frame",
    "ia.display.tag-browse-tree",
]

COMPONENT_KEYS = [
    "type",
    "meta",
    "props",
    "propConfig",
    "events",
    "children",
    "position",
    "custom",
    "scripts",
]

KNOWN_PROPS = [
    "text",
    "style",
    "classes",
    "color",
    "backgroundColor",
    "value",
    "data",
    "enabled",
    "visible",
    "direction",
    "justify",
    "alignItems",
    "wrap",
    "gap",
    "icon",
    "path",
    "source",
    "params",
    "items",
    "options",
    "format",
    "tagPath",
    "viewPath",
    "viewParams",
    "tooltip",
    "badge",
    "placeholder",
    "readOnly",
    "min",
    "max",
    "step",
    "rows",
    "selectionMode",
    "columns",
]

EVENT_CATEGORIES = ["component", "dom"]

COMPONENT_EVENTS = [
    "onActionPerformed",
    "onStartup",
    "onShutdown",
    "onChange",
    "onClick",
    "onDoubleClick",
    "onMouseEnter",
    "onMouseLeave",
    "onFocus",
    "onBlur",
    "onKeyDown",
    "onKeyUp",
]

# Context types returned by _detect_json_context
CONTEXT_TYPE_VALUE = "type_value"
CONTEXT_COMPONENT_KEY = "component_key"
CONTEXT_PROPS_KEY = "props_key"
CONTEXT_EVENTS_KEY = "events_key"
CONTEXT_EVENT_HANDLERS = "event_handlers"


def is_perspective_json(document: TextDocument) -> bool:
    """Check if a document is a Perspective view.json file."""
    if not document.uri.endswith(".json"):
        return False

    try:
        data = json.loads(document.source)
    except (json.JSONDecodeError, TypeError):
        return False

    root = data.get("root")
    if isinstance(root, dict):
        root_type = root.get("type", "")
        if isinstance(root_type, str) and root_type.startswith("ia."):
            return True

    return False


def _find_enclosing_key(lines: List[str], line_idx: int, char_idx: int) -> Optional[str]:
    """Scan backward from cursor to find the nearest enclosing JSON object key.

    Counts unmatched braces to determine the parent key.
    Returns the key name or None.
    """
    import re

    depth = 0
    # Start from the current line (up to cursor position), then go backward
    for i in range(line_idx, -1, -1):
        if i == line_idx:
            text = lines[i][:char_idx]
        else:
            text = lines[i]

        # Scan right-to-left character by character, tracking position
        for j in range(len(text) - 1, -1, -1):
            ch = text[j]
            if ch == "}":
                depth += 1
            elif ch == "{":
                if depth > 0:
                    depth -= 1
                else:
                    # Found an unmatched opening brace at position j on line i
                    # Look for "key": pattern before this brace
                    before_brace = text[:j]
                    match = re.search(r'"(\w+)"\s*:\s*$', before_brace)
                    if match:
                        return match.group(1)

                    # Check previous lines if brace was at start of line
                    for k in range(i - 1, max(i - 3, -1), -1):
                        if k < 0:
                            break
                        prev_line = lines[k].rstrip()
                        match = re.search(r'"(\w+)"\s*:\s*$', prev_line)
                        if match:
                            return match.group(1)

                    return None

    return None


def _detect_json_context(
    document: TextDocument, position,
) -> Optional[Tuple[str, str]]:
    """Detect the JSON context at the cursor position.

    Returns (context_type, partial_text) or None.
    """
    lines = document.source.splitlines()
    if position.line >= len(lines):
        return None

    line = lines[position.line]
    text_before = line[:position.character]

    # Context: inside "type": "|"
    # Pattern: "type"\s*:\s*"partial
    import re
    type_match = re.search(r'"type"\s*:\s*"([^"]*?)$', text_before)
    if type_match:
        return (CONTEXT_TYPE_VALUE, type_match.group(1))

    # Check if we're at a key position (after opening quote for a key)
    # Pattern: leading whitespace then " at cursor
    key_match = re.search(r'^\s*"([^"]*?)$', text_before)
    if key_match:
        partial = key_match.group(1)
        enclosing = _find_enclosing_key(lines, position.line, position.character)

        if enclosing == "props":
            return (CONTEXT_PROPS_KEY, partial)
        elif enclosing == "events" or enclosing in EVENT_CATEGORIES:
            if enclosing in EVENT_CATEGORIES:
                return (CONTEXT_EVENT_HANDLERS, partial)
            return (CONTEXT_EVENTS_KEY, partial)
        else:
            # Could be a component-level key if inside a component object
            return (CONTEXT_COMPONENT_KEY, partial)

    return None


def get_json_completions(
    document: TextDocument, position,
) -> Optional[CompletionList]:
    """Generate JSON completions for a Perspective view.

    Returns CompletionList if context detected, None to fall through.
    """
    ctx = _detect_json_context(document, position)
    if ctx is None:
        return None

    context_type, partial = ctx
    items: List[CompletionItem] = []

    if context_type == CONTEXT_TYPE_VALUE:
        for comp_type in COMPONENT_TYPES:
            if not partial or comp_type.startswith(partial) or partial in comp_type:
                items.append(
                    CompletionItem(
                        label=comp_type,
                        kind=CompletionItemKind.EnumMember,
                        detail="Perspective component type",
                    )
                )

    elif context_type == CONTEXT_COMPONENT_KEY:
        for key in COMPONENT_KEYS:
            if not partial or key.startswith(partial):
                items.append(
                    CompletionItem(
                        label=key,
                        kind=CompletionItemKind.Property,
                        detail="Component structure key",
                    )
                )

    elif context_type == CONTEXT_PROPS_KEY:
        for prop in KNOWN_PROPS:
            if not partial or prop.startswith(partial):
                items.append(
                    CompletionItem(
                        label=prop,
                        kind=CompletionItemKind.Property,
                        detail="Component property",
                    )
                )

    elif context_type == CONTEXT_EVENTS_KEY:
        for cat in EVENT_CATEGORIES:
            if not partial or cat.startswith(partial):
                items.append(
                    CompletionItem(
                        label=cat,
                        kind=CompletionItemKind.Folder,
                        detail="Event category",
                    )
                )

    elif context_type == CONTEXT_EVENT_HANDLERS:
        for handler in COMPONENT_EVENTS:
            if not partial or handler.startswith(partial):
                items.append(
                    CompletionItem(
                        label=handler,
                        kind=CompletionItemKind.Event,
                        detail="Event handler",
                    )
                )

    if not items:
        return None

    return CompletionList(is_incomplete=False, items=items)
