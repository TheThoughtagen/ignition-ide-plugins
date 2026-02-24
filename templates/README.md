# Ignition Claude Code Templates

Drop-in files that give Claude Code full Ignition SCADA awareness inside your project. Includes a `CLAUDE.md` with the complete API reference and expression language, plus a hook that auto-runs `ignition-lint` after every file edit.

## Quick Start

From your Ignition project root (the directory with `project.json`):

```bash
curl -sL https://raw.githubusercontent.com/whiskeyhouse/ignition-nvim/main/templates/setup.sh | bash
```

Or from a local clone of this repo:

```bash
bash /path/to/ignition-nvim/templates/setup.sh
```

## What Gets Installed

```
your-ignition-project/
  CLAUDE.md                        # API reference, expressions, conventions
  .claude/
    settings.json                  # Hook configuration
    hooks/
      ignition-lint.sh             # Auto-lint on Write/Edit
```

### CLAUDE.md

A project-level instruction file that Claude reads automatically. Contains:

- **Ignition project structure** — where views, scripts, and tags live
- **Jython conventions** — Python 2.7 on JVM, key differences from Python 3
- **System API reference** — all 14 modules, 239 functions with signatures
- **Expression language** — all 104 functions by category
- **Common patterns** — tag reads, parameterized queries, dataset iteration, logging
- **Anti-patterns** — SQL injection, shadowing `system`, hardcoded URLs, `import *`
- **ignition-lint usage** — profiles, diagnostic codes, inline suppression

### Auto-Lint Hook

The `.claude/settings.json` configures a PostToolUse hook that fires after every Write or Edit:

- `.py` files → `ignition-lint --profile scripts-only`
- `view.json` files → `ignition-lint --profile perspective-only`
- `tags.json` files → `ignition-lint --profile full`

Diagnostics are fed back to Claude as structured JSON. Claude sees the issues and fixes them in its next edit — no manual lint runs needed.

If `ignition-lint` is not installed, the hook silently exits.

## Prerequisites

```bash
pip install ignition-lint-toolkit
```

The templates work without the linter installed — Claude still gets the full API reference from `CLAUDE.md`. The lint hook activates once the linter is available.

## Templates vs Plugin

This repo also ships a [Claude Code plugin](../claude-code-plugin/) for the same purpose:

| | Templates (this directory) | Plugin (`claude-code-plugin/`) |
|--|-----------|------|
| **Scope** | Per-project — files live in your repo | Global — works across all projects |
| **Install** | `setup.sh` or manual copy | `claude plugin add` |
| **Team sharing** | Check `.claude/` into your repo | Each developer installs the plugin |
| **Customization** | Edit `CLAUDE.md` directly | Plugin files are managed externally |
| **Best for** | Teams, CI pipelines, project-specific rules | Solo developers, multiple projects |

## Updating

Re-run the setup script. Existing files are backed up to `.bak` before overwriting:

```bash
bash /path/to/ignition-nvim/templates/setup.sh
```

## File Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project instructions — API reference, expressions, conventions, anti-patterns |
| `.claude/settings.json` | Hook configuration — triggers lint on Write/Edit |
| `.claude/hooks/ignition-lint.sh` | Hook script — routes files to appropriate lint profiles |
| `setup.sh` | Installer — copies files, checks for ignition-lint |
