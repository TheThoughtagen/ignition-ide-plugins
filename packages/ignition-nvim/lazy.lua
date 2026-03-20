-- lazy.nvim plugin spec for ignition.nvim
-- Users can install with just: { 'TheThoughtagen/ignition-nvim' }
-- and get sensible defaults. All options are overridable in the user spec.

---@type LazyPluginSpec
return {
  'TheThoughtagen/ignition-nvim',

  -- Track releases via git tags (v0.3.1, v0.3.2, etc.)
  version = '*', -- Use latest stable release tag

  -- Lazy-load on Ignition file types and commands
  ft = { 'ignition', 'python' },
  cmd = {
    'IgnitionDecode',
    'IgnitionDecodeAll',
    'IgnitionEncode',
    'IgnitionListScripts',
    'IgnitionOpenKindling',
    'IgnitionInfo',
    'IgnitionComponentTree',
    'IgnitionFormat',
    'IgnitionTabify',
  },

  -- Install the Python LSP server after cloning
  -- Always upgrade to latest version from PyPI
  -- Use TestPyPI for ignition-lint-toolkit beta
  build = 'cd lsp && python3 -m venv venv && venv/bin/pip install --upgrade --extra-index-url https://test.pypi.org/simple/ ignition-lsp',

  opts = {},

  config = function(_, opts)
    require('ignition').setup(opts)
  end,
}
