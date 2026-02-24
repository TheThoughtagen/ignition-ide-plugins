"""Main LSP server implementation."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlparse

import lsprotocol.types
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS,
    WORKSPACE_SYMBOL,
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
        logging.FileHandler('/tmp/ignition-lsp.log'),
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


server = IgnitionLanguageServer("ignition-lsp", "v0.1.0")

# Initialize API loaders and symbol cache on server creation
server.initialize_api_loader()
server.initialize_java_loader()
server.initialize_pylib_loader()

from ignition_lsp.script_symbols import SymbolCache
server.symbol_cache = SymbolCache()


# Document Synchronization Handlers

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
        except:
            pass


# LSP Feature Handlers

@server.feature(TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=["."]))
def completion(ls: IgnitionLanguageServer, params: CompletionParams) -> Optional[CompletionList]:
    """Provide completion items for Ignition APIs."""
    logger.info(f"Completion requested at {params.position}")

    # Use API loader if available
    if ls.api_loader:
        try:
            from ignition_lsp.completion import get_completions
            doc = ls.workspace.get_text_document(params.text_document.uri)
            return get_completions(doc, params.position, ls.api_loader, ls.project_index, ls.java_loader, ls.symbol_cache, ls.pylib_loader)
        except Exception as e:
            logger.error(f"Error getting completions: {e}", exc_info=True)

    # Fallback to basic completions
    items = [
        CompletionItem(
            label="system",
            detail="Ignition system functions",
            documentation="Ignition platform system functions",
        ),
    ]

    return CompletionList(is_incomplete=False, items=items)


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: IgnitionLanguageServer, params: HoverParams) -> Optional[Hover]:
    """Provide hover information for Ignition functions."""
    logger.info(f"Hover requested at {params.position}")

    # Use API loader if available
    if ls.api_loader:
        try:
            from ignition_lsp.hover import get_hover_info
            doc = ls.workspace.get_text_document(params.text_document.uri)
            return get_hover_info(doc, params.position, ls.api_loader, ls.java_loader, ls.project_index, ls.symbol_cache, ls.pylib_loader)
        except Exception as e:
            logger.error(f"Error getting hover info: {e}", exc_info=True)

    # Fallback
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


def main():
    """Start the Ignition LSP server."""
    logger.info("Starting Ignition LSP Server...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Server version: v0.1.0")

    try:
        # Start the server using stdio
        server.start_io()
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
