# Ignition LSP Server

Language Server Protocol implementation for Ignition by Inductive Automation.

## Features

- Autocompletion for `system.*`, `project.*`, and `shared.*` namespaces (239+ functions across 14 modules)
- Hover documentation with function signatures, parameter details, and scope info
- Go-to-definition for API functions and project scripts
- Diagnostics for common scripting issues
- Workspace symbols for project-wide script navigation
- Project indexing across Ignition resource files

## Installation

### From PyPI

```bash
pip install ignition-lsp
```

### From Source

```bash
cd lsp
pip install -e .
```

### Development Installation

```bash
cd lsp
pip install -e ".[dev]"
```

## Usage

The LSP server is automatically started by the ignition.nvim plugin when editing Ignition files.

### Manual Start

```bash
ignition-lsp
```

The server communicates via stdio and follows the LSP specification.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black ignition_lsp tests
```

### Type Checking

```bash
mypy ignition_lsp
```

### Linting

```bash
ruff check ignition_lsp tests
```

## Architecture

- `server.py` - Main LSP server implementation using pygls 2.0
- `api_loader.py` - API database loader and indexer
- `completion.py` - Completion provider for Ignition APIs and project scripts
- `hover.py` - Hover documentation provider
- `diagnostics.py` - Diagnostic provider for code analysis
- `definition.py` - Go-to-definition for API functions and project scripts
- `project_scanner.py` - Ignition project structure indexer
- `workspace_symbols.py` - Workspace symbol provider
- `api_db/` - Ignition API function definitions (14 modules, 239+ functions)

## Contributing

See the main project README for contribution guidelines.

## License

MIT License - see LICENSE file for details.
