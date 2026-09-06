"""Tests for the Perspective view -> HTML wireframe renderer."""

import json
from pathlib import Path

import pytest

from ignition_lsp.view_renderer import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    PREVIEW_DIR_NAME,
    NotAPerspectiveView,
    is_perspective_view,
    parse_view,
    preview_path,
    render_view_html,
)

FIXTURE_PROJECT = Path(__file__).parent / "fixtures" / "perspective_project"
PUMPS_VIEW = (
    FIXTURE_PROJECT
    / "com.inductiveautomation.perspective"
    / "views"
    / "Overview"
    / "Pumps"
    / "view.json"
)


@pytest.fixture
def pumps_text() -> str:
    return PUMPS_VIEW.read_text(encoding="utf-8")


def _node(view, *names):
    """Walk the tree by component names."""
    node = view.root
    for name in names:
        node = next(c for c in node.children if c.name == name)
    return node


# ── Detection ────────────────────────────────────────────────────────


class TestDetection:
    def test_recognises_a_view(self, pumps_text: str) -> None:
        assert is_perspective_view(json.loads(pumps_text))

    @pytest.mark.parametrize(
        "data",
        [
            {},
            {"root": "nope"},
            {"root": {"type": "custom.thing"}},
            {"scope": "G", "files": ["view.json"]},  # resource.json
            [],
            None,
        ],
    )
    def test_rejects_other_json(self, data) -> None:
        assert not is_perspective_view(data)

    def test_parse_rejects_non_views(self) -> None:
        with pytest.raises(NotAPerspectiveView):
            parse_view('{"root": {"type": "custom.thing"}}')

    def test_parse_rejects_invalid_json(self) -> None:
        with pytest.raises(ValueError):
            parse_view("{not json")


# ── Parsing ──────────────────────────────────────────────────────────


class TestParsing:
    def test_size_from_default_size(self, pumps_text: str) -> None:
        view = parse_view(pumps_text)
        assert (view.width, view.height) == (720, 480)

    def test_size_falls_back_when_missing(self) -> None:
        view = parse_view('{"root": {"type": "ia.container.coord", "children": []}}')
        assert (view.width, view.height) == (DEFAULT_WIDTH, DEFAULT_HEIGHT)

    def test_tree_shape(self, pumps_text: str) -> None:
        view = parse_view(pumps_text)
        assert view.root.type == "ia.container.flex"
        assert view.root.short_type == "flex"
        assert [c.name for c in view.root.children] == ["Header", "Body", "Footer"]
        body = _node(view, "Body")
        assert body.is_container
        assert [c.name for c in body.children] == [
            "StartButton",
            "Speed",
            "Status",
            "Hidden",
            "Trend",
        ]

    def test_position_is_carried_verbatim(self, pumps_text: str) -> None:
        view = parse_view(pumps_text)
        assert _node(view, "Body", "Speed").position == {
            "height": 40,
            "width": 200,
            "x": 160,
            "y": 20,
        }
        assert _node(view, "Header").position == {"basis": "56px", "grow": 0, "shrink": 0}

    def test_bindings_by_kind(self, pumps_text: str) -> None:
        view = parse_view(pumps_text)
        tag = _node(view, "Body", "Speed").bindings
        assert [(b.prop, b.kind, b.detail) for b in tag] == [
            ("props.value", "tag", "[default]Pumps/Pump1/Speed")
        ]
        expr = _node(view, "Body", "Status").bindings[0]
        assert expr.kind == "expr"
        assert "view.params.pumpId" in expr.detail
        prop = _node(view, "Body", "Trend").bindings[0]
        assert (prop.prop, prop.kind, prop.detail) == (
            "props.series[0].data",
            "property",
            "view.custom.history",
        )

    def test_script_events_are_flagged(self, pumps_text: str) -> None:
        view = parse_view(pumps_text)
        assert _node(view, "Body", "StartButton").has_scripts
        assert not _node(view, "Body", "Speed").has_scripts

    def test_unnamed_component_gets_a_placeholder_name(self) -> None:
        view = parse_view(
            '{"root": {"type": "ia.container.coord", "children": [{"type": "ia.display.label"}]}}'
        )
        assert view.root.children[0].name


# ── Rendering ────────────────────────────────────────────────────────


class TestRendering:
    @pytest.fixture
    def html(self, pumps_text: str) -> str:
        return render_view_html(parse_view(pumps_text), "Overview/Pumps", "views/Overview/Pumps")

    def test_document_is_self_contained(self, html: str) -> None:
        assert html.startswith("<!DOCTYPE html>")
        assert "<style>" in html
        assert "<script" not in html
        assert 'http-equiv="refresh"' in html
        assert "Overview/Pumps" in html

    def test_stage_uses_view_size(self, html: str) -> None:
        assert "width:720px;height:480px" in html
        assert "720×480" in html

    def test_coord_children_are_absolutely_positioned(self, html: str) -> None:
        assert "position:absolute;left:160px;top:20px;width:200px;height:40px;" in html

    def test_flex_children_carry_flex_shorthand(self, html: str) -> None:
        assert "flex:0 0 56px;" in html  # Header
        assert "flex:1 1 0px;" in html  # Body

    def test_flex_direction_follows_props(self, html: str) -> None:
        assert "flex-direction:row" in html  # Footer
        assert "justify-content:flex-end" in html

    def test_hidden_component_is_not_displayed(self, html: str) -> None:
        # `position.display: false` hides the Icon even inside a coord container.
        hidden = html.index("Hidden")
        assert "display:none" in html[hidden - 400 : hidden]

    def test_bindings_render_as_placeholders(self, html: str) -> None:
        assert "⟨tag [default]Pumps/Pump1/Speed⟩" in html
        assert "⟨property view.custom.history⟩" in html
        assert "1 bound" in html

    def test_scripted_component_is_marked(self, html: str) -> None:
        start = html.index("StartButton")
        assert "scripted" in html[start - 300 : start]

    def test_headline_uses_text_prop(self, html: str) -> None:
        assert '<span class="headline">Pump Station</span>' in html

    def test_style_passthrough_is_kebab_cased(self, html: str) -> None:
        assert "background-color:#1f3a5f" in html
        assert "border-top:1px solid #ccc" in html

    def test_user_content_is_escaped(self) -> None:
        text = json.dumps(
            {
                "root": {
                    "type": "ia.container.coord",
                    "children": [
                        {
                            "type": "ia.display.label",
                            "meta": {"name": "<img src=x onerror=alert(1)>"},
                            "props": {
                                "text": "</div><script>alert(1)</script>",
                                "style": {"color": 'red"><b>x'},
                            },
                        }
                    ],
                }
            }
        )
        html = render_view_html(parse_view(text), "<title>", "<src>")
        assert "<script>" not in html
        assert "<img" not in html
        assert "&lt;script&gt;" in html
        assert "&lt;title&gt;" in html
        assert 'red"><b>' not in html

    def test_percent_mode_coord_container(self) -> None:
        text = json.dumps(
            {
                "root": {
                    "type": "ia.container.coord",
                    "props": {"mode": "percent"},
                    "children": [
                        {
                            "type": "ia.display.label",
                            "meta": {"name": "Half"},
                            "position": {"x": 0.25, "y": 0.5, "width": 0.5, "height": 0.1},
                        }
                    ],
                }
            }
        )
        html = render_view_html(parse_view(text), "t")
        assert "left:25%;top:50%;width:50%;height:10%;" in html

    def test_unknown_container_stacks_children(self) -> None:
        text = json.dumps(
            {
                "root": {
                    "type": "ia.container.column",
                    "children": [{"type": "ia.display.label", "meta": {"name": "A"}}],
                }
            }
        )
        html = render_view_html(parse_view(text), "t")
        assert "position:relative;width:100%;" in html


# ── Preview path ─────────────────────────────────────────────────────


class TestPreviewPath:
    def test_lives_in_preview_dir_at_project_root(self, tmp_path: Path) -> None:
        source = tmp_path / "com.inductiveautomation.perspective" / "views" / "A" / "view.json"
        target = preview_path(str(tmp_path), str(source))
        assert target.parent == tmp_path / PREVIEW_DIR_NAME
        assert target.suffix == ".html"
        assert target.name.startswith("com.inductiveautomation.perspective__views__A__view__")

    def test_flattened_paths_stay_distinct(self, tmp_path: Path) -> None:
        a = preview_path(str(tmp_path), str(tmp_path / "views" / "A__B" / "view.json"))
        b = preview_path(str(tmp_path), str(tmp_path / "views__A" / "B" / "view.json"))
        assert a != b

    def test_is_stable(self, tmp_path: Path) -> None:
        source = str(tmp_path / "views" / "A" / "view.json")
        assert preview_path(str(tmp_path), source) == preview_path(str(tmp_path), source)

    def test_file_outside_root_uses_its_name(self, tmp_path: Path) -> None:
        target = preview_path(str(tmp_path / "project"), "/elsewhere/view.json")
        assert target.parent == tmp_path / "project" / PREVIEW_DIR_NAME
        assert target.name.startswith("view__")
