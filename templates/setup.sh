#!/usr/bin/env bash
# Ignition Claude Code Setup
# Installs CLAUDE.md and ignition-lint hooks into your Ignition project.
#
# Usage (from your Ignition project root):
#   curl -sL https://raw.githubusercontent.com/whiskeyhouse/ignition-nvim/main/templates/setup.sh | bash
#
# Or if you've cloned the repo:
#   bash /path/to/ignition-nvim/templates/setup.sh

set -euo pipefail

REPO="whiskeyhouse/ignition-nvim"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/$REPO/$BRANCH/templates"

# Colors (if terminal supports them)
if [ -t 1 ]; then
  BOLD='\033[1m'
  GREEN='\033[32m'
  YELLOW='\033[33m'
  RESET='\033[0m'
else
  BOLD='' GREEN='' YELLOW='' RESET=''
fi

info()  { echo -e "${GREEN}${BOLD}[ignition]${RESET} $*"; }
warn()  { echo -e "${YELLOW}${BOLD}[ignition]${RESET} $*"; }

# Check we're in a plausible Ignition project
if [ ! -f "project.json" ]; then
  warn "No project.json found in $(pwd)"
  warn "Run this from the root of your Ignition project."
  echo ""
  read -rp "Continue anyway? [y/N] " answer
  case "$answer" in
    [yY]*) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

# Detect source: local clone or remote fetch
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -f "$SCRIPT_DIR/CLAUDE.md" ] && [ -f "$SCRIPT_DIR/.claude/settings.json" ]; then
  # Running from a local clone
  SOURCE="local"
  info "Installing from local clone: $SCRIPT_DIR"
else
  SOURCE="remote"
  info "Downloading from github.com/$REPO..."
fi

fetch_file() {
  local rel_path="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"

  if [ "$SOURCE" = "local" ]; then
    cp "$SCRIPT_DIR/$rel_path" "$dest"
  else
    if ! curl -sfL "$BASE_URL/$rel_path" -o "$dest"; then
       warn "Failed to download $rel_path"
       exit 1
    fi
  fi
}

# Install CLAUDE.md
if [ -f "CLAUDE.md" ]; then
  warn "CLAUDE.md already exists — backing up to CLAUDE.md.bak"
  cp CLAUDE.md CLAUDE.md.bak
fi
fetch_file "CLAUDE.md" "CLAUDE.md"
info "Installed CLAUDE.md"

# Install .claude/settings.json
if [ -f ".claude/settings.json" ]; then
  warn ".claude/settings.json already exists — backing up to .claude/settings.json.bak"
  cp .claude/settings.json .claude/settings.json.bak
fi
fetch_file ".claude/settings.json" ".claude/settings.json"
info "Installed .claude/settings.json"

# Install hook script
fetch_file ".claude/hooks/ignition-lint.sh" ".claude/hooks/ignition-lint.sh"
chmod +x .claude/hooks/ignition-lint.sh
info "Installed .claude/hooks/ignition-lint.sh"

# Check for ignition-lint
echo ""
if command -v ignition-lint &>/dev/null; then
  VERSION=$(ignition-lint --version 2>&1 || echo "unknown")
  info "ignition-lint found: $VERSION"
else
  warn "ignition-lint not found. Install it:"
  echo "  pip install ignition-lint-toolkit"
  echo ""
  echo "The hook will work once it's installed. No rush."
fi

echo ""
info "Done! Your Ignition project now has:"
echo "  CLAUDE.md                          — API reference, expressions, conventions"
echo "  .claude/settings.json              — Auto-lint hook config"
echo "  .claude/hooks/ignition-lint.sh     — Lint .py, view.json, tags.json on edit"
echo ""
info "Open Claude Code in this project and start writing Ignition scripts."
