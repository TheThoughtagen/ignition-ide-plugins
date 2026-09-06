"""Render a Perspective view.json as a static HTML wireframe.

Perspective's real components are proprietary React code that lives on the
Gateway, so nothing built from view.json alone can be a faithful render. What
this module produces is a *layout wireframe*: containers laid out with the
same CSS model Perspective uses (absolute positioning for coordinate
containers, flexbox for flex containers), leaf components drawn as labelled
boxes carrying their most telling props, and bound props shown as placeholders
rather than resolved values. It answers "what is the shape of this view" without
a Gateway; for the real thing, open the view in the Gateway instead.

This module is pure logic: no I/O, so every rule here is directly testable.
"""

import hashlib
import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Directory (relative to the project root) holding generated previews.
PREVIEW_DIR_NAME = ".ignition-preview"

# Perspective's default view size when defaultSize is absent.
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600

# Seconds between browser auto-refreshes. The server regenerates the file on
# every change to a previewed view, so this is what makes the preview live.
REFRESH_SECONDS = 2

# Props worth surfacing on a leaf, in priority order. The first present wins
# as the box's headline; the rest are listed underneath.
_HEADLINE_PROPS = ("text", "title", "label", "placeholder", "tagPath", "source", "value")
_MAX_LISTED_PROPS = 5

# Container types with layout semantics this renderer understands. Anything
# else under ia.container.* is stacked vertically as an honest approximation.
_COORD = "ia.container.coord"
_FLEX = "ia.container.flex"

_CAMEL_RE = re.compile(r"(?<!^)(?=[A-Z])")


class NotAPerspectiveView(ValueError):
    """Raised when JSON does not have the shape of a Perspective view."""


@dataclass
class Binding:
    """A binding on a component prop, summarised for display."""

    prop: str  # e.g. "props.text"
    kind: str  # "tag", "expr", "property", "query", ...
    detail: str  # tag path, expression text, or "" when there is nothing terse


@dataclass
class Node:
    """One component in the view tree, with only what the renderer needs."""

    type: str
    name: str
    props: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, Any] = field(default_factory=dict)
    bindings: List[Binding] = field(default_factory=list)
    has_scripts: bool = False
    children: List["Node"] = field(default_factory=list)

    @property
    def short_type(self) -> str:
        """`ia.display.label` -> `label`."""
        return self.type.rsplit(".", 1)[-1] if self.type else "?"

    @property
    def is_container(self) -> bool:
        return self.type.startswith("ia.container.")


@dataclass
class ViewModel:
    """A parsed view: its root node and default size."""

    root: Node
    width: int
    height: int


# ── Parsing ───────────────────────────────────────────────────────────


def is_perspective_view(data: Any) -> bool:
    """Whether parsed JSON looks like a Perspective view."""
    if not isinstance(data, dict):
        return False
    root = data.get("root")
    return isinstance(root, dict) and str(root.get("type", "")).startswith("ia.")


def parse_view(text: str) -> ViewModel:
    """Parse view.json text into a ViewModel.

    Raises NotAPerspectiveView for anything that is not a view, including
    invalid JSON, so callers have one thing to catch.
    """
    try:
        data = json.loads(text)
    except ValueError as e:
        raise NotAPerspectiveView(f"Not valid JSON: {e}") from e

    if not is_perspective_view(data):
        raise NotAPerspectiveView("JSON has no root component of type ia.*")

    size = (data.get("props") or {}).get("defaultSize") or {}
    width = _as_int(size.get("width"), DEFAULT_WIDTH)
    height = _as_int(size.get("height"), DEFAULT_HEIGHT)

    return ViewModel(root=_parse_node(data["root"]), width=width, height=height)


def _parse_node(component: Dict[str, Any]) -> Node:
    meta = component.get("meta") or {}
    props = component.get("props") or {}
    position = component.get("position") or {}

    bindings = _parse_bindings(component.get("propConfig") or {})
    has_scripts = bool(component.get("events")) or any("script" in str(k).lower() for k in props)

    children = []
    for child in component.get("children") or []:
        if isinstance(child, dict):
            children.append(_parse_node(child))

    return Node(
        type=str(component.get("type", "")),
        name=str(meta.get("name", "(unnamed)")),
        props=props if isinstance(props, dict) else {},
        position=position if isinstance(position, dict) else {},
        bindings=bindings,
        has_scripts=has_scripts,
        children=children,
    )


def _parse_bindings(prop_config: Dict[str, Any]) -> List[Binding]:
    """Summarise propConfig bindings.

    propConfig maps a dotted prop path ("props.text") to a config object that
    may carry a `binding` with a `type` and a `config`. Only the type and the
    most identifying piece of config are kept; the renderer shows these as
    placeholders, it never evaluates them.
    """
    bindings: List[Binding] = []
    for prop, cfg in prop_config.items():
        if not isinstance(cfg, dict):
            continue
        binding = cfg.get("binding")
        if not isinstance(binding, dict):
            continue
        kind = str(binding.get("type", "?"))
        config = binding.get("config") or {}
        detail = ""
        if isinstance(config, dict):
            for key in ("tagPath", "expression", "path", "queryPath", "path"):
                value = config.get(key)
                if isinstance(value, str) and value:
                    detail = value
                    break
        bindings.append(Binding(prop=str(prop), kind=kind, detail=detail))
    return bindings


# ── Rendering ─────────────────────────────────────────────────────────


def render_view_html(view: ViewModel, title: str, source_label: str = "") -> str:
    """Render a ViewModel as a complete, self-contained HTML document."""
    body = _render_node(view.root, parent=None, depth=0)
    return _DOCUMENT.format(
        title=html.escape(title),
        refresh=REFRESH_SECONDS,
        width=view.width,
        height=view.height,
        source=html.escape(source_label),
        body=body,
        css=_CSS,
    )


def _render_node(node: Node, parent: Optional[Node], depth: int) -> str:
    style = _layout_style(node, parent) + _user_style(node)
    classes = ["c", "container" if node.is_container else "leaf"]
    if node.has_scripts:
        classes.append("scripted")

    header = _render_header(node)
    inner = (
        "".join(_render_node(child, node, depth + 1) for child in node.children)
        if node.is_container
        else _render_leaf_body(node)
    )

    # Container children get a positioning context and, for flex, the flex
    # rules of their parent. Leaves have no children to lay out.
    children_style = _children_style(node) if node.is_container else ""
    return (
        f'<div class="{" ".join(classes)}" style="{style}" title="{html.escape(node.type)}">'
        f"{header}"
        f'<div class="children" style="{children_style}">{inner}</div>'
        f"</div>"
    )


def _render_header(node: Node) -> str:
    badges = ""
    if node.has_scripts:
        badges += '<span class="badge script" title="has event scripts">script</span>'
    if node.bindings:
        badges += (
            f'<span class="badge bound" title="{len(node.bindings)} bound prop(s)">'
            f"{len(node.bindings)} bound</span>"
        )
    return (
        f'<div class="hdr"><span class="type">{html.escape(node.short_type)}</span>'
        f'<span class="name">{html.escape(node.name)}</span>{badges}</div>'
    )


def _render_leaf_body(node: Node) -> str:
    bound_props = {b.prop.split(".", 1)[-1]: b for b in node.bindings}
    lines: List[str] = []

    headline = None
    for key in _HEADLINE_PROPS:
        if key in bound_props:
            headline = _binding_placeholder(bound_props[key])
            break
        value = node.props.get(key)
        if isinstance(value, (str, int, float)) and str(value) != "":
            headline = f'<span class="headline">{html.escape(str(value))}</span>'
            break
    if headline:
        lines.append(headline)

    listed = 0
    for key, value in node.props.items():
        if key in _HEADLINE_PROPS or key == "style":
            continue
        if listed >= _MAX_LISTED_PROPS:
            lines.append('<span class="prop more">…</span>')
            break
        if key in bound_props:
            lines.append(
                f'<span class="prop">{html.escape(key)}: '
                f"{_binding_placeholder(bound_props[key])}</span>"
            )
            listed += 1
        elif isinstance(value, (str, int, float, bool)):
            shown = html.escape(str(value))
            if len(shown) > 40:
                shown = shown[:37] + "…"
            lines.append(f'<span class="prop">{html.escape(key)}: {shown}</span>')
            listed += 1

    # Bindings on props that were not otherwise listed still deserve a mention.
    for prop, binding in bound_props.items():
        if prop in _HEADLINE_PROPS or prop in node.props:
            continue
        lines.append(
            f'<span class="prop">{html.escape(prop)}: ' f"{_binding_placeholder(binding)}</span>"
        )

    return "".join(lines)


def _binding_placeholder(binding: Binding) -> str:
    detail = f" {html.escape(binding.detail)}" if binding.detail else ""
    return f'<span class="binding" title="bound">⟨{html.escape(binding.kind)}{detail}⟩</span>'


# ── Layout ────────────────────────────────────────────────────────────


def _layout_style(node: Node, parent: Optional[Node]) -> str:
    """CSS placing `node` inside `parent`, per the parent's container type.

    Position semantics belong to the parent: a coordinate container places
    children by x/y/width/height, a flex container by grow/shrink/basis.
    """
    if parent is None:
        return "position:relative;width:100%;height:100%;"

    style = _placement_style(node, parent)
    # `position.display: false` hides a component in any container type.
    if node.position.get("display") is False:
        style += "display:none;"
    return style


def _placement_style(node: Node, parent: Node) -> str:
    pos = node.position
    if parent.type == _COORD:
        percent = parent.props.get("mode") == "percent"
        unit = "%" if percent else "px"
        scale = 100 if percent else 1
        left = _as_float(pos.get("x"), 0) * scale
        top = _as_float(pos.get("y"), 0) * scale
        width = _as_float(pos.get("width"), 100 if not percent else 0.25) * scale
        height = _as_float(pos.get("height"), 40 if not percent else 0.1) * scale
        return (
            f"position:absolute;left:{_num(left)}{unit};top:{_num(top)}{unit};"
            f"width:{_num(width)}{unit};height:{_num(height)}{unit};"
        )

    if parent.type == _FLEX:
        grow = _as_float(pos.get("grow"), 0)
        shrink = _as_float(pos.get("shrink"), 1)
        basis = pos.get("basis", "auto")
        basis_css = _css_length(basis)
        return f"flex:{_num(grow)} {_num(shrink)} {basis_css};"

    # Column, breakpoint, tab, split and unknown containers: stack.
    return "position:relative;width:100%;"


def _children_style(node: Node) -> str:
    """CSS for a container's children wrapper, per the container's own type."""
    if node.type == _COORD:
        return "position:relative;width:100%;height:100%;"

    if node.type == _FLEX:
        direction = node.props.get("direction", "column")
        if direction not in ("row", "column", "row-reverse", "column-reverse"):
            direction = "column"
        justify = _css_word(node.props.get("justify"), "flex-start")
        align = _css_word(node.props.get("alignItems"), "stretch")
        wrap = "wrap" if node.props.get("wrap") == "wrap" else "nowrap"
        return (
            f"display:flex;flex-direction:{direction};justify-content:{justify};"
            f"align-items:{align};flex-wrap:{wrap};width:100%;height:100%;"
        )

    return "display:flex;flex-direction:column;width:100%;"


def _user_style(node: Node) -> str:
    """Pass `props.style` through as inline CSS.

    Keys are camelCase in Perspective and kebab-case in CSS. Values are
    escaped; anything that is not a scalar is dropped rather than guessed at.
    """
    style = node.props.get("style")
    if not isinstance(style, dict):
        return ""
    out = []
    for key, value in style.items():
        if not isinstance(key, str) or not isinstance(value, (str, int, float)):
            continue
        if key == "classes":
            continue  # Gateway theme classes; meaningless without the theme.
        css_key = _CAMEL_RE.sub("-", key).lower()
        if not re.fullmatch(r"[a-z-]+", css_key):
            continue
        css_val = html.escape(str(value), quote=True).replace(";", "")
        out.append(f"{css_key}:{css_val};")
    return "".join(out)


# ── Small helpers ─────────────────────────────────────────────────────


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _num(value: float) -> str:
    """Format a number for CSS without a trailing .0."""
    return str(int(value)) if float(value).is_integer() else f"{value:.4g}"


def _css_length(value: Any) -> str:
    """A flex-basis: numbers are pixels, strings pass through if they look safe."""
    if isinstance(value, (int, float)):
        return f"{_num(float(value))}px"
    if isinstance(value, str) and re.fullmatch(r"[0-9.]+(px|%|em|rem|vh|vw)?|auto", value):
        return value if not re.fullmatch(r"[0-9.]+", value) else f"{value}px"
    return "auto"


def _css_word(value: Any, default: str) -> str:
    return value if isinstance(value, str) and re.fullmatch(r"[a-z-]+", value) else default


# ── Output location ───────────────────────────────────────────────────


def preview_path(project_root: str, source_path: str) -> Path:
    """Where the preview for a view file lives, under the project's preview dir.

    Flattened like sidecar scripts, with a short path digest so two views
    whose paths flatten identically cannot share a preview file.
    """
    root = Path(project_root)
    try:
        relative = str(Path(source_path).relative_to(root))
    except ValueError:
        relative = Path(source_path).name
    normalized = relative.replace("\\", "/").strip("/")
    stem = normalized[: -len(".json")] if normalized.endswith(".json") else normalized
    flat = stem.replace("/", "__")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return root / PREVIEW_DIR_NAME / f"{flat}__{digest}.html"


# ── Document template ─────────────────────────────────────────────────

_CSS = """
:root { color-scheme: light dark; }
body { margin: 0; font: 12px/1.35 system-ui, sans-serif; background: #e9e9ec; color: #1c1c1e; }
@media (prefers-color-scheme: dark) { body { background: #1c1c1e; color: #e5e5ea; } }
.bar { padding: 8px 14px; font-size: 12px; opacity: .8; display: flex; gap: 14px; flex-wrap: wrap; }
.bar b { opacity: 1; }
.stage { margin: 0 14px 14px; overflow: auto; }
.view { position: relative; background: #fff; border: 1px solid #b8b8bd;
        box-shadow: 0 1px 4px rgba(0,0,0,.15); overflow: hidden; }
@media (prefers-color-scheme: dark) { .view { background: #2c2c2e; border-color: #48484a; } }
.c { box-sizing: border-box; border: 1px solid rgba(60,60,67,.35); min-height: 22px;
     overflow: hidden; display: flex; flex-direction: column; }
.container { border-style: dashed; background: rgba(120,120,128,.06); }
.leaf { background: rgba(10,132,255,.07); }
.scripted { border-left: 3px solid #ff9f0a; }
.hdr { display: flex; gap: 6px; align-items: baseline; padding: 1px 5px; font-size: 10px;
       opacity: .7; white-space: nowrap; overflow: hidden; }
.hdr .type { font-weight: 600; }
.badge { font-size: 9px; padding: 0 4px; border-radius: 3px; background: rgba(120,120,128,.25); }
.badge.script { background: rgba(255,159,10,.35); }
.badge.bound { background: rgba(10,132,255,.25); }
.children { flex: 1 1 auto; min-height: 0; }
.leaf .children { padding: 2px 6px 4px; display: flex; flex-direction: column; gap: 1px; }
.headline, .prop { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.headline { font-size: 13px; font-weight: 500; }
.prop { font-size: 10px; opacity: .75; font-family: ui-monospace, monospace; }
.binding { color: #0a84ff; font-family: ui-monospace, monospace; }
.legend { display: flex; gap: 12px; }
.sw { display: inline-block; width: 12px; height: 12px; vertical-align: -2px;
      margin-right: 4px; border: 1px solid rgba(60,60,67,.35); }
"""

_DOCUMENT = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{refresh}">
<title>{title} — Ignition preview</title>
<style>{css}</style>
</head><body>
<div class="bar">
  <b>{title}</b>
  <span>{width}×{height}</span>
  <span>{source}</span>
  <span class="legend">
    <span><i class="sw"
      style="border-style:dashed;background:rgba(120,120,128,.06)"></i>container</span>
    <span><i class="sw" style="background:rgba(10,132,255,.07)"></i>component</span>
    <span><i class="sw" style="border-left:3px solid #ff9f0a"></i>has scripts</span>
    <span><span class="binding">⟨…⟩</span> bound prop</span>
  </span>
  <span>wireframe — not a Gateway render; refreshes every {refresh}s</span>
</div>
<div class="stage"><div class="view" style="width:{width}px;height:{height}px">{body}</div></div>
</body></html>
"""
