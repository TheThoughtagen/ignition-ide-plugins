#!/bin/bash
# Manual LSP start script for testing

# Find plugin root (parent of dev-scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate the venv
cd "$PLUGIN_ROOT/lsp"
source venv/bin/activate

# Run the server
python server.py
