# Changelog

All notable changes to ignition-nvim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Zed extension** (`packages/ignition-zed/`) — Rust/WebAssembly extension registering
  `ignition-lsp` for Python and JSON inside Ignition projects:
  - Completions, hover docs, go-to-definition, diagnostics, and workspace symbols
  - Auto-installs the language server into a managed virtualenv on first use
  - Attaches only to worktrees with a root `project.json`, leaving unrelated projects alone
  - Settings passthrough via `lsp.ignition-lsp.settings` (accepts the Neovim settings shape)
- **LSP code actions for embedded scripts** — decode/encode is now available to any
  standard LSP client, not just editors with a virtual-document API:
  - `textDocument/codeAction` offers "Ignition: Decode …" on JSON resource lines and
    "Ignition: Save … back to JSON" on decoded files
  - New `ignition.decodeScriptToFile` and `ignition.saveScriptToSource` commands
  - Decoded scripts are written to `.ignition-scripts/` with a metadata header
    recording their source URI, key, line, indentation, and a digest of the
    encoded script
  - Saves are validated before they write: the sidecar must sit where its own
    header says, the source must resolve inside the owning project, and the
    digest must still match the script at that line, so a stale sidecar cannot
    overwrite a script that has since moved into its position

- **Ignition System API completions** — 14 modules with 239+ functions:
  - `system.tag` — Tag operations (read, write, browse)
  - `system.db` — Database queries and transactions
  - `system.perspective` — Perspective session and component control
  - `system.util` — Utility functions (timers, threading, exports)
  - `system.alarm` — Alarm management
  - `system.dataset` — Dataset manipulation
  - `system.date` — Date/time functions
  - `system.file` — File I/O operations
  - `system.gui` — GUI interactions (client scope)
  - `system.nav` — Navigation functions
  - `system.net` — HTTP requests and email
  - `system.opc` — OPC operations
  - `system.security` — Authentication and authorization
  - `system.user` — User management
- **Java API completions** — 27 modules with comprehensive Java/Jython support:
  - Standard Java libraries (java.lang, java.util, java.io, java.math, java.nio, etc.)
  - Java GUI frameworks (java.awt, javax.swing, and related packages)
  - Java networking and security (java.net, java.security, javax.crypto, javax.net.ssl)
  - Java SQL and database (java.sql, javax.servlet)
  - Java time and text processing (java.time, java.text, java.util.regex)
  - Ignition SDK modules (com.inductiveautomation.common, com.inductiveautomation.gateway)
  - Context-aware Java import and class member completions
- **JSON schema completions for Perspective** — Context-aware completions for view.json files:
  - Component type completions (ia.container.*, ia.display.*, ia.input.*, ia.chart.*)
  - Structural keys (root, custom, meta, propConfig, position, events)
  - Props and event handlers specific to component types
  - Smart detection of Perspective JSON files
- **Project script completions** — Full support for project-level scripting:
  - `project.*` module completions for project scripts
  - `shared.*` module completions for shared scripts
  - Inherited project modules from parent projects
  - Cross-file script navigation and indexing
- Project indexing and workspace symbols for cross-file navigation
- Go-to-definition for `system.*` functions, Java classes, and project scripts
- Kindling integration for `.gwbk` file support
- Comprehensive test suite:
  - 162 Python tests across 7 test files
  - 107 Lua tests across 7 spec files
- lazy.nvim plugin spec with automatic LSP installation
- CI/CD pipeline (GitHub Actions):
  - Automated testing on Neovim stable + nightly
  - Python test matrix (3.9, 3.11, 3.13)
  - Linting and type checking
  - PyPI publishing workflows (beta and release)
- Deploy-docs workflow for Docusaurus documentation site
- Comprehensive documentation:
  - Docusaurus user guide
  - Vim help files (`:help ignition-nvim`)
  - CONTRIBUTING.md with developer guidelines
  - TROUBLESHOOTING.md with common issues and solutions
  - CHANGELOG.md (this file)

### Changed
- Migrated LSP client to `vim.lsp.start()` (Neovim 0.11+ native API)
  - No longer requires nvim-lspconfig
  - Simpler, more reliable auto-start
- Updated to pygls 2.0 for LSP server
  - Better async handling
  - Improved protocol compliance
- Improved encoding round-trip fidelity
  - Uses plain string replacement (not Lua patterns)
  - Matches Ignition Flint behavior exactly
  - Comprehensive round-trip tests

### Fixed
- Saving an embedded script with no edits no longer fails with "Key not found".
  The missing-key check now tests for the key itself rather than inferring it from
  an unchanged line, so a genuine no-op save succeeds. Affects `ignition/saveScript`
  in all editors.
- LSP auto-start with FileType autocmd
  - Prevents race conditions
  - Reliable attachment on buffer open
- Prevent duplicate LSP client instances
  - Checks for existing clients before starting
  - Avoids multiple hover/completion sources
- Lua pattern vs plain string replacement bug in encoding
  - Now uses `string.gsub` with plain flag
  - Fixes special character handling
- Include `java_db` in PyPI package
  - Was missing from package manifest
  - Now properly included in distributions

## [0.1.0] - 2025-10-27

### Added
- Initial release
- File type detection for Ignition files (`.gwbk`, `.proj`, `resource.json`, etc.)
- Script decode/encode workflow using Ignition Flint format
  - Standard JSON string escaping
  - Unicode escapes for special characters
  - NOT base64 — scripts remain partially readable
- Virtual buffer system with `acwrite` and auto-save
  - Edit decoded scripts in virtual buffers
  - Auto-encode on save
  - Preserves source JSON location
- LSP server foundation with pygls
  - Basic server structure
  - Document synchronization
  - Request routing
- Diagnostics integration with ignition-lint
  - Syntax errors
  - Hardcoded localhost warnings
  - Print statement detection
  - HTTP error handling checks
- Interactive script selection for multi-script files
  - Preview window with syntax highlighting
  - Navigate with j/k, select with Enter
  - Decode all scripts at once with `:IgnitionDecodeAll`
- Auto-detection of embedded scripts in JSON
  - Scans for script-like keys: `script`, `code`, `transform`, `onActionPerformed`, etc.
  - Handles nested objects and arrays
  - Supports deeply nested structures
- Commands:
  - `:IgnitionDecode` — Decode scripts (interactive selection)
  - `:IgnitionDecodeAll` — Decode all scripts
  - `:IgnitionEncode` — Encode script back to JSON
  - `:IgnitionListScripts` — Show all scripts in floating window
  - `:IgnitionOpenKindling [file]` — Open in Kindling
  - `:IgnitionInfo` — Show plugin information
- Default keymaps for Ignition files:
  - `<localleader>id` — Decode scripts
  - `<localleader>ia` — Decode all scripts
  - `<localleader>il` — List all scripts
  - `<localleader>ie` — Encode script
  - `<localleader>ii` — Plugin info
  - `<localleader>ik` — Open in Kindling
- Configuration system with sensible defaults
  - LSP settings (enabled, auto_start, cmd, version)
  - Kindling integration (enabled, path)
  - Decoder behavior (auto_decode, auto_encode)
  - UI preferences (notifications, statusline)
  - Keymap control (enabled/disabled)
- Basic documentation
  - README with features, installation, usage
  - Code comments and docstrings
  - Example configuration

[unreleased]: https://github.com/whiskeyhouse/ignition-nvim/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/whiskeyhouse/ignition-nvim/releases/tag/v0.1.0
