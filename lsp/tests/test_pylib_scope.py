"""Tests for Python stdlib scope tracking and import detection."""

import pytest
from lsprotocol.types import Position

from ignition_lsp.pylib_loader import PylibLoader
from ignition_lsp.pylib_scope import (
    PylibContext,
    PylibContextType,
    detect_pylib_context,
    scan_pylib_imports,
)
from tests.conftest import MockTextDocument


@pytest.fixture
def pylib_loader():
    """Create a real PylibLoader from the pylib_db directory."""
    return PylibLoader()


class TestScanPylibImports:
    """Test import statement scanning for Python stdlib modules."""

    def test_import_module(self, pylib_loader):
        """Detect 'import json'."""
        doc = MockTextDocument("file:///test.py", "import json\n")
        result = scan_pylib_imports(doc, pylib_loader)
        assert "json" in result
        assert result["json"].module.name == "json"
        assert result["json"].member_name is None

    def test_import_module_with_alias(self, pylib_loader):
        """Detect 'import json as j'."""
        doc = MockTextDocument("file:///test.py", "import json as j\n")
        result = scan_pylib_imports(doc, pylib_loader)
        assert "j" in result
        assert result["j"].module.name == "json"
        assert "json" not in result

    def test_from_import_function(self, pylib_loader):
        """Detect 'from json import loads'."""
        doc = MockTextDocument("file:///test.py", "from json import loads\n")
        result = scan_pylib_imports(doc, pylib_loader)
        assert "loads" in result
        assert result["loads"].module.name == "json"
        assert result["loads"].member_name == "loads"

    def test_from_import_multiple(self, pylib_loader):
        """Detect 'from json import loads, dumps'."""
        doc = MockTextDocument(
            "file:///test.py",
            "from json import loads, dumps\n",
        )
        result = scan_pylib_imports(doc, pylib_loader)
        assert "loads" in result
        assert "dumps" in result

    def test_from_import_with_alias(self, pylib_loader):
        """Detect 'from json import loads as jloads'."""
        doc = MockTextDocument(
            "file:///test.py",
            "from json import loads as jloads\n",
        )
        result = scan_pylib_imports(doc, pylib_loader)
        assert "jloads" in result
        assert result["jloads"].member_name == "loads"
        assert "loads" not in result

    def test_from_import_class(self, pylib_loader):
        """Detect 'from collections import OrderedDict'."""
        doc = MockTextDocument(
            "file:///test.py",
            "from collections import OrderedDict\n",
        )
        result = scan_pylib_imports(doc, pylib_loader)
        assert "OrderedDict" in result
        assert result["OrderedDict"].member_name == "OrderedDict"

    def test_no_pylib_imports(self, pylib_loader):
        """Script with no stdlib imports returns empty dict."""
        doc = MockTextDocument(
            "file:///test.py",
            "import system\nlogger = system.util.getLogger('test')\n",
        )
        result = scan_pylib_imports(doc, pylib_loader)
        assert result == {}

    def test_unknown_module_ignored(self, pylib_loader):
        """Unknown modules are silently skipped."""
        doc = MockTextDocument(
            "file:///test.py",
            "import json\nimport nonexistent_module\n",
        )
        result = scan_pylib_imports(doc, pylib_loader)
        assert "json" in result
        assert "nonexistent_module" not in result

    def test_multiple_import_lines(self, pylib_loader):
        """Multiple import lines are all scanned."""
        doc = MockTextDocument(
            "file:///test.py",
            "import json\nimport re\nimport math\n",
        )
        result = scan_pylib_imports(doc, pylib_loader)
        assert "json" in result
        assert "re" in result
        assert "math" in result

    def test_comments_skipped(self, pylib_loader):
        """Commented out imports are skipped."""
        doc = MockTextDocument(
            "file:///test.py",
            "# import json\nimport re\n",
        )
        result = scan_pylib_imports(doc, pylib_loader)
        assert "json" not in result
        assert "re" in result

    def test_import_os_path(self, pylib_loader):
        """Detect 'import os.path'."""
        doc = MockTextDocument("file:///test.py", "import os.path\n")
        result = scan_pylib_imports(doc, pylib_loader)
        assert "os.path" in result
        assert result["os.path"].module.name == "os.path"


class TestDetectPylibContext:
    """Test completion context detection for Python stdlib."""

    def test_import_module_context(self, pylib_loader):
        """'import j' should detect IMPORT_MODULE with partial 'j'."""
        doc = MockTextDocument("file:///test.py", "import j\n")
        pos = Position(line=0, character=8)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.IMPORT_MODULE
        assert ctx.partial == "j"

    def test_import_empty_context(self, pylib_loader):
        """'import ' should detect IMPORT_MODULE with empty partial."""
        doc = MockTextDocument("file:///test.py", "import \n")
        pos = Position(line=0, character=7)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.IMPORT_MODULE
        assert ctx.partial == ""

    def test_from_module_import_context(self, pylib_loader):
        """'from json import ' should detect FROM_MODULE."""
        doc = MockTextDocument("file:///test.py", "from json import \n")
        pos = Position(line=0, character=17)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.FROM_MODULE
        assert ctx.module.name == "json"

    def test_from_module_import_partial(self, pylib_loader):
        """'from json import lo' should detect FROM_MODULE with partial 'lo'."""
        doc = MockTextDocument("file:///test.py", "from json import lo\n")
        pos = Position(line=0, character=19)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.FROM_MODULE
        assert ctx.partial == "lo"

    def test_from_unknown_module(self, pylib_loader):
        """'from unknown_module import ' should return None."""
        doc = MockTextDocument("file:///test.py", "from unknown_module import \n")
        pos = Position(line=0, character=27)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is None

    def test_from_partial_module(self, pylib_loader):
        """'from j' should detect IMPORT_MODULE with partial 'j'."""
        doc = MockTextDocument("file:///test.py", "from j\n")
        pos = Position(line=0, character=6)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.IMPORT_MODULE
        assert ctx.partial == "j"

    def test_module_member_context(self, pylib_loader):
        """'json.' after importing json should detect MODULE_MEMBER."""
        source = "import json\njson.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=5)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.MODULE_MEMBER
        assert ctx.module.name == "json"

    def test_module_member_partial(self, pylib_loader):
        """'json.lo' should detect MODULE_MEMBER with partial 'lo'."""
        source = "import json\njson.lo\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=7)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.MODULE_MEMBER
        assert ctx.partial == "lo"

    def test_class_member_context(self, pylib_loader):
        """'json.JSONEncoder.' should detect CLASS_MEMBER."""
        source = "import json\njson.JSONEncoder.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=17)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.CLASS_MEMBER
        assert ctx.py_class.name == "JSONEncoder"

    def test_from_import_class_member(self, pylib_loader):
        """'OrderedDict.' after 'from collections import OrderedDict' should detect CLASS_MEMBER."""
        source = "from collections import OrderedDict\nOrderedDict.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=12)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.CLASS_MEMBER
        assert ctx.py_class.name == "OrderedDict"

    def test_no_context_plain_code(self, pylib_loader):
        """Regular code should return None."""
        doc = MockTextDocument("file:///test.py", "x = 42\n")
        pos = Position(line=0, character=6)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is None

    def test_no_context_system_api(self, pylib_loader):
        """system.tag. should not trigger pylib context."""
        doc = MockTextDocument("file:///test.py", "system.tag.\n")
        pos = Position(line=0, character=11)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is None

    def test_no_context_without_import(self, pylib_loader):
        """'json.' without an import should return None."""
        doc = MockTextDocument("file:///test.py", "json.\n")
        pos = Position(line=0, character=5)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is None

    def test_aliased_module_member(self, pylib_loader):
        """'j.' after 'import json as j' should detect MODULE_MEMBER."""
        source = "import json as j\nj.\n"
        doc = MockTextDocument("file:///test.py", source)
        pos = Position(line=1, character=2)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.MODULE_MEMBER
        assert ctx.module.name == "json"

    def test_from_import_after_comma(self, pylib_loader):
        """'from json import loads, ' should detect FROM_MODULE."""
        doc = MockTextDocument("file:///test.py", "from json import loads, \n")
        pos = Position(line=0, character=24)
        ctx = detect_pylib_context(doc, pos, pylib_loader)
        assert ctx is not None
        assert ctx.type == PylibContextType.FROM_MODULE
        assert ctx.partial == ""
