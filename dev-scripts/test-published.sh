#!/bin/bash
# Test script for published ignition-nvim packages

set -e

echo "=== Testing ignition-nvim from published packages ==="
echo

# Clean up any previous test installation
echo "1. Cleaning up previous test data..."
rm -rf ~/.local/share/nvim/lazy-test

# Launch Neovim with test config
echo "2. Installing plugin from GitHub and LSP from PyPI..."
echo "   This will take a moment..."

# Find the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

nvim -u "$SCRIPT_DIR/test-install.lua" --headless "+Lazy! sync" +qa

echo
echo "3. Verifying installed versions..."
LSP_PIP=~/.local/share/nvim/lazy-test/ignition-nvim/lsp/venv/bin/pip

echo -n "   ignition-lsp: "
$LSP_PIP show ignition-lsp 2>/dev/null | grep "^Version:" | cut -d' ' -f2

echo -n "   ignition-lint-toolkit: "
$LSP_PIP show ignition-lint-toolkit 2>/dev/null | grep "^Version:" | cut -d' ' -f2 || echo "Not installed (Python <3.10)"

echo
echo "4. Checking LSP server executable..."
LSP_BIN=~/.local/share/nvim/lazy-test/ignition-nvim/lsp/venv/bin/ignition-lsp
if [ -f "$LSP_BIN" ]; then
    echo "   ✓ LSP server found at: $LSP_BIN"
else
    echo "   ✗ LSP server not found!"
    exit 1
fi

echo
echo "5. Testing LSP server..."
echo '{"jsonrpc":"2.0","method":"initialize","id":1}' | $LSP_BIN --stdio 2>&1 | head -5

echo
echo "=== Installation successful! ==="
echo
echo "To test interactively:"
echo "  nvim -u test-install.lua"
echo
echo "Then run:"
echo "  :IgnitionTestVersions"
echo "  :IgnitionInfo"
echo
echo "Plugin installed at:"
echo "  ~/.local/share/nvim/lazy-test/ignition-nvim"
