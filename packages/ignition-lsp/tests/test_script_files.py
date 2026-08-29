"""Tests for sidecar script file logic (script_files.py)."""

from pathlib import Path

from ignition_lsp.script_files import (
    HEADER_BEGIN,
    HEADER_END,
    SCRIPTS_DIR_NAME,
    ScriptRef,
    build_header,
    build_sidecar_content,
    parse_header,
    sidecar_filename,
    sidecar_path,
    strip_header,
)


class TestSidecarFilename:
    """Test flattening a source path into a sidecar filename."""

    def test_basic(self) -> None:
        assert (
            sidecar_filename("views/Main/view.json", "eventScript", 42)
            == "views__Main__view.json__eventScript__L42.py"
        )

    def test_bare_filename(self) -> None:
        assert sidecar_filename("view.json", "script", 1) == "view.json__script__L1.py"

    def test_windows_separators_normalised(self) -> None:
        assert (
            sidecar_filename("views\\Main\\view.json", "script", 7)
            == "views__Main__view.json__script__L7.py"
        )

    def test_leading_slash_stripped(self) -> None:
        assert sidecar_filename("/views/view.json", "script", 3).startswith("views__")

    def test_distinct_scripts_get_distinct_names(self) -> None:
        """Two scripts in one file must not collide."""
        first = sidecar_filename("view.json", "script", 10)
        second = sidecar_filename("view.json", "script", 20)
        third = sidecar_filename("view.json", "transform", 10)
        assert len({first, second, third}) == 3


class TestSidecarPath:
    """Test resolving the full sidecar path."""

    def test_under_project_root(self) -> None:
        result = sidecar_path("/proj", "/proj/views/view.json", "script", 5)
        assert result == Path("/proj") / SCRIPTS_DIR_NAME / "views__view.json__script__L5.py"

    def test_source_outside_root_falls_back_to_basename(self) -> None:
        result = sidecar_path("/proj", "/elsewhere/view.json", "script", 5)
        assert result == Path("/proj") / SCRIPTS_DIR_NAME / "view.json__script__L5.py"


class TestHeaderRoundTrip:
    """Test building and parsing the sidecar metadata header."""

    def test_round_trip(self) -> None:
        ref = ScriptRef(
            source_uri="file:///proj/views/view.json",
            key="eventScript",
            line=42,
            indent="\t\t",
        )
        parsed = parse_header(build_header(ref))
        assert parsed == ref

    def test_empty_indent_round_trips(self) -> None:
        ref = ScriptRef(source_uri="file:///a.json", key="script", line=1, indent="")
        assert parse_header(build_header(ref)) == ref

    def test_header_is_all_comments(self) -> None:
        """The header must stay valid Python so the sidecar parses."""
        ref = ScriptRef(source_uri="file:///a.json", key="script", line=1, indent="\t")
        for line in build_header(ref).split("\n"):
            assert line == "" or line.startswith("#")

    def test_uri_with_spaces_and_colons(self) -> None:
        ref = ScriptRef(
            source_uri="file:///proj/My%20Views/a:b.json", key="script", line=9, indent="\t"
        )
        assert parse_header(build_header(ref)) == ref


class TestParseHeaderRejectsBadInput:
    """A malformed header must never be guessed at — it decides what gets written."""

    def test_no_header(self) -> None:
        assert parse_header("print('hello')\n") is None

    def test_empty_text(self) -> None:
        assert parse_header("") is None

    def test_missing_terminator(self) -> None:
        text = "\n".join(
            [
                HEADER_BEGIN,
                "# source: file:///a.json",
                "# key: script",
                "# line: 1",
                "# indent: ",
                "print('x')",
            ]
        )
        assert parse_header(text) is None

    def test_missing_field(self) -> None:
        text = "\n".join(
            [HEADER_BEGIN, "# source: file:///a.json", "# key: script", HEADER_END]
        )
        assert parse_header(text) is None

    def test_non_numeric_line(self) -> None:
        text = "\n".join(
            [
                HEADER_BEGIN,
                "# source: file:///a.json",
                "# key: script",
                "# line: not-a-number",
                "# indent: ",
                HEADER_END,
            ]
        )
        assert parse_header(text) is None

    def test_script_comments_are_not_mistaken_for_a_header(self) -> None:
        text = "# source: nope\n# key: nope\n# line: 3\n# indent: \nprint('x')\n"
        assert parse_header(text) is None


class TestStripHeader:
    """Test recovering the script body from a sidecar file."""

    def test_strips_complete_header(self) -> None:
        ref = ScriptRef(source_uri="file:///a.json", key="script", line=1, indent="\t")
        body = "def handler():\n\tpass\n"
        assert strip_header(build_sidecar_content(ref, body)) == body

    def test_leaves_plain_script_untouched(self) -> None:
        body = "print('hello')\n"
        assert strip_header(body) == body

    def test_preserves_comments_in_body(self) -> None:
        ref = ScriptRef(source_uri="file:///a.json", key="script", line=1, indent="")
        body = "# a real comment\n# line: 99\nprint('x')\n"
        assert strip_header(build_sidecar_content(ref, body)) == body

    def test_empty_body(self) -> None:
        ref = ScriptRef(source_uri="file:///a.json", key="script", line=1, indent="")
        assert strip_header(build_sidecar_content(ref, "")) == ""
