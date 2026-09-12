# Installation

Choose VS Code, Neovim, or Zed. The editors share a Python language server, with different interfaces for editing embedded scripts.

The language server requires Python 3.8+. Use Python 3.10+ to include the ignition-lint dependency and its diagnostics.

## VS Code

Install [Ignition Dev Tools](https://marketplace.visualstudio.com/items?itemName=WhiskeyHouse.ignition-dev-tools). Open the Ignition project folder. The extension installs the language server on first activation.

Use the Command Palette and search for `Ignition` to find script editing actions. See the [VS Code package guide](https://github.com/TheThoughtagen/ignition-ide-plugins/blob/main/packages/ignition-vscode/README.md) for extension-specific configuration.

## Neovim

Use Neovim 0.11+ with lazy.nvim:

```lua
{ 'TheThoughtagen/ignition-ide-plugins' }
```

The repository includes a lazy.nvim spec with language server setup. Run `:IgnitionInfo` after installation to inspect the plugin state. See [configuration options](../configuration/options.md) to change the Ignition version used for API help.

## Zed

Install the `Ignition` extension from Zed's extensions view. Keep Python on your PATH and open the Ignition project folder containing `project.json`.

Zed edits extracted scripts as real files under `.ignition-scripts/`. Use the save-back code action to update the source JSON. See the [Zed package guide](https://github.com/TheThoughtagen/ignition-ide-plugins/blob/main/packages/ignition-zed/README.md) for installation and language server settings.

## Language server from source

For development or troubleshooting, use an isolated Python environment:

```sh
git clone https://github.com/TheThoughtagen/ignition-ide-plugins.git
cd ignition-ide-plugins
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e packages/ignition-lsp
```

On Windows, activate with `.venv\Scripts\activate` instead. Configure your editor to use the installed `ignition-lsp` executable when overriding automatic installation.

Continue with [editing a first script](quickstart.md).
