# CLAUDE.md — Ignition Dev Tools

## Project Overview

**Ignition Dev Tools** is a multi-editor monorepo providing full IDE support for Inductive Automation's Ignition SCADA platform. It delivers LSP completions, hover docs, diagnostics, script decode/encode, project browsing, and more — for **Neovim**, **VS Code**, and **Zed**.

Part of the **Whiskey House Ignition Developer Toolkit**:
- **Ignition Dev Tools** — Neovim, VS Code, and Zed IDE support (this repo)
- **ignition-lint** — Static analysis for Ignition Python scripts
- **ignition-git-module** — Native Git inside Ignition Designer

## Monorepo Structure

```
packages/
├── ignition-lsp/        # Python LSP server (shared by all editors)
├── ignition-nvim/       # Neovim plugin (Lua)
├── ignition-vscode/     # VS Code extension (TypeScript)
└── ignition-zed/        # Zed extension (Rust → WebAssembly)
```

Top-level symlinks (`lua/`, `lsp/`, `ftdetect/`, `ftplugin/`, `plugin/`, `syntax/`, `queries/`, `doc/`, `lazy.lua`) point into `packages/` so the repo works directly as a Neovim plugin via lazy.nvim's `runtimepath` discovery.

## Architecture

### Python LSP Server (`packages/ignition-lsp/`)
pygls 2.0 language server — shared by all editors.

| Module | Responsibility |
|--------|---------------|
| `server.py` | Main pygls server, document sync, request routing |
| `completion.py` | Context-aware completions for `system.*` and project scripts |
| `hover.py` | Hover documentation from API database |
| `diagnostics.py` | Integration with `ignition-lint` JythonValidator |
| `definition.py` | Go-to-definition for `system.*` and project scripts |
| `api_loader.py` | Loads and indexes API definitions from `api_db/` JSON |
| `project_scanner.py` | Walks Ignition project dirs, builds script index |
| `workspace_symbols.py` | Exposes project index via LSP workspace symbols |
| `script_files.py` | Sidecar decoded-script files (path + metadata header) for clients without virtual documents |
| `api_db/*.json` | 14 modules, 239 functions — follows `api_db/schema.json` |
| `java_db/*.json` | Java/Jython class completions (26 packages, 146 classes) |
| `stubs/**/*.pyi` | Pyright/Pylance type stubs for Ignition APIs |

### Neovim Plugin (`packages/ignition-nvim/`)
Core Neovim plugin loaded at runtime.

| Module | Responsibility |
|--------|---------------|
| `lua/ignition/init.lua` | Entry point, `setup(opts)`, initializes subsystems |
| `lua/ignition/config.lua` | Configuration schema, validation, defaults |
| `lua/ignition/encoding.lua` | Encode/decode scripts (Ignition Flint format) |
| `lua/ignition/json_parser.lua` | Find embedded scripts in JSON by key names |
| `lua/ignition/decoder.lua` | Decode workflow: interactive selection, decode all, list scripts |
| `lua/ignition/virtual_doc.lua` | Virtual buffer system: `acwrite` buffers, auto-save, source tracking |
| `lua/ignition/lsp.lua` | LSP client via `vim.lsp.start()` (Neovim 0.11+) |
| `lua/ignition/kindling.lua` | Integration with Kindling for `.gwbk` files |

### VS Code Extension (`packages/ignition-vscode/`)
TypeScript extension providing IDE features in VS Code.

| Component | Responsibility |
|-----------|---------------|
| `src/extension.ts` | Extension entry point, activation, command registration |
| `src/lsp/` | LSP client management, auto-install of ignition-lsp |
| `src/encoding/` | Decode/encode scripts, CodeLens for embedded scripts |
| `src/views/projectBrowser.ts` | Designer-style project tree sidebar |
| `src/views/tagBrowser.ts` | Tag browser for ignition-git-module tag exports |
| `src/views/componentTree.ts` | Perspective view component hierarchy |
| `resources/` | Sidebar icons and static assets |
| `syntaxes/` | TextMate grammars for syntax highlighting |
| `test/` | Vitest test suite |

### Zed Extension (`packages/ignition-zed/`)
Rust extension compiled to WebAssembly (`wasm32-wasip2`), built against `zed_extension_api` 0.7.

| Component | Responsibility |
|-----------|---------------|
| `extension.toml` | Extension manifest; registers `ignition-lsp` for the Python and JSON languages |
| `src/lib.rs` | Binary discovery, venv auto-install, project gating, settings passthrough |
| `Cargo.lock` | Committed — the Zed extension registry builds from it |

Zed has no API for sidebars, custom commands, or CodeLens, so the Project Browser,
Tag Browser, Component Tree, and Kindling integration are VS Code / Neovim only.
Decode/encode is exposed instead through standard LSP code actions (see below).

### Supporting Files
- `lazy.lua` → symlink to `packages/ignition-nvim/lazy.lua` (lazy.nvim plugin spec)
- `ftdetect/`, `ftplugin/`, `syntax/`, `plugin/`, `queries/`, `doc/` → symlinks for Neovim runtimepath
- `lsp/` → symlink to `packages/ignition-lsp/`
- `website/` — Docusaurus documentation site
- `claude-code-plugin/` — Claude Code plugin for Ignition awareness
- `templates/` — Per-project Claude Code templates

## Domain Context

**Ignition** is a SCADA/ICS platform by Inductive Automation. Projects are stored as JSON files containing embedded Python (Jython) scripts. Developers use `system.*` scripting APIs (e.g., `system.tag.readBlocking()`, `system.db.runPrepQuery()`, `system.perspective.sendMessage()`).

All three editors decode those embedded scripts into editable Python buffers with full LSP support, then encode them back. Zed uses real sidecar files rather than in-memory buffers (see Code Actions below).

## Critical Technical Details

### Encoding (HANDLE WITH EXTREME CARE)
- Uses **Ignition Flint format** — plain string replacement, NOT base64
- Standard JSON escapes: `\"`, `\n`, `\t`, `\b`, `\r`, `\f`
- Unicode escapes: `<` → `\u003c`, `>` → `\u003e`, `&` → `\u0026`, `=` → `\u003d`, `'` → `\u0027`
- **Order matters:** backslash first to avoid double-escaping
- **Round-trip fidelity is sacred:** `encode(decode(x)) == x` must always hold
- Lua encoding uses `string.gsub` with **plain flag** — NOT Lua patterns (this caused bugs)
- VS Code encoding in `src/encoding/` mirrors the same logic in TypeScript

### Code Actions (decode/encode for plain LSP clients)
- `textDocument/codeAction` offers **Ignition: Decode …** on a JSON resource line
  holding an encoded script, and **Ignition: Save … back to JSON** on a decoded file
- Backed by the `ignition.decodeScriptToFile` and `ignition.saveScriptToSource`
  commands (`workspace/executeCommand`)
- Decoded scripts land in `.ignition-scripts/` at the project root, carrying a
  comment header (`# >>> ignition-lsp:begin`) that records source URI, key, line,
  indent, and a digest of the encoded script — the save path reads it, so
  **never change the header format without changing `parse_header` in lockstep**
- `_validate_sidecar_target()` runs before every write: the sidecar must sit at
  the path `sidecar_path()` derives from its own header, the source must resolve
  inside the owning project, and the digest must still match the script at
  (line, key). A stale sidecar is refused rather than allowed to overwrite a
  script that moved into its position
- Both save paths funnel through `_write_script_to_source()` so round-trip
  behaviour cannot diverge between clients

### LSP Client
- **Neovim:** Uses `vim.lsp.start()` — modern Neovim 0.11+ API, NOT lspconfig
- **VS Code:** Uses `vscode-languageclient` — standard VS Code LSP client library
- **Zed:** Extension returns the server command from `language_server_command()`;
  declines (returns `Err`) when the worktree has no root `project.json`, which is
  what keeps the server off unrelated Python/JSON files
- All three auto-install `ignition-lsp` from PyPI on first activation
- Python venv at `packages/ignition-lsp/venv/` (Python 3.13 for local dev)

### Virtual Buffers (Neovim)
- Use `acwrite` buftype with `BufWriteCmd` autocmd
- Saving a virtual buffer encodes the script back into the source JSON

### CodeLens (VS Code)
- "Edit Script" actions appear above embedded Python in JSON resource files
- Clicking decodes the script into an editable Python buffer

## Build / Test / Lint Commands

### Python LSP Server (`packages/ignition-lsp/`)
```bash
# Setup
cd packages/ignition-lsp && python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# Tests (162 tests across 7 test files)
cd packages/ignition-lsp && venv/bin/python -m pytest tests/ -v

# With coverage
cd packages/ignition-lsp && venv/bin/python -m pytest tests/ -v --cov=ignition_lsp

# Linting
cd packages/ignition-lsp && venv/bin/ruff check ignition_lsp/
cd packages/ignition-lsp && venv/bin/mypy ignition_lsp/
cd packages/ignition-lsp && venv/bin/black --check ignition_lsp/
```

### Lua Tests (`tests/` — plenary.nvim / busted)
```bash
# All tests (107 tests across 7 spec files)
nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua'}"

# Single file
nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedFile tests/encoding_spec.lua"
```

### Lua Linting
```bash
luacheck lua/ --config .luacheckrc
```

### VS Code Extension (`packages/ignition-vscode/`)
```bash
# Setup
cd packages/ignition-vscode && npm ci

# Compile TypeScript
cd packages/ignition-vscode && npm run compile

# Tests (Vitest)
cd packages/ignition-vscode && npm test

# Lint
cd packages/ignition-vscode && npx eslint src/ --ext .ts

# Package .vsix
cd packages/ignition-vscode && npx @vscode/vsce package
```

### Zed Extension (`packages/ignition-zed/`)
```bash
# Setup (once)
rustup target add wasm32-wasip2

# Build the WASM extension
cd packages/ignition-zed && cargo build --target wasm32-wasip2 --release

# Lint / format
cd packages/ignition-zed && cargo clippy --target wasm32-wasip2 --release -- -D warnings
cd packages/ignition-zed && cargo fmt --check
```

Load it in Zed via `zed: extensions` → **Install Dev Extension** → `packages/ignition-zed`.

## Git Workflow

- **Branch:** Work on `main` (single contributor flow)
- **Commits:** Conventional format — `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- **Scoped commits:** Use scope for package-specific changes — `feat(vscode):`, `fix(lsp):`, `refactor(nvim):`, `feat(zed):`
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) — Lua tests (Neovim stable+nightly), Python tests (3.9/3.11/3.13), VS Code extension tests (Node 20), Zed extension (fmt/clippy/wasm build)
- **Release pipelines:**
  - `beta.yml` / `release.yml` — PyPI publishing for ignition-lsp
  - `release-vscode.yml` — VS Code Marketplace publishing (triggered by `vscode/v*` tags)
  - `deploy-docs.yml` — Docusaurus site deployment

## API Database

14 modules in `packages/ignition-lsp/ignition_lsp/api_db/`:
`system_alarm`, `system_dataset`, `system_date`, `system_db`, `system_file`, `system_gui`, `system_nav`, `system_net`, `system_opc`, `system_perspective`, `system_security`, `system_tag`, `system_user`, `system_util`

All follow `schema.json`. Adding a new module = immediate completions + hover for all users (all editors).

## Marketing (gitignored)

`marketing/` is gitignored and contains the Whiskey House marketing strategy:
- `plan.md` — Strategy, target audiences, channels, content mix, messaging pillars, launch sequence
- `calendar.md` — 12-week content calendar (36 posts), Phase 4 topic bank

3 posts/week: ~1 direct project content, ~1 tangential technical, ~1 community/opinion.

---

## Human-in-the-Loop Validation

**IMPORTANT:** Always confirm with the user before taking these actions:

### Always Ask First
- **Encoding changes** — Any modification to encoding/decode logic (Lua `encoding.lua` or TypeScript `src/encoding/`). Round-trip fidelity is the most fragile part of the system. Describe the change and get approval.
- **LSP protocol changes** — Modifications to `server.py` request handlers, new LSP capabilities, or changes to how clients connect. These affect every user's editor experience.
- **API database schema changes** — Modifications to `api_db/schema.json`. All 14 module files depend on it.
- **Breaking config changes** — Anything that changes the Neovim `setup(opts)` interface, VS Code `package.json` contributes, or default behavior.
- **CI/CD pipeline changes** — Modifications to `.github/workflows/*.yml`. These affect releases and publishing.
- **Package metadata** — Changes to `pyproject.toml` version/deps, `package.json` version/deps, or publish config.
- **Git operations** — Never push, force-push, rebase, or amend without explicit approval. Never commit unless asked.
- **Deleting files or code** — Confirm before removing any module, test file, or significant code block.
- **Marketing content** — Always present draft content for review before finalizing. Never post or publish anything.
- **Cross-repo changes** — Anything that affects `ignition-lint` or `ignition-git-module` integration.

### Safe to Proceed Without Asking
- Reading files, exploring code, running tests (read-only)
- Adding new API database module files (as long as they follow `schema.json`)
- Adding new test files or test cases
- Bug fixes with clear root cause and isolated scope
- Documentation edits (comments, docstrings, help files)
- Adding new entries to `.gitignore`

### When Uncertain
If a change doesn't clearly fall into either category, **ask**. The cost of a quick confirmation is low; the cost of breaking encode/decode round-trips or publishing bad releases is high.

## Ralph (Autonomous Agent)

This project has a separate AI agent (Ralph) configured in `.ralph/`:
- `PROMPT.md` — Vision doc with domain context, architecture, principles
- `AGENT.md` — Build/test/run commands
- `fix_plan.md` — Prioritized task list (7 priority levels, mostly complete)
- `specs/` — Detailed specs for API database, project indexing, go-to-definition

Ralph follows `fix_plan.md` and implements one task per loop. Claude Code should not modify Ralph's configuration without asking.

## Current State (March 2026)

- **Monorepo** with four packages: ignition-nvim, ignition-lsp, ignition-vscode, ignition-zed
- All 7 priority levels in `fix_plan.md` are complete
- 14 API modules, 239 functions + 26 Java packages (146 classes)
- 704 Python tests + 6 Rust tests + 107 Lua tests + VS Code extension tests — all passing
- VS Code extension features: CodeLens, Project Browser, Tag Browser, Component Tree, diagnostics toggle, Pyright/Pylance stubs
- Project indexing and go-to-definition implemented
- Kindling integration tested across platforms
- lazy.nvim spec with auto LSP install (Neovim), auto LSP install (VS Code)
- CI pipeline: Lua (stable+nightly), Python (3.9/3.11/3.13), VS Code (Node 20), Zed (wasm32-wasip2)
- PyPI publishing configured for ignition-lsp
- VS Code Marketplace publishing configured (publisher: WhiskeyHouse)
- Remaining: full documentation, additional API modules (10+ more exist in Ignition)
