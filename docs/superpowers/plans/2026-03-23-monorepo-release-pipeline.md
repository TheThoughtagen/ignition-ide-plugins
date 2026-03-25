# Monorepo Release Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add VS Code extension CI testing and marketplace CD, add tag collision guards to existing workflows, and fix missing files in Neovim plugin archives.

**Architecture:** Four workflow files — `ci.yml` gains a VS Code test job, `release-vscode.yml` is a new workflow for marketplace publishing, `release.yml` and `beta.yml` get tag collision guards and plugin-archive fixes.

**Tech Stack:** GitHub Actions, `@vscode/vsce`, Node.js 20, npm

**Spec:** `docs/superpowers/specs/2026-03-23-monorepo-release-pipeline-design.md`

**Prerequisites (manual, before first VS Code release):**
1. Create VS Code Marketplace publisher at https://marketplace.visualstudio.com/manage with ID `whiskeyhouse`
2. Generate Azure DevOps PAT with `Marketplace > Manage` scope
3. Add `VSCE_PAT` secret to GitHub repo (Settings → Secrets → Actions)

---

### Task 1: Add VS Code test job to CI

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add `vscode-tests` job to `ci.yml`**

Append this job after the existing `python-tests` job:

```yaml
  vscode-tests:
    name: VS Code Extension Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: packages/ignition-vscode/package-lock.json

      - name: Install dependencies
        run: cd packages/ignition-vscode && npm ci

      - name: Compile TypeScript
        run: cd packages/ignition-vscode && npm run compile

      - name: Run tests
        run: cd packages/ignition-vscode && npm test
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
Expected: No output (valid YAML)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add VS Code extension tests to CI pipeline"
```

---

### Task 2: Add tag collision guards to `release.yml`

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Add `if` guard to the `ci` job**

The `ci` job is the first job in the pipeline and all downstream jobs depend on it via `needs: ci`. Adding the guard here blocks the entire pipeline for VS Code tags.

Change the `ci` job from:

```yaml
  ci:
    uses: ./.github/workflows/ci.yml
```

to:

```yaml
  ci:
    if: "!startsWith(github.ref_name, 'vscode/')"
    uses: ./.github/workflows/ci.yml
```

- [ ] **Step 2: Fix plugin-archive to include `doc/` and `queries/`**

In the `plugin-archive` job, change the `cp -r` line from:

```bash
cp -r lua plugin ftdetect ftplugin syntax README.md LICENSE lazy.lua ignition-nvim/
```

to:

```bash
cp -r lua plugin ftdetect ftplugin syntax doc queries README.md LICENSE lazy.lua ignition-nvim/
```

- [ ] **Step 3: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`
Expected: No output (valid YAML)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "fix: add vscode tag guard and include doc/queries in plugin archive"
```

---

### Task 3: Add tag collision guards to `beta.yml`

**Files:**
- Modify: `.github/workflows/beta.yml`

- [ ] **Step 1: Add `if` guard to the `ci` job**

Change the `ci` job from:

```yaml
  ci:
    uses: ./.github/workflows/ci.yml
```

to:

```yaml
  ci:
    if: "!startsWith(github.ref_name, 'vscode/')"
    uses: ./.github/workflows/ci.yml
```

- [ ] **Step 2: Fix plugin-archive to include `doc/` and `queries/`**

In the `plugin-archive` job, change the `cp -r` line from:

```bash
cp -r lua plugin ftdetect ftplugin syntax README.md LICENSE lazy.lua ignition-nvim/
```

to:

```bash
cp -r lua plugin ftdetect ftplugin syntax doc queries README.md LICENSE lazy.lua ignition-nvim/
```

- [ ] **Step 3: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/beta.yml'))"`
Expected: No output (valid YAML)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/beta.yml
git commit -m "fix: add vscode tag guard and include doc/queries in beta plugin archive"
```

---

### Task 4: Create `release-vscode.yml` workflow

**Files:**
- Create: `.github/workflows/release-vscode.yml`

- [ ] **Step 1: Create the workflow file**

Write the complete workflow to `.github/workflows/release-vscode.yml`:

```yaml
name: VS Code Extension Release

on:
  push:
    tags:
      - "vscode/v*"

concurrency:
  group: vscode-release
  cancel-in-progress: false

jobs:
  ci:
    uses: ./.github/workflows/ci.yml

  build:
    name: Build VS Code Extension
    needs: ci
    runs-on: ubuntu-latest
    outputs:
      is-prerelease: ${{ steps.meta.outputs.is-prerelease }}
      version: ${{ steps.meta.outputs.version }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: packages/ignition-vscode/package-lock.json

      - name: Extract version metadata
        id: meta
        run: |
          TAG="${GITHUB_REF#refs/tags/vscode/v}"
          if [[ "$TAG" == *-beta.* ]] || [[ "$TAG" == *-rc.* ]]; then
            echo "is-prerelease=true" >> "$GITHUB_OUTPUT"
          else
            echo "is-prerelease=false" >> "$GITHUB_OUTPUT"
          fi
          echo "version=$TAG" >> "$GITHUB_OUTPUT"

      - name: Set version in package.json
        run: |
          cd packages/ignition-vscode
          npm version "${{ steps.meta.outputs.version }}" --no-git-tag-version

      - name: Install dependencies
        run: cd packages/ignition-vscode && npm ci

      - name: Package extension
        run: cd packages/ignition-vscode && npx @vscode/vsce package

      - name: Upload .vsix artifact
        uses: actions/upload-artifact@v4
        with:
          name: vsix
          path: packages/ignition-vscode/*.vsix

  publish-marketplace:
    name: Publish to VS Code Marketplace
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Download .vsix
        uses: actions/download-artifact@v4
        with:
          name: vsix
          path: vsix/

      - name: Publish
        run: |
          FLAGS=""
          if [ "${{ needs.build.outputs.is-prerelease }}" = "true" ]; then
            FLAGS="--pre-release"
          fi
          npx @vscode/vsce publish $FLAGS --packagePath vsix/*.vsix
        env:
          VSCE_PAT: ${{ secrets.VSCE_PAT }}

  github-release:
    name: Create GitHub Release
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Download .vsix
        uses: actions/download-artifact@v4
        with:
          name: vsix
          path: vsix/

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          prerelease: ${{ needs.build.outputs.is-prerelease == 'true' }}
          generate_release_notes: true
          files: vsix/*
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release-vscode.yml'))"`
Expected: No output (valid YAML)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release-vscode.yml
git commit -m "feat: add VS Code extension release pipeline with marketplace CD"
```
