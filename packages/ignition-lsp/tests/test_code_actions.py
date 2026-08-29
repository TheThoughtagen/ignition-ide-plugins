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
    '{\n'
    '  "name": "TestView",\n'
    '  "events": {\n'
    '    "onActionPerformed": "def runAction(self, event):\\n\\tsystem.perspective.'
    'navigate(\\u0027/home\\u0027)\\n\\tprint(\\"done\\")\\n"\n'
    '  }\n'
    '}\n'
)

# 1-based line number of the onActionPerformed script above.
SCRIPT_LINE = 4
SCRIPT_KEY = "onActionPerformed"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal Ignition project containing one JSON resource with a script."""
    (tmp_path / "project.json").write_text('{"name": "TestProject"}', encoding="utf-8")
    views = tmp_path / "views" / "Main"
    views.mkdir(parents=True)
    (views / "view.json").write_text(RESOURCE_JSON, encoding="utf-8")
    return tmp_path


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
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(
            uri, RESOURCE_JSON
        )

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
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(
            uri, RESOURCE_JSON
        )

        assert code_action(mock_ls, _params(uri, 0)) is None

    def test_range_spanning_file_offers_every_script(self, mock_ls: MagicMock) -> None:
        uri = "file:///proj/views/Main/view.json"
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(
            uri, RESOURCE_JSON
        )

        actions = code_action(mock_ls, _params(uri, 0, 20))

        assert actions is not None
        assert len(actions) == 1

    def test_non_json_file_gets_no_actions(self, mock_ls: MagicMock) -> None:
        uri = "file:///proj/scripts/code.py"
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(
            uri, "print('hello')\n"
        )

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

    def test_writes_sidecar_with_header_and_body(
        self, mock_ls: MagicMock, project: Path
    ) -> None:
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

    def test_asks_the_client_to_open_the_sidecar(
        self, mock_ls: MagicMock, project: Path
    ) -> None:
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

    def test_edit_is_written_back_encoded(
        self, mock_ls: MagicMock, project: Path
    ) -> None:
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

    def test_missing_header_is_refused(
        self, mock_ls: MagicMock, project: Path
    ) -> None:
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
        mock_ls.workspace.get_text_document.return_value = MockTextDocument(
            uri, "print('hello')\n"
        )

        assert code_action(mock_ls, _params(uri, 0)) is None
