---
sidebar_position: 1
slug: /
---

# Introduction

**Ignition Dev Tools** is a multi-editor monorepo providing full IDE support for [Ignition by Inductive Automation](https://inductiveautomation.com/). It brings first-class development tooling to Neovim, VS Code, and Claude Code — covering everything from LSP completions to automated test scaffolding.

Part of the **Whiskey House Ignition Developer Toolkit**:
- **Ignition Dev Tools** — IDE support for Neovim, VS Code, and Claude Code (this project)
- [**ignition-lint**](https://pypi.org/project/ignition-lint-toolkit/) — Static analysis for Ignition Python scripts
- **ignition-git-module** — Native Git integration inside Ignition Designer

## The Problem

Developing Ignition projects outside the Designer is painful:

- **No IDE support** — Generic Python editors don't understand Ignition's `system.*` APIs, Java/Jython interop, or project structure
- **No type awareness** — Jython's dynamic typing combined with Java imports means zero autocomplete in most editors
- **No schema validation** — Tag JSON and Perspective component definitions have strict schemas that generic editors can't validate
- **Embedded scripts** — Python code is stored inside JSON files using Ignition's custom encoding format, making editing tedious
- **Limited tooling** — The Designer's built-in editor lacks modern IDE features (LSP, plugins, advanced motions)
- **No testing** — No standard framework for unit testing Jython scripts or browser-testing Perspective views

## The Solution

Ignition Dev Tools brings modern IDE capabilities to Ignition development across three editors:

- **Full LSP integration** — Context-aware completions for all `system.*` APIs (239+ functions), Java/Jython classes (146 classes), and project scripts
- **Intelligent decode/encode** — Seamlessly edit embedded Python scripts with full syntax highlighting and LSP support, auto-encoded on save
- **Type-aware completions** — Understands Jython's Java interop, providing accurate completions for `java.util.*`, `javax.swing.*`, and Ignition SDK classes
- **Project navigation** — Workspace symbols, go-to-definition, and cross-file script references
- **Diagnostics** — Catch errors in your scripts before deploying to the gateway
- **Claude Code plugin** — Auto-linting, API reference skills, and automated test scaffolding for Jython gateway tests and Playwright browser tests

## Architecture

The project is organized as a monorepo with three packages:

```
packages/
├── ignition-lsp/        # Python LSP server (shared by both editors)
├── ignition-nvim/       # Neovim plugin (Lua)
└── ignition-vscode/     # VS Code extension (TypeScript)
```

### Shared LSP Server (`packages/ignition-lsp/`)

A Python language server built on [pygls](https://github.com/openlawlibrary/pygls), providing completions, hover documentation, diagnostics, go-to-definition, and workspace symbols. Both editors use the same server, so all language features are consistent.

- 14 API modules covering 239 `system.*` functions
- 26 Java packages with 146 classes for Jython interop
- Pyright/Pylance type stubs for static analysis

### Neovim Plugin (`packages/ignition-nvim/`)

Lua plugin using Neovim 0.11+ native LSP (`vim.lsp.start()`). Provides script decode/encode, virtual buffers, Kindling integration for `.gwbk` files, and file type detection.

### VS Code Extension (`packages/ignition-vscode/`)

TypeScript extension with CodeLens for embedded scripts, a Designer-style project browser sidebar, tag browser, component tree, and one-click decode/encode.

### Claude Code Plugin (`claude-code-plugin/`)

A Claude Code plugin that gives Claude full Ignition domain awareness. Includes auto-linting, the complete `system.*` API reference, expression language catalog, and automated test scaffolding for both Jython gateway tests and Playwright browser tests.

## Next Steps

- **Neovim** — [Install the plugin](getting-started/installation) and LSP server
- **Neovim** — [Try the quickstart](getting-started/quickstart) to decode your first script
- **Claude Code** — [Set up the plugin](claude-code-plugin/overview) for auto-linting and testing
- **Claude Code** — [Scaffold tests](claude-code-plugin/testing) for your Ignition project
