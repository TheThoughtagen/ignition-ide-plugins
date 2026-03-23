# CLAUDE.md — ignition-nvim

## Project Overview

**ignition-nvim** is a Neovim plugin for Inductive Automation's Ignition SCADA platform. It provides full IDE support — LSP completions, hover docs, diagnostics, script decode/encode, and virtual buffers — for editing Ignition projects in Neovim.

Part of the **Whiskey House Ignition Developer Toolkit** (three repos):
- **ignition-nvim** — Neovim IDE support (this repo)
- **ignition-lint** — Static analysis for Ignition Python scripts (sibling `../ignition-lint/`)
- **ignition-git-module** — Native Git inside Ignition Designer

## Architecture

Hybrid **Lua + Python** project:

### Lua Plugin (`lua/ignition/`)
Core Neovim plugin loaded at runtime.

| Module | Responsibility |
|--------|---------------|
| `init.lua` | Entry point, `setup(opts)`, initializes subsystems |
| `config.lua` | Configuration schema, validation, defaults |
| `encoding.lua` | Encode/decode scripts (Ignition Flint format) |
| `json_parser.lua` | Find embedded scripts in JSON by key names |
| `decoder.lua` | Decode workflow: interactive selection, decode all, list scripts |
| `virtual_doc.lua` | Virtual buffer system: `acwrite` buffers, auto-save, source tracking |
| `lsp.lua` | LSP client via `vim.lsp.start()` (Neovim 0.11+) |
| `kindling.lua` | Integration with Kindling for `.gwbk` files |

### Python LSP Server (`lsp/ignition_lsp/`)
pygls 2.0 language server providing code intelligence.

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
| `api_db/*.json` | 14 modules, 239 functions — follows `api_db/schema.json` |

### Supporting Files
- `lazy.lua` — lazy.nvim plugin spec (ft/cmd lazy-loading, auto LSP install)
- `ftdetect/` — Filetype detection
- `ftplugin/` — Filetype-specific settings
- `syntax/` — Syntax highlighting
- `plugin/` — Plugin autoload
- `doc/` — Vim help files
- `website/` — Docusaurus documentation site

## Domain Context

**Ignition** is a SCADA/ICS platform by Inductive Automation. Projects are stored as JSON files containing embedded Python (Jython) scripts. Developers use `system.*` scripting APIs (e.g., `system.tag.readBlocking()`, `system.db.runPrepQuery()`, `system.perspective.sendMessage()`).

This plugin decodes those embedded scripts into editable Python buffers with full LSP support, then encodes them back.

## Critical Technical Details

### Encoding (HANDLE WITH EXTREME CARE)
- Uses **Ignition Flint format** — plain string replacement, NOT base64
- Standard JSON escapes: `\"`, `\n`, `\t`, `\b`, `\r`, `\f`
- Unicode escapes: `<` → `\u003c`, `>` → `\u003e`, `&` → `\u0026`, `=` → `\u003d`, `'` → `\u0027`
- **Order matters:** backslash first to avoid double-escaping
- **Round-trip fidelity is sacred:** `encode(decode(x)) == x` must always hold
- Lua encoding uses `string.gsub` with **plain flag** — NOT Lua patterns (this caused bugs)

### LSP Client
- Uses `vim.lsp.start()` — modern Neovim 0.11+ API, NOT lspconfig
- Python venv at `lsp/venv/` (Python 3.13)

### Virtual Buffers
- Use `acwrite` buftype with `BufWriteCmd` autocmd
- Saving a virtual buffer encodes the script back into the source JSON

## Build / Test / Lint Commands

### Python LSP Setup
```bash
cd lsp && source venv/bin/activate
pip install -e ".[dev]"
```

### Lua Tests (plenary.nvim / busted)
```bash
# All tests (107 tests across 7 spec files)
nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua'}"

# Single file
nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedFile tests/encoding_spec.lua"
```

### Python Tests (pytest)
```bash
# All tests (162 tests across 7 test files)
cd lsp && venv/bin/python -m pytest tests/ -v

# With coverage
cd lsp && venv/bin/python -m pytest tests/ -v --cov=ignition_lsp
```

### Python Linting
```bash
cd lsp && venv/bin/ruff check ignition_lsp/
cd lsp && venv/bin/mypy ignition_lsp/
cd lsp && venv/bin/black --check ignition_lsp/
```

### Lua Linting
```bash
luacheck lua/ --config .luacheckrc
```

## Git Workflow

- **Branch:** Work on `main` (single contributor flow)
- **Commits:** Conventional format — `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) — Lua tests (Neovim stable+nightly), Python tests (3.9/3.11/3.13 matrix)
- **Release pipelines:** `beta.yml`, `release.yml` for PyPI publishing

## API Database

14 modules in `lsp/ignition_lsp/api_db/`:
`system_alarm`, `system_dataset`, `system_date`, `system_db`, `system_file`, `system_gui`, `system_nav`, `system_net`, `system_opc`, `system_perspective`, `system_security`, `system_tag`, `system_user`, `system_util`

All follow `schema.json`. Adding a new module = immediate completions + hover for all users.

## Marketing (gitignored)

`marketing/` is gitignored and contains the Whiskey House marketing strategy:
- `plan.md` — Strategy, target audiences, channels, content mix, messaging pillars, launch sequence
- `calendar.md` — 12-week content calendar (36 posts), Phase 4 topic bank

3 posts/week: ~1 direct project content, ~1 tangential technical, ~1 community/opinion.

---

## Human-in-the-Loop Validation

**IMPORTANT:** Always confirm with the user before taking these actions:

### Always Ask First
- **Encoding changes** — Any modification to `encoding.lua` or encode/decode logic. Round-trip fidelity is the most fragile part of the system. Describe the change and get approval.
- **LSP protocol changes** — Modifications to `server.py` request handlers, new LSP capabilities, or changes to how the client connects. These affect every user's editor experience.
- **API database schema changes** — Modifications to `api_db/schema.json`. All 14 module files depend on it.
- **Breaking config changes** — Anything that changes the `setup(opts)` interface or default behavior.
- **CI/CD pipeline changes** — Modifications to `.github/workflows/*.yml`. These affect releases and publishing.
- **Package metadata** — Changes to `pyproject.toml` version, dependencies, or publish config.
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

## Current State (Feb 2026)

- All 7 priority levels in `fix_plan.md` are complete
- 14 API modules, 239 functions defined
- 162 Python tests + 107 Lua tests — all passing
- Project indexing and go-to-definition implemented
- Kindling integration tested across platforms
- lazy.nvim spec with auto LSP install
- CI pipeline running (GitHub Actions)
- PyPI publishing configured
- Remaining: full documentation, additional API modules (10+ more exist in Ignition)
