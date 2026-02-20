-- LSP client integration for Ignition (Neovim 0.11+)
local M = {}

local lsp_config = {}

-- Setup LSP client
function M.setup(config)
  lsp_config = config

  -- Auto-detect LSP server command if not provided
  if not lsp_config.cmd then
    lsp_config.cmd = M.find_lsp_server()
  end

  if not lsp_config.cmd then
    return
  end

  -- Register LSP configuration with Neovim 0.11+ API
  -- Uses project.json as root marker so the LSP only attaches inside
  -- Ignition projects (every Ignition project has project.json at root).
  -- Supports both 'ignition' (JSON resources) and 'python' (webdev scripts,
  -- scheduled scripts, script-python modules, etc.)
  vim.lsp.config('ignition_lsp', {
    cmd = lsp_config.cmd,
    root_markers = { 'project.json' },
    filetypes = { 'ignition', 'python', 'ignition_expr' },
    settings = lsp_config.settings or {},
    init_options = {
      ignition_version = (lsp_config.settings or {}).ignition
        and (lsp_config.settings.ignition.version or '8.1')
        or '8.1',
    },
  })

  -- Auto-start for matching filetypes in Ignition projects
  vim.api.nvim_create_autocmd('FileType', {
    pattern = { 'ignition', 'python', 'ignition_expr' },
    callback = function(args)
      -- Check if already attached to avoid duplicate clients
      local clients = vim.lsp.get_clients({ bufnr = args.buf, name = 'ignition_lsp' })
      if #clients > 0 then
        return
      end

      -- Get the registered config
      local config = vim.lsp.config.ignition_lsp
      if config then
        vim.lsp.start(config, { bufnr = args.buf })
      end
    end,
    desc = 'Start Ignition LSP for Ignition project files',
  })
end

-- Find the Ignition LSP server executable
function M.find_lsp_server()
  local plugin_root = vim.fn.fnamemodify(debug.getinfo(1).source:sub(2), ':p:h:h:h')

  -- 1. PyPI install in plugin venv (end users via lazy.nvim)
  local venv_cmd = plugin_root .. '/lsp/venv/bin/ignition-lsp'
  if vim.fn.executable(venv_cmd) == 1 then
    return { venv_cmd }
  end

  -- 2. System-installed ignition-lsp (pipx, global pip)
  local installed_cmd = vim.fn.exepath('ignition-lsp')
  if installed_cmd ~= '' then
    return { installed_cmd }
  end

  -- 3. Dev venv with source (contributors)
  local venv_python = plugin_root .. '/lsp/venv/bin/python'
  local server_path = plugin_root .. '/lsp/ignition_lsp/server.py'
  if vim.fn.executable(venv_python) == 1 and vim.fn.filereadable(server_path) == 1 then
    return { venv_python, server_path }
  end

  vim.notify(
    'Ignition LSP server not found. Run :Lazy build ignition-nvim',
    vim.log.levels.ERROR,
    { title = 'Ignition.nvim' }
  )

  return nil
end

-- Start LSP for a specific buffer (used for virtual buffers)
-- @param bufnr number Buffer number (optional, defaults to current buffer)
-- @param root_dir string Root directory for LSP (optional, will auto-detect if not provided)
function M.start_lsp_for_buffer(bufnr, root_dir)
  bufnr = bufnr or vim.api.nvim_get_current_buf()

  if not lsp_config.cmd then
    return nil
  end

  local clients = vim.lsp.get_clients({ bufnr = bufnr, name = 'ignition_lsp' })
  if #clients > 0 then
    return clients[1].id
  end

  local config = vim.lsp.config.ignition_lsp
  if config then
    -- If root_dir is explicitly provided (for virtual buffers), use it
    -- Otherwise let vim.lsp.start auto-detect from buffer path
    local start_config = vim.tbl_extend('force', {}, config)
    if root_dir then
      start_config.root_dir = root_dir
    end
    return vim.lsp.start(start_config, { bufnr = bufnr })
  end

  return nil
end

return M
