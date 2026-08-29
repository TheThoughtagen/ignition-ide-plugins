"""Tests for textDocument/codeAction and the decode/save workspace commands.

These drive the round trip that plain LSP clients (Zed, Helix) rely on:
JSON resource -> decoded sidecar file -> edited -> written back to JSON.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from lsprotocol.types import (
    CodeActionContext,
    CodeActionParams,
    Position,
    Range,
    TextDocumentIdentifier,
)

from ignition_lsp.encoding import decode
from ignition_lsp.script_files import SCRIPTS_DIR_NAME, parse_header, strip_header
from ignition_lsp.server import (
    DECODE_SCRIPT_COMMAND,
    SAVE_SCRIPT_COMMAND,
    code_action,
    decode_script_to_file_command,
    save_script_to_source_command,
)
from tests.conftest import MockTextDocument

RESOURCE_JSON = (
    "{\n"
    '  "name": "TestView",\n'
    '  "events": {\n'
    '    "onActionPerformed": "def runAction(self, event):\\n\\tsystem.perspective.'
    'navigate(\\u0027/home\\u0027)\\n\\tprint(\\"done\\")\\n"\n'
    "  }\n"
    "}\n"
)

# 1-based line number of the onActionPerformed script above.
SCRIPT_LINE = 4
SCRIPT_KEY = "onActionPerformed"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal Ignition project containing one JSON resource with a script.

    Nested under tmp_path rather than being tmp_path itself, so tests can also
    place files genuinely outside the project.
    """
    root = tmp_path / "project"
    root.mkdir()
    (root / "project.json").write_text('{"name": "TestProject"}', encoding="utf-8")
    views = root / "views" / "Main"
    views.mkdir(parents=True)
    (views / "view.json").write_text(RESOURCE_JSON, encoding="utf-8")
    return root


@pytest.fixture
def mock_ls(project: Path) -> MagicMock:
    """Mock server whose project-root lookup resolves to the temp project."""
    ls = MagicMock()
    ls._find_project_root.return_value = str(project)
    return ls


def _params(uri: str, start_line: int, end_line: int = None) -> CodeActionParams:
    end = start_line if end_line is None else end_line
    return CodeActionParams(
        text_document=TextDocumentIdentifier(uri=uri),
        range=Range(
            start=Position(line=start_line, character=0),
            end=Position(line=end, character=0),
        ),
        context=CodeActionContext(diagnostics=[]),
    )


class TestJsonResourceCodeActions:
    """Decode actions offered on an Ignition JSON resource."""

    def test_offers_decode_on_script_line(self, mock_ls: MagicMock) -> None:
        uri = "file:///proj/views/Main/view.json"
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(uri, RESOURCE_JSON)

        actions = code_action(mock_ls, _params(uri, SCRIPT_LINE - 1))

        assert actions is not None
        assert len(actions) == 1
        assert actions[0].command.command == DECODE_SCRIPT_COMMAND
        assert actions[0].command.arguments[0] == {
            "uri": uri,
            "line": SCRIPT_LINE,
            "key": SCRIPT_KEY,
        }

    def test_no_actions_on_unrelated_line(self, mock_ls: MagicMock) -> None:
        uri = "file:///proj/views/Main/view.json"
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(uri, RESOURCE_JSON)

        assert code_action(mock_ls, _params(uri, 0)) is None

    def test_range_spanning_file_offers_every_script(self, mock_ls: MagicMock) -> None:
        uri = "file:///proj/views/Main/view.json"
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(uri, RESOURCE_JSON)

        actions = code_action(mock_ls, _params(uri, 0, 20))

        assert actions is not None
        assert len(actions) == 1

    def test_non_json_file_gets_no_actions(self, mock_ls: MagicMock) -> None:
        uri = "file:///proj/scripts/code.py"
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(uri, "print('hello')\n")

        assert code_action(mock_ls, _params(uri, 0)) is None

    def test_json_without_scripts_gets_no_actions(self, mock_ls: MagicMock) -> None:
        uri = "file:///proj/plain.json"
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(
            uri, '{"name": "nothing here"}\n'
        )

        assert code_action(mock_ls, _params(uri, 0)) is None

    def test_unreadable_document_is_handled(self, mock_ls: MagicMock) -> None:
        mock_ls.workspace.get_text_document.side_effect = KeyError("not open")

        assert code_action(mock_ls, _params("file:///gone.json", 0)) is None


class TestDecodeScriptToFileCommand:
    """Decoding an embedded script into a sidecar file."""

    def test_writes_sidecar_with_header_and_body(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )

        assert result["success"] is True
        sidecar = Path(result["path"])
        assert sidecar.parent == project / SCRIPTS_DIR_NAME
        assert sidecar.is_file()

        text = sidecar.read_text(encoding="utf-8")
        ref = parse_header(text)
        assert ref is not None
        assert ref.key == SCRIPT_KEY
        assert ref.line == SCRIPT_LINE
        assert ref.source_uri == source.as_uri()

        body = strip_header(text)
        assert "def runAction(self, event):" in body
        # Unicode escapes must come back as real characters.
        assert "'/home'" in body
        assert '"done"' in body

    def test_asks_the_client_to_open_the_sidecar(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )

        mock_ls.window_show_document.assert_called_once()

    def test_show_document_failure_does_not_fail_the_command(
        self, mock_ls: MagicMock, project: Path
    ) -> None:
        """Clients without window/showDocument still get the file."""
        mock_ls.window_show_document.side_effect = RuntimeError("unsupported")
        source = project / "views" / "Main" / "view.json"

        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )

        assert result["success"] is True

    def test_missing_file(self, mock_ls: MagicMock) -> None:
        result = decode_script_to_file_command(
            mock_ls, {"uri": "file:///nope/view.json", "line": 1, "key": "script"}
        )
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_wrong_line(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls, {"uri": source.as_uri(), "line": 1, "key": SCRIPT_KEY}
        )
        assert result["success"] is False


class TestSaveScriptToSourceCommand:
    """Writing a sidecar script back into its source JSON."""

    def _decode(self, mock_ls: MagicMock, project: Path) -> Path:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        assert result["success"] is True
        return Path(result["path"])

    def test_untouched_round_trip_is_byte_identical(
        self, mock_ls: MagicMock, project: Path
    ) -> None:
        """decode -> save with no edits must not change the source file at all."""
        source = project / "views" / "Main" / "view.json"
        original = source.read_text(encoding="utf-8")

        sidecar = self._decode(mock_ls, project)
        result = save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        assert result["success"] is True
        assert source.read_text(encoding="utf-8") == original

    def test_edit_is_written_back_encoded(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        sidecar = self._decode(mock_ls, project)

        text = sidecar.read_text(encoding="utf-8")
        edited = text.replace('print("done")', 'print("changed & done")')
        assert edited != text
        sidecar.write_text(edited, encoding="utf-8")

        result = save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})
        assert result["success"] is True

        updated = source.read_text(encoding="utf-8")
        # Stored encoded, not raw: '&' becomes & and the JSON stays one line.
        assert "\\u0026" in updated
        assert len(updated.splitlines()) == len(RESOURCE_JSON.splitlines())

        # And it decodes back to exactly what was typed.
        line = updated.splitlines()[SCRIPT_LINE - 1]
        encoded = line.split('"onActionPerformed": "', 1)[1].rsplit('"', 1)[0]
        assert 'print("changed & done")' in decode(encoded)

    def test_indentation_is_restored(self, mock_ls: MagicMock, project: Path) -> None:
        """The tab indent stripped on decode must be re-added on save."""
        source = project / "views" / "Main" / "view.json"
        sidecar = self._decode(mock_ls, project)
        save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        line = source.read_text(encoding="utf-8").splitlines()[SCRIPT_LINE - 1]
        encoded = line.split('"onActionPerformed": "', 1)[1].rsplit('"', 1)[0]
        assert "\tsystem.perspective.navigate" in decode(encoded)

    def test_missing_header_is_refused(self, mock_ls: MagicMock, project: Path) -> None:
        stray = project / SCRIPTS_DIR_NAME / "stray.py"
        stray.parent.mkdir(parents=True, exist_ok=True)
        stray.write_text("print('no header here')\n", encoding="utf-8")

        result = save_script_to_source_command(mock_ls, {"uri": stray.as_uri()})

        assert result["success"] is False
        assert "header" in result["error"].lower()

    def test_missing_file_is_refused(self, mock_ls: MagicMock) -> None:
        result = save_script_to_source_command(mock_ls, {"uri": "file:///nope.py"})
        assert result["success"] is False


class TestSidecarCodeActions:
    """The save-back action offered on a decoded sidecar file."""

    def test_offers_save_action(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        sidecar = Path(result["path"])
        uri = sidecar.as_uri()
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(
            uri, sidecar.read_text(encoding="utf-8")
        )

        actions = code_action(mock_ls, _params(uri, 0))

        assert actions is not None
        assert len(actions) == 1
        assert actions[0].command.command == SAVE_SCRIPT_COMMAND
        assert actions[0].command.arguments[0] == {"uri": uri}
        assert SCRIPT_KEY in actions[0].title

    def test_sidecar_without_header_gets_no_action(self, mock_ls: MagicMock) -> None:
        uri = f"file:///proj/{SCRIPTS_DIR_NAME}/stray.py"
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(uri, "print('hello')\n")

        assert code_action(mock_ls, _params(uri, 0)) is None


class TestSidecarValidation:
    """Guards that run before a sidecar is written back to its source."""

    def _decode(self, mock_ls: MagicMock, project: Path) -> Path:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        assert result["success"] is True
        return Path(result["path"])

    def test_stale_sidecar_is_refused(self, mock_ls: MagicMock, project: Path) -> None:
        """If the source script changed after decode, the save must not land."""
        source = project / "views" / "Main" / "view.json"
        sidecar = self._decode(mock_ls, project)

        # Someone else edits the same script in the source file.
        source.write_text(
            RESOURCE_JSON.replace('print(\\"done\\")', 'print(\\"something else\\")'),
            encoding="utf-8",
        )
        changed = source.read_text(encoding="utf-8")

        result = save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        assert result["success"] is False
        assert "changed" in result["error"].lower()
        # And the source is left exactly as the other edit left it.
        assert source.read_text(encoding="utf-8") == changed

    def test_script_removed_from_line_is_refused(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        sidecar = self._decode(mock_ls, project)

        source.write_text('{\n  "name": "TestView",\n  "events": {\n  }\n}\n', encoding="utf-8")

        result = save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        assert result["success"] is False
        assert "no '" in result["error"] or "changed" in result["error"].lower()

    def test_source_outside_project_is_refused(
        self, mock_ls: MagicMock, project: Path, tmp_path: Path
    ) -> None:
        """A rewritten `source:` must not redirect the write out of the project."""
        outside = tmp_path / "outside.json"
        outside.write_text(RESOURCE_JSON, encoding="utf-8")
        original = outside.read_text(encoding="utf-8")

        sidecar = self._decode(mock_ls, project)
        text = sidecar.read_text(encoding="utf-8")
        sidecar.write_text(
            text.replace(
                f"# source: {(project / 'views' / 'Main' / 'view.json').as_uri()}",
                f"# source: {outside.as_uri()}",
            ),
            encoding="utf-8",
        )

        result = save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        assert result["success"] is False
        assert "outside the project" in result["error"]
        assert outside.read_text(encoding="utf-8") == original

    def test_sidecar_at_wrong_path_is_refused(self, mock_ls: MagicMock, project: Path) -> None:
        """A header that does not match the file's own location is not trusted."""
        sidecar = self._decode(mock_ls, project)
        moved = sidecar.parent / "renamed.py"
        moved.write_text(sidecar.read_text(encoding="utf-8"), encoding="utf-8")

        result = save_script_to_source_command(mock_ls, {"uri": moved.as_uri()})

        assert result["success"] is False
        assert "does not match its location" in result["error"]

    def test_sidecar_outside_scripts_dir_is_refused(
        self, mock_ls: MagicMock, project: Path
    ) -> None:
        sidecar = self._decode(mock_ls, project)
        stray = project / "stray.py"
        stray.write_text(sidecar.read_text(encoding="utf-8"), encoding="utf-8")

        result = save_script_to_source_command(mock_ls, {"uri": stray.as_uri()})

        assert result["success"] is False
        assert SCRIPTS_DIR_NAME in result["error"]


class TestUriToPath:
    """File URIs must survive the round trip on every platform."""

    def test_posix_path(self) -> None:
        from ignition_lsp.server import _uri_to_path

        assert _uri_to_path("file:///proj/views/view.json") == "/proj/views/view.json"

    def test_percent_encoding_is_decoded(self) -> None:
        from ignition_lsp.server import _uri_to_path

        assert _uri_to_path("file:///proj/My%20Views/view.json") == "/proj/My Views/view.json"

    def test_round_trips_a_real_path(self, tmp_path: Path) -> None:
        from ignition_lsp.server import _uri_to_path

        target = tmp_path / "a b" / "view.json"
        target.parent.mkdir()
        target.write_text("{}", encoding="utf-8")
        assert Path(_uri_to_path(target.as_uri())) == target

    def test_non_file_scheme_is_left_alone(self) -> None:
        """Virtual-buffer URIs are not filesystem paths."""
        from ignition_lsp.server import _uri_to_path

        assert _uri_to_path("ignition-script:///abc/key/42") == "/abc/key/42"


class TestRepeatedSaves:
    """Editing and saving the same sidecar repeatedly must keep working."""

    def test_successive_edits_all_land(self, mock_ls: MagicMock, project: Path) -> None:
        """Regression: the digest must be refreshed after each save."""
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        sidecar = Path(result["path"])

        for marker in ("first", "second", "third"):
            text = sidecar.read_text(encoding="utf-8")
            body = strip_header(text)
            new_body = body.rsplit("\n\t", 1)[0] + f'\n\tprint("{marker}")\n'
            sidecar.write_text(text.replace(body, new_body), encoding="utf-8")

            outcome = save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})
            assert outcome["success"] is True, f"{marker}: {outcome.get('error')}"

            line = source.read_text(encoding="utf-8").splitlines()[SCRIPT_LINE - 1]
            encoded = line.split('"onActionPerformed": "', 1)[1].rsplit('"', 1)[0]
            assert f'print("{marker}")' in decode(encoded)

    def test_save_refreshes_the_header_digest(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        sidecar = Path(result["path"])

        before = parse_header(sidecar.read_text(encoding="utf-8"))
        text = sidecar.read_text(encoding="utf-8")
        sidecar.write_text(text.replace('print("done")', 'print("new")'), encoding="utf-8")

        save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        after = parse_header(sidecar.read_text(encoding="utf-8"))
        assert before is not None and after is not None
        assert after.digest != before.digest
        # Everything else about the reference is unchanged.
        assert (after.source_uri, after.key, after.line, after.indent) == (
            before.source_uri,
            before.key,
            before.line,
            before.indent,
        )

    def test_body_is_preserved_across_the_refresh(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        sidecar = Path(result["path"])
        body_before = strip_header(sidecar.read_text(encoding="utf-8"))

        save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        assert strip_header(sidecar.read_text(encoding="utf-8")) == body_before


class TestAtomicWrites:
    """A partial write must never leave a project file torn."""

    def test_failed_write_leaves_source_intact(
        self, mock_ls: MagicMock, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        sidecar = Path(result["path"])
        text = sidecar.read_text(encoding="utf-8")
        sidecar.write_text(text.replace('print("done")', 'print("new")'), encoding="utf-8")
        original = source.read_text(encoding="utf-8")

        def boom(*args: object, **kwargs: object) -> None:
            raise OSError("simulated crash during rename")

        monkeypatch.setattr("ignition_lsp.server.os.replace", boom)
        outcome = save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        assert outcome["success"] is False
        # The source is untouched, not half-written.
        assert source.read_text(encoding="utf-8") == original

    def test_failed_write_leaves_no_temp_file(
        self, mock_ls: MagicMock, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        sidecar = Path(result["path"])
        text = sidecar.read_text(encoding="utf-8")
        sidecar.write_text(text.replace('print("done")', 'print("new")'), encoding="utf-8")

        def boom(*args: object, **kwargs: object) -> None:
            raise OSError("simulated crash during rename")

        monkeypatch.setattr("ignition_lsp.server.os.replace", boom)
        save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})

        leftovers = [p.name for p in source.parent.iterdir() if ".ignition-lsp.tmp" in p.name]
        assert leftovers == []

    def test_successful_write_leaves_no_temp_file(self, mock_ls: MagicMock, project: Path) -> None:
        source = project / "views" / "Main" / "view.json"
        result = decode_script_to_file_command(
            mock_ls,
            {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY},
        )
        sidecar = Path(result["path"])
        assert save_script_to_source_command(mock_ls, {"uri": sidecar.as_uri()})["success"]

        for directory in (source.parent, sidecar.parent):
            assert [p.name for p in directory.iterdir() if ".ignition-lsp.tmp" in p.name] == []


class TestPercentEncodedPaths:
    """Project roots and sources must resolve through one conversion.

    A root resolved one way and a source path another do not compare equal,
    which sends the sidecar somewhere unexpected and then refuses to save it.
    """

    @pytest.fixture
    def spaced_project(self, tmp_path: Path) -> Path:
        root = tmp_path / "My Ignition Project"
        root.mkdir()
        (root / "project.json").write_text('{"name": "Spaced"}', encoding="utf-8")
        views = root / "My Views" / "Main"
        views.mkdir(parents=True)
        (views / "view.json").write_text(RESOURCE_JSON, encoding="utf-8")
        return root

    def test_round_trip_through_a_path_with_spaces(self, spaced_project: Path) -> None:
        ls = MagicMock()
        ls._find_project_root.return_value = str(spaced_project)
        source = spaced_project / "My Views" / "Main" / "view.json"
        original = source.read_text(encoding="utf-8")

        result = decode_script_to_file_command(
            ls, {"uri": source.as_uri(), "line": SCRIPT_LINE, "key": SCRIPT_KEY}
        )
        assert result["success"] is True

        sidecar = Path(result["path"])
        # The sidecar lands inside the project, not somewhere derived from a
        # differently-decoded root.
        assert sidecar.parent == spaced_project / SCRIPTS_DIR_NAME

        assert save_script_to_source_command(ls, {"uri": sidecar.as_uri()})["success"] is True
        assert source.read_text(encoding="utf-8") == original

    def test_project_root_resolution_matches_uri_conversion(self, spaced_project: Path) -> None:
        """_find_project_root must decode URIs the same way _uri_to_path does."""
        from ignition_lsp.server import IgnitionLanguageServer, _uri_to_path

        source = spaced_project / "My Views" / "Main" / "view.json"
        server = IgnitionLanguageServer.__new__(IgnitionLanguageServer)

        root = IgnitionLanguageServer._find_project_root(server, source.as_uri())

        assert root == str(spaced_project)
        # relative_to rather than is_relative_to: the package supports 3.8.
        Path(_uri_to_path(source.as_uri())).relative_to(Path(root))
