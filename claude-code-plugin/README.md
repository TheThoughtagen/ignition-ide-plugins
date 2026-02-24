# Ignition SCADA — Claude Code Plugin

A Claude Code plugin that gives Claude full domain awareness when working on Ignition SCADA projects. Includes auto-linting, the complete `system.*` API reference (14 modules, 239 functions), and the expression language catalog (104 functions).

## What It Does

| Feature | Description |
|---------|-------------|
| **Auto-lint hook** | Runs `ignition-lint` after every Write/Edit on `.py`, `view.json`, and `tags.json` files. Diagnostics are fed back to Claude so it fixes issues immediately. |
| **API reference** | Claude knows every `system.*` function — completions, conventions, anti-patterns — without you having to explain the API. |
| **Expression language** | Claude understands Ignition's expression syntax (NOT Python) and all 104 built-in functions. |
| **Manual lint skill** | Run `/ignition-scada:ignition-lint` to lint specific files or the whole project on demand. |

## Install

```bash
claude plugin add --from whiskeyhouse/ignition-nvim --path claude-code-plugin
```

Or from a local clone:

```bash
claude plugin add --from /path/to/ignition-nvim/claude-code-plugin
```

## Prerequisites

The auto-lint hook requires [`ignition-lint`](https://pypi.org/project/ignition-lint-toolkit/):

```bash
pip install ignition-lint-toolkit
```

If `ignition-lint` is not installed, the hook silently exits — nothing breaks.

The hook also requires `jq` for JSON parsing (pre-installed on most systems).

## How It Works

### Auto-Lint Hook

After every Write or Edit, the hook checks if the file is inside an Ignition project (walks up from the file looking for `project.json`). If it is:

- `.py` files are linted with the `scripts-only` profile
- `view.json` files are linted with the `perspective-only` profile
- `tags.json` files are linted with the `full` profile

Any issues are returned as structured JSON, which Claude reads and acts on — typically fixing the issue in its next edit.

Files outside Ignition projects are ignored. The hook is safe for global install.

### Skills

Three skills are bundled:

| Skill | Invocable? | Purpose |
|-------|-----------|---------|
| `ignition-api` | Claude-only | Loaded automatically when Claude writes Ignition scripts. Provides Jython conventions, all `system.*` modules, common patterns, and anti-patterns. |
| `ignition-expressions` | Claude-only | Loaded automatically when Claude writes expression bindings. All 104 functions with signatures, descriptions, and usage tips. |
| `ignition-lint` | User + Claude | Run `/ignition-scada:ignition-lint` to lint files or the project. Claude explains diagnostics and applies fixes. |

Claude-only skills are never shown in the `/` menu — they're background knowledge that Claude draws on when relevant.

## Plugin vs Templates

This repo offers two ways to give Claude Ignition awareness:

| | Plugin (`claude-code-plugin/`) | Templates (`templates/`) |
|--|------|-----------|
| **Scope** | Global — works across all your Ignition projects | Per-project — files live in your project repo |
| **Install** | `claude plugin add` once | Copy files or run `setup.sh` per project |
| **Updates** | `claude plugin update` | Re-run setup or manually copy |
| **Best for** | Developers who work on multiple Ignition projects | Teams who want the config checked into their project |

Both approaches include the same lint hook and the same domain knowledge. The plugin packages it as a reusable install; the templates embed it directly.

## File Structure

```
claude-code-plugin/
  .claude-plugin/
    plugin.json           # Plugin manifest (name, version, entry points)
  hooks/
    hooks.json            # PostToolUse hook config (Write|Edit matcher)
  scripts/
    ignition-lint.sh      # Lint hook script (finds project.json, runs linter)
  skills/
    ignition-api/
      SKILL.md            # system.* API reference (Claude-only)
    ignition-expressions/
      SKILL.md            # Expression language reference (Claude-only)
    ignition-lint/
      SKILL.md            # Manual lint skill (user-invocable)
```

## Diagnostic Codes

The hook and lint skill report issues using these codes. See the [ignition-lint docs](https://pypi.org/project/ignition-lint-toolkit/) for full details.

**Script:** `JYTHON_SYNTAX_ERROR`, `JYTHON_PRINT_STATEMENT`, `JYTHON_IMPORT_STAR`, `IGNITION_UNKNOWN_SYSTEM_CALL`, `IGNITION_SYSTEM_OVERRIDE`, `LONG_LINE`, `MISSING_DOCSTRING`

**Expression:** `EXPR_NOW_DEFAULT_POLLING`, `EXPR_NOW_LOW_POLLING`, `EXPR_UNKNOWN_FUNCTION`, `EXPR_BAD_COMPONENT_REF`

**Perspective:** `EMPTY_COMPONENT_NAME`, `GENERIC_COMPONENT_NAME`, `MISSING_TAG_PATH`, `MISSING_EXPRESSION`, `INVALID_BINDING_TYPE`

**Tag:** `INVALID_TAG_TYPE`, `MISSING_DATA_TYPE`, `MISSING_VALUE_SOURCE`, `OPC_MISSING_CONFIG`
