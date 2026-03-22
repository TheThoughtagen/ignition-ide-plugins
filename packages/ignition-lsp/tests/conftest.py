"""Shared fixtures for Ignition LSP tests."""

import pytest
from lsprotocol.types import Position

from ignition_lsp.api_loader import IgnitionAPILoader
from ignition_lsp.java_loader import JavaAPILoader
from ignition_lsp.script_symbols import SymbolCache


class MockTextDocument:
    """Lightweight mock of pygls TextDocument for testing."""

    def __init__(self, uri: str, source: str):
        self.uri = uri
        self.source = source
        self._lines = source.splitlines(True)
        # Ensure at least one line for empty documents
        if not self._lines:
            self._lines = [""]

    @property
    def lines(self):
        return self._lines


@pytest.fixture
def api_loader():
    """Create a real IgnitionAPILoader from the api_db directory."""
    return IgnitionAPILoader(version="8.1")


@pytest.fixture
def java_loader():
    """Create a real JavaAPILoader from the java_db directory."""
    return JavaAPILoader()


@pytest.fixture
def mock_document():
    """Factory fixture for creating mock text documents."""

    def _make(source: str, uri: str = "file:///test.py"):
        return MockTextDocument(uri, source)

    return _make


@pytest.fixture
def symbol_cache():
    """Create a fresh SymbolCache for testing."""
    return SymbolCache()


@pytest.fixture
def sample_script():
    """A typical Ignition script for testing."""
    return """import system

logger = system.util.getLogger("MyScript")

tags = system.tag.readBlocking(["[default]MyTag"])
value = tags[0].value

system.db.runPrepQuery("SELECT * FROM table WHERE id = ?", [value])

system.perspective.sendMessage("updateView", {"value": value})
"""


@pytest.fixture
def position():
    """Factory fixture for creating LSP Position objects."""

    def _make(line: int, character: int):
        return Position(line=line, character=character)

    return _make
