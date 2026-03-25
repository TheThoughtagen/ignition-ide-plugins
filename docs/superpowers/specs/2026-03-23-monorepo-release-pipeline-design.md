# Monorepo Release Pipeline Design

## Overview

Release pipeline redesign for the ignition-nvim monorepo to support independent releases of three packages (Neovim plugin, Python LSP server, VS Code extension) with full CD to the VS Code Marketplace.

## Decision Record

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tag strategy | Hybrid — unified tags for nvim+LSP, prefixed `vscode/v*` for VS Code | Neovim plugin and LSP are tightly coupled (plugin installs LSP); VS Code extension has its own marketplace lifecycle |
| VS Code publishing | Full automation via `vsce publish` in CI | Do it right from the start — manual uploads don't scale |
| VS Code CI testing | Gate releases on tests (`npm test` → `vitest run`) | Matches existing test-gating for Lua and Python packages |
| VS Code pre-releases | Tag format detection (`-beta.*`/`-rc.*` suffix) with marketplace `--pre-release` flag | Single tag namespace, no separate workflow file |

## Architecture

### Workflow Files

| File | Trigger | Guard | Purpose |
|------|---------|-------|---------|
| `ci.yml` | push/PR to main, `workflow_call` | — | Lua tests + Python tests + VS Code build+test |
| `release.yml` | `v[0-9]+.[0-9]+.[0-9]+` tags | `if: !startsWith(github.ref_name, 'vscode/')` | LSP → PyPI, Neovim archive → GitHub Release |
| `beta.yml` | `v*-beta.*`, `v*-rc.*` tags | `if: !startsWith(github.ref_name, 'vscode/')` | LSP → TestPyPI, Neovim archive → GitHub Pre-release |
| `release-vscode.yml` (new) | `vscode/v*` tags | — | VS Code extension → Marketplace + GitHub Release |

### Tag Namespaces

Explicit `if` guards on `release.yml` and `beta.yml` prevent VS Code tags from triggering the wrong pipelines. GitHub Actions tag glob matching does not treat `/` as a path boundary, so `v*-beta.*` could match `vscode/v0.2.0-beta.1` without the guard.

- **Neovim + LSP stable:** `v1.3.0`
- **Neovim + LSP beta:** `v1.3.0-beta.1`, `v1.3.0-rc.1`
- **VS Code stable:** `vscode/v0.2.0`
- **VS Code pre-release:** `vscode/v0.2.0-beta.1`, `vscode/v0.2.0-rc.1`

### Release Flow: VS Code Extension

```
git tag vscode/v0.2.0
git push origin vscode/v0.2.0
         │
         ▼
   ┌─────────────┐
   │   ci.yml     │  All tests (Lua + Python + VS Code)
   └──────┬──────┘
          │ pass
          ▼
   ┌─────────────┐
   │    build     │  npm ci → vsce package (runs tsc via prepublish) → upload .vsix
   └──────┬──────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐ ┌──────────────┐
│ GitHub │ │  Marketplace  │  vsce publish (+ --pre-release if beta/rc tag)
│Release │ │   publish     │
└────────┘ └──────────────┘
```

## Changes

### 1. `ci.yml` — Add VS Code test job

New `vscode-tests` job alongside existing `lua-tests` and `python-tests`:

```yaml
vscode-tests:
  name: VS Code Extension Tests
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'
        cache-dependency-path: packages/ignition-vscode/package-lock.json
    - run: cd packages/ignition-vscode && npm ci
    - run: cd packages/ignition-vscode && npm run compile
    - run: cd packages/ignition-vscode && npm test
```

### 2. `release-vscode.yml` — New workflow

Single workflow handling both stable and pre-release VS Code extension publishing:

- **Trigger:** `vscode/v*` tags
- **Concurrency:** `vscode-release` group, never cancel in-progress releases
- **CI gate:** Calls `ci.yml` (reusable workflow)
- **Build job:**
  - Extracts version from tag, detects pre-release via `-beta`/`-rc` suffix
  - Sets version in `package.json` via `npm version --no-git-tag-version`
  - Runs `npm ci` then `npx @vscode/vsce package` (which triggers `vscode:prepublish` → `tsc` automatically, no need for explicit compile)
  - Uploads `.vsix` artifact (named `ignition-dev-tools-{version}.vsix` by convention)
- **Publish job:**
  - Downloads `.vsix` artifact
  - Runs `npx @vscode/vsce publish` with `--pre-release` flag if applicable
  - Uses `VSCE_PAT` secret for authentication
- **GitHub Release job:**
  - Requires `permissions: contents: write`
  - Creates release (or pre-release) with `.vsix` attached
  - Auto-generates release notes

### 3. Existing workflows — Add tag collision guards

Add `if: "!startsWith(github.ref_name, 'vscode/')"` to the first job in both `release.yml` and `beta.yml`. Since all downstream jobs use `needs:`, the guard on the first job (`ci`) is sufficient to block the entire pipeline.

### 4. Plugin archive fix (pre-existing)

The `plugin-archive` job in `release.yml` and `beta.yml` is missing `doc/` (Vim help files) and `queries/` (treesitter queries) from the archive. Add them to the `cp -r` line.

## Prerequisites (One-Time Setup)

1. **Create VS Code Marketplace publisher** at https://marketplace.visualstudio.com/manage with ID `whiskeyhouse`
2. **Generate Azure DevOps PAT** with `Marketplace > Manage` scope
3. **Add `VSCE_PAT` secret** to GitHub repo (Settings → Secrets → Actions)
4. **Generate `package-lock.json`** in `packages/ignition-vscode/` if not present (`npm install`)

## Secrets Required

| Secret | Where | Purpose |
|--------|-------|---------|
| `VSCE_PAT` | GitHub Actions secrets | VS Code Marketplace publishing |
| (existing) PyPI trusted publishing | GitHub environment `pypi` | LSP publishing (unchanged) |
| (existing) TestPyPI trusted publishing | GitHub environment `testpypi` | LSP beta publishing (unchanged) |
