-- Filetype plugin for Python files inside Ignition projects
-- Sets Jython tab conventions (tabs, not spaces) when inside an Ignition project

-- Only apply once per buffer
if vim.b.ignition_python_ftplugin then
  return
end

-- Check if this file is inside an Ignition project (has project.json ancestor)
local function in_ignition_project()
  local path = vim.api.nvim_buf_get_name(0)
  if path == '' then
    return false
  end
  local dir = vim.fn.fnamemodify(path, ':h')
  local root = vim.fs.find('project.json', { path = dir, upward = true, type = 'file' })[1]
  return root ~= nil
end

if not in_ignition_project() then
  return
end

vim.b.ignition_python_ftplugin = 1

-- Jython convention: tabs, not spaces
vim.bo.expandtab = false
vim.bo.tabstop = 4
vim.bo.shiftwidth = 4
vim.bo.softtabstop = 4

-- Convert leading spaces to tabs in the current buffer
-- Only touches indentation, leaves spaces inside code untouched
local function tabify_buffer()
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local ts = vim.bo.tabstop
  local changed = false

  for i, line in ipairs(lines) do
    local leading = line:match('^([ \t]*)')
    if leading:find(' ') then
      -- Expand existing tabs to spaces first, then convert to tabs
      local expanded = leading:gsub('\t', string.rep(' ', ts))
      local tab_count = math.floor(#expanded / ts)
      local remainder = #expanded % ts
      local new_leading = string.rep('\t', tab_count) .. string.rep(' ', remainder)
      if new_leading ~= leading then
        lines[i] = new_leading .. line:sub(#leading + 1)
        changed = true
      end
    end
  end

  if changed then
    vim.api.nvim_buf_set_lines(0, 0, -1, false, lines)
  end
end

-- Tabify on load
tabify_buffer()

-- Tabify before save (catches any spaces introduced by paste/format)
vim.api.nvim_create_autocmd('BufWritePre', {
  buffer = 0,
  callback = tabify_buffer,
})

-- Suppress Pyright/basedpyright false positives for Ignition project imports.
-- Ignition's Jython runtime resolves project module paths (e.g.,
-- "from core.networking.graphql import ...") at runtime, so static analysis
-- can't find them. We keep Pyright attached for general Python linting but
-- disable import-related diagnostics.
local pyright_overrides = {
  python = {
    analysis = {
      diagnosticSeverityOverrides = {
        reportMissingImports = 'none',
        reportMissingModuleSource = 'none',
      },
    },
  },
}

local function configure_pyright(client)
  client.settings = vim.tbl_deep_extend('force', client.settings or {}, pyright_overrides)
  client:notify('workspace/didChangeConfiguration', { settings = client.settings })
end

-- Configure any already-attached Pyright
for _, client in ipairs(vim.lsp.get_clients({ bufnr = 0 })) do
  if client.name == 'pyright' or client.name == 'basedpyright' then
    configure_pyright(client)
  end
end

-- Configure Pyright if it attaches later
vim.api.nvim_create_autocmd('LspAttach', {
  buffer = 0,
  callback = function(args)
    local client = vim.lsp.get_client_by_id(args.data.client_id)
    if client and (client.name == 'pyright' or client.name == 'basedpyright') then
      vim.schedule(function()
        configure_pyright(client)
      end)
    end
  end,
})
