-- Minimal Neovim config to test ignition-nvim from published packages
-- Usage: nvim -u test-install.lua

-- Set up lazy.nvim in a test directory
local lazypath = vim.fn.stdpath("data") .. "/lazy-test/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

-- Install ignition-nvim from GitHub with LSP from PyPI
require("lazy").setup({
  {
    'pmannion2/ignition-nvim',
    ft = { 'ignition', 'python' },
    -- This will pip install ignition-lsp==0.3.1 from PyPI
    build = 'cd lsp && python3 -m venv venv && venv/bin/pip install ignition-lsp==0.3.1',
    opts = {},
  }
}, {
  root = vim.fn.stdpath("data") .. "/lazy-test",
})

-- Helper command to verify versions
vim.api.nvim_create_user_command('IgnitionTestVersions', function()
  print("=== Installed Versions ===")
  local lsp_path = vim.fn.stdpath("data") .. "/lazy-test/ignition-nvim/lsp/venv/bin/pip"
  local result = vim.fn.system(lsp_path .. " show ignition-lsp 2>/dev/null | grep Version")
  print("ignition-lsp: " .. vim.trim(result))

  local lint_result = vim.fn.system(lsp_path .. " show ignition-lint-toolkit 2>/dev/null | grep Version")
  print("ignition-lint-toolkit: " .. vim.trim(lint_result))

  print("\nPlugin location: " .. vim.fn.stdpath("data") .. "/lazy-test/ignition-nvim")
end, {})

print("Test environment loaded!")
print("Run :IgnitionTestVersions to verify package versions")
print("Run :Lazy to check plugin installation")
