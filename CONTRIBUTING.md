# Contributing to Ignition Dev Tools

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

### Prerequisites

- **Neovim** >= 0.11.0 (for Neovim plugin development)
- **Python** >= 3.8 (for LSP server)
- **Node.js** >= 20 (for VS Code extension development)
- **Git**
- **luacheck** (for Lua linting)

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/TheThoughtagen/ignition-nvim.git
   cd ignition-nvim
   ```

2. **Set up the Python LSP server:**
   ```bash
   cd packages/ignition-lsp
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Set up the VS Code extension:**
   ```bash
   cd packages/ignition-vscode
   npm ci
   npm run compile
   ```

4. **Install test dependencies:**
   - [plenary.nvim](https://github.com/nvim-lua/plenary.nvim) for Lua tests
   - pytest for Python tests (installed with `[dev]` extras above)
   - Vitest for VS Code tests (installed with `npm ci` above)

## Project Structure

```
ignition-nvim/                    # Monorepo root
├── packages/
│   ├── ignition-lsp/            # Python LSP server (shared by both editors)
│   │   ├── ignition_lsp/        # Server source
│   │   │   ├── server.py        # Main server, request routing
│   │   │   ├── completion.py    # Completions
│   │   │   ├── hover.py         # Hover documentation
│   │   │   ├── diagnostics.py   # ignition-lint integration
│   │   │   ├── definition.py    # Go-to-definition
│   │   │   ├── api_loader.py    # API database loader
│   │   │   ├── project_scanner.py # Project indexing
│   │   │   ├── api_db/          # API definitions (14 modules, JSON)
│   │   │   ├── java_db/         # Java class definitions (JSON)
│   │   │   └── stubs/           # Pyright/Pylance type stubs
│   │   ├── tests/               # Python tests (pytest)
│   │   └── pyproject.toml
│   │
│   ├── ignition-nvim/           # Neovim plugin (Lua)
│   │   ├── lua/ignition/        # Plugin source
│   │   │   ├── init.lua         # Entry point, setup()
│   │   │   ├── config.lua       # Configuration schema
│   │   │   ├── encoding.lua     # Encode/decode scripts
│   │   │   ├── decoder.lua      # Interactive decode workflow
│   │   │   ├── virtual_doc.lua  # Virtual buffer system
│   │   │   ├── lsp.lua          # LSP client
│   │   │   └── kindling.lua     # Kindling integration
│   │   ├── ftdetect/            # Filetype detection
│   │   ├── ftplugin/            # Filetype settings
│   │   ├── syntax/              # Syntax highlighting
│   │   ├── plugin/              # Plugin autoload
│   │   ├── doc/                 # Vim help files
│   │   └── lazy.lua             # lazy.nvim plugin spec
│   │
│   └── ignition-vscode/         # VS Code extension (TypeScript)
│       ├── src/                 # Extension source
│       │   ├── extension.ts     # Entry point
│       │   ├── lsp/             # LSP client management
│       │   ├── encoding/        # Decode/encode, CodeLens
│       │   └── views/           # Project Browser, Tag Browser, etc.
│       ├── test/                # Vitest tests
│       ├── syntaxes/            # TextMate grammars
│       ├── resources/           # Icons and static assets
│       └── package.json
│
├── tests/                       # Lua tests (plenary.nvim)
│   ├── minimal_init.lua         # Test harness
│   └── *_spec.lua               # 7 spec files
│
├── docs/                        # User documentation (Docusaurus)
├── website/                     # Docusaurus site
├── claude-code-plugin/          # Claude Code integration
├── templates/                   # Per-project Claude Code templates
│
├── lua/ -> packages/ignition-nvim/lua       # Symlinks for Neovim runtimepath
├── lsp/ -> packages/ignition-lsp
├── ftdetect/ -> packages/ignition-nvim/ftdetect
├── ftplugin/ -> packages/ignition-nvim/ftplugin
├── plugin/ -> packages/ignition-nvim/plugin
├── syntax/ -> packages/ignition-nvim/syntax
├── queries/ -> packages/ignition-nvim/queries
├── doc/ -> packages/ignition-nvim/doc
├── lazy.lua -> packages/ignition-nvim/lazy.lua
│
└── .github/workflows/           # CI/CD pipelines
    ├── ci.yml                   # Test and lint (all packages)
    ├── beta.yml                 # PyPI beta releases
    ├── release.yml              # PyPI releases
    ├── release-vscode.yml       # VS Code Marketplace releases
    └── deploy-docs.yml          # Docusaurus deployment
```

## Running Tests

### Python Tests (pytest)

**All tests (162 tests across 7 test files):**
```bash
cd packages/ignition-lsp
venv/bin/python -m pytest tests/ -v
```

**With coverage:**
```bash
cd packages/ignition-lsp
venv/bin/python -m pytest tests/ -v --cov=ignition_lsp
```

**Single file:**
```bash
cd packages/ignition-lsp
venv/bin/python -m pytest tests/test_completion.py -v
```

### Lua Tests (plenary.nvim)

**All tests (107 tests across 7 spec files):**
```bash
nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua'}"
```

**Single file:**
```bash
nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedFile tests/encoding_spec.lua"
```

### VS Code Extension Tests (Vitest)

```bash
cd packages/ignition-vscode
npm test
```

## Linting

### Python

```bash
cd packages/ignition-lsp
venv/bin/ruff check ignition_lsp/
venv/bin/mypy ignition_lsp/
venv/bin/black --check ignition_lsp/
```

**Auto-fix with Black:**
```bash
cd packages/ignition-lsp
venv/bin/black ignition_lsp/
```

### Lua

```bash
luacheck lua/ --config .luacheckrc
```

### TypeScript

```bash
cd packages/ignition-vscode
npx eslint src/ --ext .ts
```

## Contribution Guidelines

### Code Style

**Lua:**
- Follow Neovim plugin conventions
- Use `snake_case` for functions and variables
- Add comments for complex logic
- Prefer explicit over implicit

**Python:**
- Black formatting (line length 100)
- Type hints for all function signatures
- Follow PEP 8
- Docstrings for public functions

**TypeScript:**
- ESLint rules in `packages/ignition-vscode/.eslintrc.json`
- Strict TypeScript (`strict: true`)
- Prefer `async`/`await` over raw Promises

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format with optional scope:

- `feat:` / `feat(vscode):` — New feature
- `fix:` / `fix(lsp):` — Bug fix
- `refactor:` / `refactor(nvim):` — Code refactoring (no behavior change)
- `test:` — Adding/updating tests
- `docs:` — Documentation changes
- `chore:` — Maintenance tasks (CI, deps, etc.)

**Scopes:** `lsp`, `nvim`, `vscode` for package-specific changes. Omit scope for cross-cutting changes.

**Examples:**
```
feat(vscode): add Tag Browser for ignition-git-module format
fix(lsp): prevent duplicate completions for overloaded functions
refactor(nvim): extract common encoding logic
feat: diagnostics toggle and Pyright/Pylance stubs integration
test: add round-trip encoding tests
docs: update installation instructions for monorepo
chore: bump pygls to 2.0.1
```

### Pull Request Process

1. **Fork the repository** and create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes** with tests:
   - Add tests for new features
   - Update tests for bug fixes
   - Ensure all tests pass

3. **Run linting:**
   ```bash
   # Lua
   luacheck lua/

   # Python
   cd packages/ignition-lsp
   venv/bin/ruff check ignition_lsp/
   venv/bin/mypy ignition_lsp/
   venv/bin/black --check ignition_lsp/

   # TypeScript
   cd packages/ignition-vscode
   npx eslint src/ --ext .ts
   ```

4. **Commit with conventional commit messages:**
   ```bash
   git add .
   git commit -m "feat(vscode): add workspace symbols support"
   ```

5. **Push and open a pull request:**
   ```bash
   git push origin feat/my-feature
   ```

6. **Respond to review feedback:**
   - Address reviewer comments
   - Make requested changes
   - Update tests as needed

## Critical Areas (Require Discussion First)

**Always open an issue or discussion before modifying:**

- **Encoding/decoding logic** (`packages/ignition-nvim/lua/ignition/encoding.lua`, `packages/ignition-vscode/src/encoding/`) — Round-trip fidelity is the most fragile part of the system. Any changes must preserve `encode(decode(x)) == x`.

- **LSP protocol handlers** (`packages/ignition-lsp/ignition_lsp/server.py`) — These affect every user's editor experience. Changes to request handlers, capabilities, or the LSP protocol require careful review.

- **API database schema** (`packages/ignition-lsp/ignition_lsp/api_db/schema.json`) — All 14 module files depend on this schema. Schema changes require updating all modules and tests.

- **Breaking configuration changes** — Anything that changes the Neovim `setup(opts)` interface, VS Code `package.json` contributes, or default behavior.

- **CI/CD pipeline modifications** (`.github/workflows/*.yml`) — These control releases and publishing to PyPI and VS Code Marketplace. Errors can break deployments.

- **Package metadata** (`packages/ignition-lsp/pyproject.toml`, `packages/ignition-vscode/package.json`) — Version numbers, dependencies, and publish config must be handled carefully.

- **Git operations** — Never force-push to main. Never amend published commits. Always use feature branches.

- **Cross-repo changes** — Anything that affects `ignition-lint` or other Whiskey House projects requires coordination.

**Safe to proceed without discussion:**

- Adding new API modules (as long as they follow `schema.json`)
- Adding test cases
- Bug fixes with clear scope and comprehensive tests
- Documentation improvements (typos, clarity, examples)
- Adding code examples or fixtures

## Adding API Functions

To add new functions to the LSP server's knowledge base:

1. **Find or create the module JSON** in `packages/ignition-lsp/ignition_lsp/api_db/`
   - Use existing modules as templates
   - Follow the exact structure in `schema.json`

2. **Add function definition:**
   ```json
   {
     "name": "readBlocking",
     "signature": "readBlocking(tagPaths, timeout=45000)",
     "description": "Read one or more tags synchronously",
     "parameters": [
       {
         "name": "tagPaths",
         "type": "List[str]",
         "description": "Tag paths to read"
       },
       {
         "name": "timeout",
         "type": "int",
         "description": "Timeout in milliseconds",
         "optional": true
       }
     ],
     "returns": {
       "type": "List[QualifiedValue]",
       "description": "List of qualified tag values"
     },
     "scope": "both",
     "docs": "https://docs.inductiveautomation.com/..."
   }
   ```

3. **Add tests** in `packages/ignition-lsp/tests/test_completion.py`

4. **Verify:**
   ```bash
   cd packages/ignition-lsp
   venv/bin/python -m pytest tests/test_completion.py -v -k readBlocking
   ```

## Testing Guidelines

- **All new features require tests** — No exceptions
- **Maintain or improve coverage** — Run with `--cov` to check
- **Test all affected packages** — LSP changes may need both Python and editor-specific tests
- **Use fixtures** — `tests/fixtures/` (Lua) and `packages/ignition-lsp/tests/fixtures/` (Python)
- **Test edge cases** — Empty inputs, special characters, error conditions
- **Test round-trip operations** — Especially for encoding/decoding

### Test Organization

**Lua tests (`tests/*_spec.lua`):**
- `encoding_spec.lua` — Encode/decode round-trip tests
- `json_parser_spec.lua` — JSON script extraction
- `decoder_spec.lua` — Interactive decode workflow
- `virtual_doc_spec.lua` — Virtual buffer system
- `lsp_spec.lua` — LSP client initialization
- `kindling_spec.lua` — Kindling integration
- `config_spec.lua` — Configuration validation

**Python tests (`packages/ignition-lsp/tests/test_*.py`):**
- `test_completion.py` — Completion provider
- `test_hover.py` — Hover documentation
- `test_diagnostics.py` — Diagnostic integration
- `test_definition.py` — Go-to-definition
- `test_api_loader.py` — API database loading
- `test_project_scanner.py` — Project indexing
- `test_workspace_symbols.py` — Workspace symbols

**VS Code tests (`packages/ignition-vscode/test/`):**
- Vitest suite for extension functionality

## Documentation

When making changes, update relevant documentation:

### User-Facing Changes

- Update `docs/` (Docusaurus site) for new features or changed behavior
- Update the root `README.md` if installation or quick start changes
- Update per-package READMEs for package-specific changes
- Update `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/) format

### Developer Documentation

- Add docstrings to Python functions (Google style)
- Add comments for complex Lua logic
- Update `CLAUDE.md` (`.ai/instructions.md`) if architecture changes
- Update this file (`CONTRIBUTING.md`) if contribution process changes

## Questions?

- **Architecture details**: Review [CLAUDE.md](CLAUDE.md)
- **Common issues**: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Design questions**: Open a [GitHub Discussion](https://github.com/TheThoughtagen/ignition-nvim/discussions)
- **Bug reports**: Open a [GitHub Issue](https://github.com/TheThoughtagen/ignition-nvim/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
