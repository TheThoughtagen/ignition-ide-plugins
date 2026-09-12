---
sidebar_position: 3
---

# LSP Features

ignition-nvim includes a comprehensive Language Server Protocol (LSP) implementation providing intelligent code completion, documentation, navigation, and validation for Ignition development.

## Overview

The LSP server provides four major feature areas:

### 🎯 [System API Completions](lsp/system-apis.md)

Complete IDE support for all Ignition `system.*` modules — 14 modules with 239+ functions.

- Tag operations (`system.tag.*`)
- Database queries (`system.db.*`)
- Perspective messaging (`system.perspective.*`)
- Date/time utilities (`system.date.*`)
- And 10 more modules

**[Read detailed guide →](lsp/system-apis.md)**

### ☕ [Java & Jython Support](lsp/java-jython.md)

Full type-aware completions for Java/Jython development — 26 packages with 146 classes.

- Standard Java libraries (`java.util`, `java.io`, `java.net`)
- GUI frameworks (`javax.swing`, `java.awt`)
- Database connectivity (`java.sql`)
- Ignition SDK (`com.inductiveautomation.*`)

**[Read detailed guide →](lsp/java-jython.md)**

### 📦 [Project Script Completions](lsp/project-scripts.md)

Intelligent completions for your project's custom scripts.

- Cross-file completions for `project.*` and `shared.*`
- Function and class member completions
- Go-to-definition across your entire project
- Workspace symbol search

**[Read detailed guide →](lsp/project-scripts.md)**

### 📐 [Perspective JSON Support](lsp/perspective-json.md)

Schema-aware completions for Perspective view.json files.

- Component type completions (all `ia.*` components)
- Property completions per component type
- Event handler completions
- Binding type completions
- Style property completions

**[Read detailed guide →](lsp/perspective-json.md)**

## Core Features

### Completions

Context-aware autocompletion triggered by `.` for:
- **System APIs** - All `system.*` functions with signatures
- **Java classes** - Methods, fields, and constructors
- **Project scripts** - Functions and classes from your project
- **Perspective** - Component types, props, events, bindings

Completions include:
- Full signatures with parameter names and types
- Brief descriptions
- Return type information
- Deprecation warnings
- Scope information (client/gateway/designer)

### Hover Documentation

Press `K` (or your configured hover key) over any symbol to see:
- Complete function/method signature
- Detailed description with examples
- Parameter documentation
- Return value information
- Links to official documentation

Works for:
- `system.*` API functions
- Java class methods and fields
- Project script functions and classes
- Perspective component properties

### Go-to-Definition

Jump to definition with `gd` (or your configured key):
- **System APIs** - Jump to API definition in the database
- **Java classes** - Navigate to class/method definitions
- **Project scripts** - Jump to function/class implementation across files
- **Cross-file references** - Follow imports and references

### Diagnostics

Real-time error and warning detection:
- **Syntax errors** - Python syntax validation via [ignition-lint](https://github.com/ia-eknorr/ignition-lint)
- **Type errors** - Basic type checking for Jython
- **Import errors** - Detect missing or invalid imports
- **Perspective schema** - Validate view.json against component schemas

Diagnostics appear inline in the editor with:
- Error messages and locations
- Suggested fixes (when available)
- Severity levels (error, warning, info)

### Workspace Symbols

Search for symbols across your entire project:
```
:LspWorkspaceSymbols validate
```

Results include:
- Functions and classes from project scripts
- System API functions
- Java class methods
- Locations in file paths

## LSP Configuration

### Auto-Start

The LSP starts automatically when you open any Python file in an Ignition project. To disable:

```lua
require('ignition').setup({
  lsp = {
    auto_start = false,  -- Manual start only
  }
})
```

### Manual Control

Start/stop the LSP manually:
```
:LspStart ignition-lsp
:LspStop
:LspRestart
```

### Check Status

View LSP status and configuration:
```
:IgnitionInfo
:LspInfo
```

### Server Settings

Configure Ignition version and other settings:

```lua
require('ignition').setup({
  lsp = {
    settings = {
      ignition = {
        version = "8.1",  -- Your Ignition version
      },
    },
  },
})
```

## Performance

The LSP is optimized for large Ignition projects:

- **Lazy loading** - API definitions loaded on-demand
- **Incremental updates** - Only rescans modified files
- **Symbol caching** - In-memory cache for fast lookups
- **Async operations** - Non-blocking background work
- **Efficient indexing** - Optimized project scanning

## Troubleshooting

### LSP Not Starting

1. Check if the LSP is installed:
   ```bash
   which ignition-lsp
   # or
   python -m ignition_lsp --version
   ```

2. Check for errors:
   ```
   :LspLog
   ```

3. Restart the LSP:
   ```
   :LspRestart
   ```

### No Completions

1. Verify the LSP is running:
   ```
   :LspInfo  # Should show ignition-lsp as active
   ```

2. Check file type:
   ```
   :set filetype?  # Should be 'python' or 'json'
   ```

3. Trigger manually:
   - Press `Ctrl-X Ctrl-O` for omnifunc completion
   - Or use your completion plugin's manual trigger

### Slow Completions

Large projects may take time to index. Check progress:
```
:IgnitionInfo  # See "Project index: X scripts"
```

To improve performance:
- Exclude large non-Ignition directories from workspace
- Reduce project size by splitting into multiple repos

### Outdated Completions

Force a full rescan:
```
:LspRestart
```

Or rebuild the project index by saving any project script file.

## Related Guides

- **[Commands & Keymaps](commands.md)** - All available commands
- **[Script Editing](script-editing.md)** - Decode/encode workflow
- **[Configuration](../configuration/options.md)** - Full configuration options

## Further Reading

For detailed examples and use cases, see the specific feature guides:
- [System API Completions](lsp/system-apis.md)
- [Java & Jython Support](lsp/java-jython.md)
- [Project Script Completions](lsp/project-scripts.md)
- [Perspective JSON Support](lsp/perspective-json.md)
