---
sidebar_position: 1
---

# Claude Code Plugin

A Claude Code plugin that gives Claude full domain awareness when working on Ignition SCADA projects. Claude automatically understands the `system.*` API, the expression language, project structure conventions, and how to scaffold and run tests — without you having to explain any of it.

## What It Does

The plugin provides 8 skills (4 Claude-only background knowledge, 4 user-invocable commands) plus auto-linting and auto-testing hooks.

| Feature | Description |
|---------|-------------|
| **Auto-lint hook** | Runs `ignition-lint` after every Write/Edit on `.py`, `view.json`, and `tags.json` files. Diagnostics feed back to Claude, which fixes issues immediately. |
| **API reference** | Claude knows every `system.*` function — completions, conventions, anti-patterns — without you explaining the API. |
| **Expression language** | Claude understands Ignition's expression syntax (NOT Python) and all 104 built-in functions. |
| **Manual lint** | `/ignition-scada:ignition-lint` — lint specific files or the whole project on demand. |
| **Test scaffolding** | `/ignition-scada:init-testing` scaffolds a Jython test framework. `/ignition-scada:init-e2e` adds Playwright browser tests. |
| **Test runner** | `/ignition-scada:test` runs gateway Jython tests or Playwright browser tests with smart routing. |
| **Auto-test hooks** | After `git commit`, runs gateway tests. After editing a `view.json`, runs scoped Playwright tests. |

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

The detection scripts also require `jq` for JSON parsing (pre-installed on most systems).

## How Auto-Linting Works

After every Write or Edit, the hook checks if the file is inside an Ignition project (walks up from the file looking for `project.json`). If it is:

- `.py` files are linted with the `scripts-only` profile
- `view.json` files are linted with the `perspective-only` profile
- `tags.json` files are linted with the `full` profile

Any issues are returned as structured JSON, which Claude reads and acts on — typically fixing the issue in its next edit.

Files outside Ignition projects are ignored. The hook is safe for global install.

## Claude-Only Skills

Four skills provide background knowledge that Claude draws on automatically. They never appear in the `/` menu — they are loaded when relevant.

### ignition-api

Gives Claude complete knowledge of Ignition's scripting API:
- All 14 `system.*` modules (239 functions) with signatures and conventions
- Jython 2.7 rules (no f-strings, no type hints, `print()` function form)
- `resource.json` structure — every file in an Ignition project needs one
- Script library structure (leaf modules vs package nodes)
- Common patterns and anti-patterns

### ignition-expressions

Teaches Claude the Ignition expression language:
- All 104 built-in functions across 10 categories (math, string, date/time, logic, type casting, dataset, JSON, tag quality, color, advanced)
- Property reference syntax (`{this.props.value}`, `{view.custom.x}`)
- Key rules like `now()` polling rates and `runScript()` syntax

### ignition-testing

Provides the complete Jython test framework reference:
- `testing.*` modules (runner, assertions, decorators, helpers, reporter)
- Test discovery conventions (`__tests__/code.py` inside each package)
- WebDev endpoint API (`testing/run`, `testing/tags`)
- Project inheritance rules

### ignition-e2e

Teaches Claude how Perspective works in the browser:
- Perspective DOM conventions (`data-component-path`, `data-component`)
- PerspectivePage page object and component wrappers
- Gateway API helper for tag operations from test code
- Auth setup and session persistence

## User-Invocable Skills

Four skills are available from the `/` menu:

| Skill | Usage |
|-------|-------|
| `/ignition-scada:ignition-lint` | Lint files or the whole project |
| `/ignition-scada:init-testing` | Scaffold Jython test framework |
| `/ignition-scada:init-e2e` | Scaffold Playwright browser tests |
| `/ignition-scada:test` | Run gateway or browser tests |

See the [Skills Reference](skills-reference) for detailed usage of each.

## Plugin vs Templates

This repo offers two ways to give Claude Ignition awareness:

| | Plugin (`claude-code-plugin/`) | Templates (`templates/`) |
|--|------|-----------|
| **Scope** | Global — works across all your Ignition projects | Per-project — files live in your project repo |
| **Install** | `claude plugin add` once | Copy files or run `setup.sh` per project |
| **Updates** | `claude plugin update` | Re-run setup or manually copy |
| **Best for** | Developers who work on multiple Ignition projects | Teams who want the config checked into their project |

Both approaches include the same lint hook and the same domain knowledge. The plugin packages it as a reusable install; the templates embed it directly.
