"""Main LSP server implementation."""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlparse

import lsprotocol.types
from lsprotocol.types import (
    INITIALIZED,
    WORKSPACE_DID_CHANGE_CONFIGURATION,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS,
    WORKSPACE_SYMBOL,
    InitializedParams,
    DidChangeConfigurationParams,
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    DefinitionParams,
    DidOpenTextDocumentParams,
    DidChangeTextDocumentParams,
    DidSaveTextDocumentParams,
    DidCloseTextDocumentParams,
    Diagnostic,
    PublishDiagnosticsParams,
    Hover,
    HoverParams,
    Location,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    DiagnosticSeverity,
    SymbolInformation,
    WorkspaceSymbolParams,
    WorkDoneProgressBegin,
    WorkDoneProgressEnd,
    ProgressParams,
    ProgressToken,
)
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(Path(tempfile.gettempdir()) / 'ignition-lsp.log')),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class IgnitionLanguageServer(LanguageServer):
    """Language server for Ignition development."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics_enabled = True
        self.api_loader = None
        self.java_loader = None
        self.pylib_loader = None
        self.project_index = None
        self.symbol_cache = None
        self._scan_in_progress = False
        logger.info("Ignition LSP Server initialized")

    def initialize_api_loader(self, version: str = "8.1"):
        """Initialize the API loader with Ignition API definitions."""
        try:
            from ignition_lsp.api_loader import IgnitionAPILoader
            self.api_loader = IgnitionAPILoader(version=version)
            logger.info(f"API loader initialized with {len(self.api_loader.api_db)} functions")
        except Exception as e:
            logger.error(f"Failed to initialize API loader: {e}", exc_info=True)
            self.api_loader = None

    def initialize_java_loader(self):
        """Initialize the Java API loader with Java class definitions."""
        try:
            from ignition_lsp.java_loader import JavaAPILoader
            self.java_loader = JavaAPILoader()
            logger.info(f"Java loader initialized with {len(self.java_loader.classes)} classes")
        except Exception as e:
            logger.error(f"Failed to initialize Java loader: {e}", exc_info=True)
            self.java_loader = None

    def initialize_pylib_loader(self):
        """Initialize the Python stdlib loader with module definitions."""
        try:
            from ignition_lsp.pylib_loader import PylibLoader
            self.pylib_loader = PylibLoader()
            logger.info(f"Pylib loader initialized with {len(self.pylib_loader.modules)} modules")
        except Exception as e:
            logger.error(f"Failed to initialize pylib loader: {e}", exc_info=True)
            self.pylib_loader = None

    def scan_project(self, root_path: str) -> None:
        """Scan an Ignition project directory and build the script index."""
        try:
            from ignition_lsp.project_scanner import ProjectScanner
            scanner = ProjectScanner(root_path)
            if scanner.is_ignition_project():
                self.project_index = scanner.scan()
                # Clear symbol cache on full re-scan (file paths may have changed)
                if self.symbol_cache is not None:
                    self.symbol_cache.clear()
                logger.info(
                    f"Project index built: {self.project_index.script_count} scripts"
                )
                # Generate .pyi stubs for external type checkers
                if self.symbol_cache is not None:
                    try:
                        from ignition_lsp.stub_generator import generate_project_stubs
                        stubs_dir = generate_project_stubs(
                            self.project_index, self.symbol_cache
                        )
                        if stubs_dir:
                            logger.info(f"Generated stubs at {stubs_dir}")
                    except Exception as e:
                        logger.error(f"Stub generation failed: {e}", exc_info=True)
            else:
                logger.debug(f"Not an Ignition project: {root_path}")
        except Exception as e:
            logger.error(f"Failed to scan project: {e}", exc_info=True)
            self.project_index = None

    def _find_project_root(self, uri: str) -> Optional[str]:
        """Find Ignition project root by walking up from a URI or workspace root."""
        # Try from the file's directory
        try:
            file_path = unquote(urlparse(uri).path)
            current = Path(file_path).parent
            while current != current.parent:
                if (current / "project.json").is_file():
                    return str(current)
                current = current.parent
        except Exception as e:
            logger.debug(f"Could not find project root from {uri}: {e}")

        # Fallback: workspace root (important for virtual buffers)
        try:
            root_uri = getattr(self.workspace, 'root_uri', None)
            if root_uri:
                root_path = unquote(urlparse(root_uri).path)
                if (Path(root_path) / "project.json").is_file():
                    return root_path
                current = Path(root_path)
                while current != current.parent:
                    if (current / "project.json").is_file():
                        return str(current)
                    current = current.parent
        except Exception as e:
            logger.debug(f"Could not find project root from workspace: {e}")

        return None

    async def ensure_project_index_async(self, uri: str) -> None:
        """Build project index lazily in a background thread.

        Returns immediately so the LSP event loop stays responsive.
        system.* completions work without the project index; only
        project.*/shared.* completions need it.
        """
        if self.project_index is not None or self._scan_in_progress:
            return

        root_path = self._find_project_root(uri)
        if not root_path:
            return

        self._scan_in_progress = True
        logger.info(f"Starting background project scan for {root_path}")

        # Send progress notification so the user sees a spinner
        token = "ignition-project-scan"
        try:
            self.progress.create(token)
        except Exception:
            pass  # Client may not support progress tokens
        try:
            self.progress.begin(
                token,
                WorkDoneProgressBegin(
                    title="Ignition",
                    message="Indexing project scripts...",
                ),
            )
        except Exception:
            pass

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self.scan_project, root_path)
        except Exception as e:
            logger.error(f"Background project scan failed: {e}", exc_info=True)
        finally:
            self._scan_in_progress = False
            try:
                count = self.project_index.script_count if self.project_index else 0
                self.progress.end(
                    token,
                    WorkDoneProgressEnd(
                        message=f"Indexed {count} scripts",
                    ),
                )
            except Exception:
                pass


server = IgnitionLanguageServer("ignition-lsp", "v0.2.0")

# Initialize API loaders and symbol cache on server creation
server.initialize_api_loader()
server.initialize_java_loader()
server.initialize_pylib_loader()

from ignition_lsp.script_symbols import SymbolCache
server.symbol_cache = SymbolCache()


# ── Lifecycle Handlers ────────────────────────────────────────────


@server.feature(INITIALIZED)
def initialized(ls: IgnitionLanguageServer, params: InitializedParams):
    """Handle initialized notification — read client settings."""
    init_opts = getattr(ls, "initialization_options", None) or {}
    _apply_settings(ls, init_opts)
    logger.info(f"Client initialized (diagnostics={ls.diagnostics_enabled})")


@server.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(
    ls: IgnitionLanguageServer, params: DidChangeConfigurationParams
):
    """Handle workspace/didChangeConfiguration — update settings dynamically."""
    settings = getattr(params, "settings", None) or {}
    ignition_settings = settings.get("ignition", settings)
    _apply_settings(ls, ignition_settings)
    logger.info(f"Configuration updated (diagnostics={ls.diagnostics_enabled})")


def _apply_settings(ls: IgnitionLanguageServer, settings: dict) -> None:
    """Apply client settings to the server instance."""
    if isinstance(settings, dict):
        # Accept both flat and nested formats
        ignition = settings.get("ignition", settings)
        if isinstance(ignition, dict):
            diag = ignition.get("diagnostics", {})
            if isinstance(diag, dict):
                enabled = diag.get("enabled")
                if isinstance(enabled, bool):
                    ls.diagnostics_enabled = enabled
            elif isinstance(diag, bool):
                ls.diagnostics_enabled = diag


# ── Custom LSP Methods: Stubs Info ────────────────────────────────


@server.feature("ignition/stubsInfo")
def stubs_info_handler(ls: IgnitionLanguageServer, params: object) -> dict:
    """Return paths to generated stub directories for type checker config.

    Clients can use this to configure Pyright/Pylance extraPaths.
    """
    try:
        from ignition_lsp.stub_generator import get_system_stubs_path

        result: dict = {
            "systemStubsPath": get_system_stubs_path(),
            "projectStubsPath": None,
        }

        if ls.project_index:
            from ignition_lsp.stub_generator import STUBS_DIR_NAME
            project_stubs = Path(ls.project_index.root_path) / STUBS_DIR_NAME
            if project_stubs.is_dir():
                result["projectStubsPath"] = str(project_stubs)

        return result
    except Exception as e:
        logger.error(f"Error getting stubs info: {e}", exc_info=True)
        return {"systemStubsPath": None, "projectStubsPath": None}


# ── Document Synchronization Handlers ────────────────────────────


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: IgnitionLanguageServer, params: DidOpenTextDocumentParams):
    """Handle document open event."""
    logger.info(f"Document opened: {params.text_document.uri}")

    # Kick off project scan in the background (non-blocking).
    # system.* completions work immediately; project.*/shared.* completions
    # become available once the scan finishes.
    asyncio.ensure_future(ls.ensure_project_index_async(params.text_document.uri))

    # Run diagnostics on open
    if ls.diagnostics_enabled:
        await run_diagnostics(ls, params.text_document.uri)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls: IgnitionLanguageServer, params: DidChangeTextDocumentParams):
    """Handle document change event."""
    logger.debug(f"Document changed: {params.text_document.uri}")

    # Run diagnostics on change (with debouncing in production)
    if ls.diagnostics_enabled:
        await run_diagnostics(ls, params.text_document.uri)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
async def did_save(ls: IgnitionLanguageServer, params: DidSaveTextDocumentParams):
    """Handle document save event."""
    uri = params.text_document.uri
    logger.info(f"Document saved: {uri}")

    # Invalidate symbol cache when a .py file is saved
    file_path = unquote(urlparse(uri).path)
    if file_path.endswith(".py") and ls.symbol_cache is not None:
        ls.symbol_cache.invalidate(file_path)

    # Re-index project when resource/view JSON files change
    basename = Path(file_path).name
    if basename in ("resource.json", "view.json", "tags.json", "data.json"):
        if ls.project_index is not None:
            logger.info(f"Re-scanning project after {basename} save")
            ls.scan_project(ls.project_index.root_path)

    # Run diagnostics on save
    if ls.diagnostics_enabled:
        await run_diagnostics(ls, uri)


@server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: IgnitionLanguageServer, params: DidCloseTextDocumentParams):
    """Handle document close event."""
    logger.info(f"Document closed: {params.text_document.uri}")

    # Clear diagnostics for closed document
    ls.text_document_publish_diagnostics(
        PublishDiagnosticsParams(
            uri=params.text_document.uri,
            diagnostics=[],
        )
    )


async def run_diagnostics(ls: IgnitionLanguageServer, uri: str):
    """Run diagnostics on a document."""
    try:
        # Use absolute import to avoid package issues when running as __main__
        from ignition_lsp.diagnostics import get_diagnostics

        doc = ls.workspace.get_text_document(uri)
        diagnostics = get_diagnostics(doc)

        # Publish diagnostics using pygls 2.0 API
        ls.text_document_publish_diagnostics(
            PublishDiagnosticsParams(
                uri=uri,
                diagnostics=diagnostics,
            )
        )
        logger.info(f"Published {len(diagnostics)} diagnostics for {uri}")

    except Exception as e:
        logger.error(f"Error running diagnostics: {e}", exc_info=True)
        # Don't crash the server on diagnostic errors
        try:
            ls.text_document_publish_diagnostics(
                PublishDiagnosticsParams(
                    uri=uri,
                    diagnostics=[],
                )
            )
        except Exception as e:
            logger.warning(f"Failed to clear diagnostics for {uri}: {e}")


# LSP Feature Handlers

@server.feature(TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=["."]))
def completion(ls: IgnitionLanguageServer, params: CompletionParams) -> Optional[CompletionList]:
    """Provide completion items for Ignition APIs."""
    logger.info(f"Completion requested at {params.position}")

    if ls.api_loader:
        try:
            from ignition_lsp.completion import get_completions
            doc = ls.workspace.get_text_document(params.text_document.uri)
            return get_completions(doc, params.position, ls.api_loader, ls.project_index, ls.java_loader, ls.symbol_cache, ls.pylib_loader)
        except Exception as e:
            logger.error(f"Error getting completions: {e}", exc_info=True)
            return CompletionList(is_incomplete=False, items=[])

    # API loader not initialized — provide a minimal hint
    logger.warning("Completion requested but API loader is not initialized")
    return CompletionList(is_incomplete=False, items=[
        CompletionItem(
            label="system",
            detail="Ignition system functions",
            documentation="Ignition platform system functions",
        ),
    ])


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: IgnitionLanguageServer, params: HoverParams) -> Optional[Hover]:
    """Provide hover information for Ignition functions."""
    logger.info(f"Hover requested at {params.position}")

    if ls.api_loader:
        try:
            from ignition_lsp.hover import get_hover_info
            doc = ls.workspace.get_text_document(params.text_document.uri)
            return get_hover_info(doc, params.position, ls.api_loader, ls.java_loader, ls.project_index, ls.symbol_cache, ls.pylib_loader)
        except Exception as e:
            logger.error(f"Error getting hover info: {e}", exc_info=True)
            return None

    # API loader not initialized
    return Hover(
        contents=MarkupContent(
            kind=MarkupKind.Markdown,
            value="**Ignition Function**\n\nAPI database not loaded.",
        )
    )


@server.feature(TEXT_DOCUMENT_DEFINITION)
def definition(ls: IgnitionLanguageServer, params: DefinitionParams) -> Optional[Location]:
    """Navigate to definition of Ignition resources."""
    logger.info(f"Definition requested at {params.position}")

    try:
        from ignition_lsp.definition import get_definition
        doc = ls.workspace.get_text_document(params.text_document.uri)
        return get_definition(doc, params.position, ls.api_loader, ls.project_index, ls.symbol_cache)
    except Exception as e:
        logger.error(f"Error getting definition: {e}", exc_info=True)
        return None


@server.feature(WORKSPACE_SYMBOL)
def workspace_symbol(
    ls: IgnitionLanguageServer, params: WorkspaceSymbolParams
) -> Optional[List[SymbolInformation]]:
    """Return workspace symbols from the project index."""
    logger.info(f"Workspace symbol query: '{params.query}'")

    try:
        from ignition_lsp.workspace_symbols import get_workspace_symbols
        return get_workspace_symbols(params.query, ls.project_index)
    except Exception as e:
        logger.error(f"Error getting workspace symbols: {e}", exc_info=True)
        return None


# ── Custom Ignition Methods ──────────────────────────────────────────


def _param(params: object, key: str, default: object = "") -> object:
    """Extract a parameter from pygls Object or plain dict.

    pygls 2.0 wraps custom method params in an attrs-based Object class,
    not a plain dict. This helper handles both for testability.
    """
    if isinstance(params, dict):
        return params.get(key, default)
    return getattr(params, key, default)


@server.feature("ignition/findScripts")
def find_scripts_handler(ls: IgnitionLanguageServer, params: object) -> list:
    """Find all embedded scripts in a JSON resource file."""
    uri = str(_param(params, "uri", ""))
    logger.info(f"ignition/findScripts: {uri}")

    try:
        from ignition_lsp.json_scanner import find_scripts

        file_path = unquote(urlparse(uri).path)
        scripts = find_scripts(file_path)
        return [
            {
                "key": s.key,
                "line": s.line,
                "content": s.content,
                "context": s.context,
                "decodedPreview": s.decoded_preview,
            }
            for s in scripts
        ]
    except Exception as e:
        logger.error(f"Error finding scripts: {e}", exc_info=True)
        return []


@server.feature("ignition/decodeScript")
def decode_script_handler(ls: IgnitionLanguageServer, params: object) -> dict:
    """Decode an Ignition-encoded script string.

    Returns dedented content and the indent prefix that was stripped,
    so the editor can re-add it on save.
    """
    encoded = str(_param(params, "encoded", ""))
    logger.info(f"ignition/decodeScript: {len(encoded)} chars")

    try:
        from ignition_lsp.encoding import decode, dedent

        decoded = decode(encoded)
        text, indent = dedent(decoded)
        return {"decoded": text, "indent": indent}
    except Exception as e:
        logger.error(f"Error decoding script: {e}", exc_info=True)
        return {"decoded": "", "indent": "", "error": str(e)}


@server.feature("ignition/encodeScript")
def encode_script_handler(ls: IgnitionLanguageServer, params: object) -> dict:
    """Encode a Python script for storage in Ignition JSON."""
    decoded = str(_param(params, "decoded", ""))
    logger.info(f"ignition/encodeScript: {len(decoded)} chars")

    try:
        from ignition_lsp.encoding import encode

        return {"encoded": encode(decoded)}
    except Exception as e:
        logger.error(f"Error encoding script: {e}", exc_info=True)
        return {"encoded": "", "error": str(e)}


@server.feature("ignition/saveScript")
def save_script_handler(ls: IgnitionLanguageServer, params: object) -> dict:
    """Save a decoded script back into its source JSON file.

    Encodes the content and writes it into the correct position in the
    source JSON file.
    """
    uri = str(_param(params, "uri", ""))
    line = int(_param(params, "line", 0))
    key = str(_param(params, "key", ""))
    decoded_content = str(_param(params, "decodedContent", ""))
    indent = str(_param(params, "indent", ""))
    logger.info(f"ignition/saveScript: {uri} line={line} key={key} indent={repr(indent)}")

    try:
        from ignition_lsp.encoding import encode, reindent
        from ignition_lsp.json_scanner import replace_script_in_line

        file_path = unquote(urlparse(uri).path)
        path = Path(file_path)

        if not path.is_file():
            return {"success": False, "error": f"File not found: {file_path}"}

        lines = path.read_text(encoding="utf-8").splitlines(True)
        line_idx = line - 1  # Convert 1-based to 0-based

        if line_idx < 0 or line_idx >= len(lines):
            return {"success": False, "error": f"Line {line} out of range"}

        # Re-indent before encoding (reverses the dedent from decodeScript)
        full_content = reindent(decoded_content, indent) if indent else decoded_content
        encoded = encode(full_content)
        # splitlines(True) preserves the line ending; strip it for replacement
        original_line = lines[line_idx]
        trailing = ""
        if original_line.endswith("\n"):
            trailing = "\n"
            original_line = original_line[:-1]
        if original_line.endswith("\r"):
            trailing = "\r" + trailing
            original_line = original_line[:-1]

        new_line = replace_script_in_line(original_line, key, encoded)

        if new_line == original_line:
            return {"success": False, "error": f"Key '{key}' not found on line {line}"}

        lines[line_idx] = new_line + trailing
        path.write_text("".join(lines), encoding="utf-8")

        logger.info(f"Saved script to {file_path} line {line}")
        return {"success": True}

    except Exception as e:
        logger.error(f"Error saving script: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def main():
    """Start the Ignition LSP server."""
    logger.info("Starting Ignition LSP Server...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Server version: v0.2.0")

    try:
        # Start the server using stdio
        server.start_io()
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
