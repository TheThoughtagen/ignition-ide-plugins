-- ignition.nvim - Neovim plugin for Ignition by Inductive Automation
-- Main plugin entry point

-- Prevent loading the plugin multiple times
if vim.g.loaded_ignition then
  return
end
vim.g.loaded_ignition = true

-- Register treesitter JSON parser for ignition filetype
-- This enables modern syntax highlighting instead of legacy syntax/json.vim
pcall(vim.treesitter.language.register, 'json', 'ignition')

-- Create user commands
vim.api.nvim_create_user_command('IgnitionDecode', function()
  require('ignition.decoder').decode_current_buffer()
end, { desc = 'Decode Ignition embedded scripts in current buffer' })

vim.api.nvim_create_user_command('IgnitionEncode', function()
  require('ignition.decoder').encode_current_buffer()
end, { desc = 'Encode Ignition scripts back to JSON format' })

vim.api.nvim_create_user_command('IgnitionOpenKindling', function(opts)
  require('ignition.kindling').open_with_kindling(opts.args)
end, {
  nargs = '?',
  complete = 'file',
  desc = 'Open .gwbk file with Kindling utility'
})

vim.api.nvim_create_user_command('IgnitionDecodeAll', function()
  require('ignition.decoder').decode_all_scripts()
end, { desc = 'Decode all Ignition scripts in current buffer' })

vim.api.nvim_create_user_command('IgnitionListScripts', function()
  require('ignition.decoder').list_scripts()
end, { desc = 'List all Ignition scripts in current buffer' })

vim.api.nvim_create_user_command('IgnitionInfo', function()
  require('ignition').info()
end, { desc = 'Show Ignition plugin information and status' })

vim.api.nvim_create_user_command('IgnitionDebugLSP', function()
  local bufnr = vim.api.nvim_get_current_buf()
  local lines = {
    '=== Ignition LSP Debug ===',
    'Buffer: ' .. bufnr,
    'Name: ' .. vim.api.nvim_buf_get_name(bufnr),
    'Filetype: ' .. vim.bo[bufnr].filetype,
    'Buftype: ' .. vim.bo[bufnr].buftype,
  }

  local vd = require('ignition.virtual_doc')
  local is_virtual = vd.is_virtual_doc(bufnr)
  table.insert(lines, 'Is Virtual: ' .. tostring(is_virtual))

  if is_virtual then
    local meta = vd.get_metadata(bufnr)
    table.insert(lines, 'Source: ' .. meta.source_file)
    local root = vim.fs.root(meta.source_file, 'project.json')
    table.insert(lines, 'Root: ' .. (root or 'NOT FOUND'))
  else
    local root = vim.fs.root(bufnr, 'project.json')
    table.insert(lines, 'Root: ' .. (root or 'NOT FOUND'))
  end

  local clients = vim.lsp.get_clients({ bufnr = bufnr })
  table.insert(lines, 'LSP Clients: ' .. #clients)
  for _, c in ipairs(clients) do
    table.insert(lines, '  - ' .. c.name .. ' root: ' .. (c.config.root_dir or 'none'))
  end

  if #clients == 0 then
    table.insert(lines, 'Attempting manual LSP start...')
    local lsp = require('ignition.lsp')
    local root_dir = nil
    if is_virtual then
      local meta = vd.get_metadata(bufnr)
      root_dir = vim.fs.root(meta.source_file, 'project.json')
    end
    local id = lsp.start_lsp_for_buffer(bufnr, root_dir)
    table.insert(lines, 'Start result: ' .. tostring(id or 'FAILED'))
  end

  print(table.concat(lines, '\n'))
end, { desc = 'Debug LSP attachment for current buffer' })

vim.api.nvim_create_user_command('IgnitionComponentTree', function()
  require('ignition.component_tree').toggle()
end, { desc = 'Toggle Perspective component tree sidebar' })

vim.api.nvim_create_user_command('IgnitionFormat', function()
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local indent = 0
  local result = {}

  for _, line in ipairs(lines) do
    local trimmed = line:match('^%s*(.-)%s*$')
    if trimmed == '' then
      result[#result + 1] = ''
      goto continue
    end

    -- Count openers/closers outside strings
    local in_string = false
    local escaped = false
    local delta = 0
    for i = 1, #trimmed do
      local ch = trimmed:sub(i, i)
      if escaped then
        escaped = false
      elseif ch == '\\' and in_string then
        escaped = true
      elseif ch == '"' then
        in_string = not in_string
      elseif not in_string then
        if ch == '{' or ch == '[' then
          delta = delta + 1
        elseif ch == '}' or ch == ']' then
          delta = delta - 1
        end
      end
    end

    -- Lines starting with closer: write at reduced indent, don't double-count
    local line_indent = indent
    if trimmed:match('^[%]%}]') then
      line_indent = math.max(0, indent - 1)
    end

    result[#result + 1] = string.rep('  ', line_indent) .. trimmed
    indent = math.max(0, indent + delta)

    ::continue::
  end

  local changed = 0
  for i, line in ipairs(lines) do
    if result[i] ~= line then
      changed = changed + 1
    end
  end

  local save = vim.fn.winsaveview()
  vim.api.nvim_buf_set_lines(0, 0, -1, false, result)
  vim.fn.winrestview(save)
  vim.notify(
    string.format('IgnitionFormat: %d/%d lines changed', changed, #lines),
    vim.log.levels.INFO,
    { title = 'Ignition.nvim' }
  )
end, { desc = 'Fix JSON indentation' })

-- Convert leading spaces to tabs in current buffer (4 spaces = 1 tab).
-- Ignition's Jython convention uses tabs for indentation.
local function spaces_to_tabs(bufnr)
  bufnr = bufnr or 0
  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local changed = 0
  local result = {}

  for _, line in ipairs(lines) do
    local spaces = line:match('^( +)')
    if spaces then
      local tab_count = math.floor(#spaces / 4)
      local remaining = #spaces % 4
      local new_line = string.rep('\t', tab_count) .. string.rep(' ', remaining) .. line:sub(#spaces + 1)
      if new_line ~= line then
        changed = changed + 1
      end
      result[#result + 1] = new_line
    else
      result[#result + 1] = line
    end
  end

  if changed > 0 then
    local save = vim.fn.winsaveview()
    vim.api.nvim_buf_set_lines(bufnr, 0, -1, false, result)
    vim.fn.winrestview(save)
  end
  return changed
end

vim.api.nvim_create_user_command('IgnitionViewDocs', function()
  -- Find .md files near the current buffer's directory or project root
  local buf_dir = vim.fn.expand('%:p:h')
  local project_root = vim.fs.root(0, 'project.json') or buf_dir

  local md_files = {}
  -- Search current dir, parent, and project root (up to 2 levels deep)
  local search_dirs = { buf_dir }
  if buf_dir ~= project_root then
    table.insert(search_dirs, project_root)
  end

  for _, dir in ipairs(search_dirs) do
    for name, type in vim.fs.dir(dir, { depth = 2 }) do
      if type == 'file' and name:match('%.md$') then
        local full = dir .. '/' .. name
        -- Deduplicate
        local found = false
        for _, existing in ipairs(md_files) do
          if existing == full then found = true; break end
        end
        if not found then
          table.insert(md_files, full)
        end
      end
    end
  end

  if #md_files == 0 then
    vim.notify('No documentation files found', vim.log.levels.INFO, { title = 'Ignition' })
    return
  end

  if #md_files == 1 then
    vim.cmd('edit ' .. vim.fn.fnameescape(md_files[1]))
    return
  end

  -- Multiple docs — show picker
  vim.ui.select(md_files, {
    prompt = 'Select documentation:',
    format_item = function(item)
      return vim.fn.fnamemodify(item, ':~:.')
    end,
  }, function(choice)
    if choice then
      vim.cmd('edit ' .. vim.fn.fnameescape(choice))
    end
  end)
end, { desc = 'View documentation (.md files) near current resource' })

vim.api.nvim_create_user_command('IgnitionTagBrowser', function(opts)
  -- Find tags/ directory from project root
  local project_root = vim.fs.root(0, 'project.json') or vim.fn.getcwd()
  local tags_dir = project_root .. '/tags'

  if vim.fn.isdirectory(tags_dir) ~= 1 then
    vim.notify('No tags/ directory found at ' .. project_root, vim.log.levels.WARN, { title = 'Ignition' })
    return
  end

  -- Build tag list by scanning the directory
  local tags = {}
  local function scan_dir(dir, prefix)
    local handle = vim.loop.fs_scandir(dir)
    if not handle then return end
    while true do
      local name, type = vim.loop.fs_scandir_next(handle)
      if not name then break end
      if name:sub(1, 1) == '.' then goto continue end

      local full_path = dir .. '/' .. name
      if type == 'directory' then
        local label = name == '_types_' and 'UDT Definitions' or name
        scan_dir(full_path, prefix .. label .. '/')
      elseif name:match('%.json$') then
        local tag_name = name:gsub('%.json$', '')
        local tag_path = prefix .. tag_name
        -- Read minimal metadata
        local ok, content = pcall(vim.fn.readfile, full_path, '', 5)
        local meta = ''
        if ok and #content > 0 then
          local text = table.concat(content, '\n')
          local dt = text:match('"dataType"%s*:%s*"([^"]*)"')
          local vs = text:match('"valueSource"%s*:%s*"([^"]*)"')
          local tt = text:match('"tagType"%s*:%s*"([^"]*)"')
          local parts = {}
          if tt and tt ~= 'AtomicTag' then table.insert(parts, tt) end
          if dt then table.insert(parts, dt) end
          if vs then table.insert(parts, vs) end
          meta = table.concat(parts, ' ')
        end
        table.insert(tags, { path = tag_path, file = full_path, meta = meta })
      end
      ::continue::
    end
  end

  -- Scan providers
  local phandle = vim.loop.fs_scandir(tags_dir)
  if not phandle then return end
  while true do
    local name, type = vim.loop.fs_scandir_next(phandle)
    if not name then break end
    if type == 'directory' and name:sub(1, 1) ~= '.' then
      scan_dir(tags_dir .. '/' .. name, '[' .. name .. ']')
    end
  end

  if #tags == 0 then
    vim.notify('No tags found', vim.log.levels.INFO, { title = 'Ignition' })
    return
  end

  -- If an argument was passed, filter by it
  local query = opts.args ~= '' and opts.args or nil

  -- Use vim.ui.select (telescope-compatible)
  local filtered = tags
  if query then
    local q = query:lower()
    filtered = vim.tbl_filter(function(t)
      return t.path:lower():find(q, 1, true)
    end, tags)
  end

  vim.ui.select(filtered, {
    prompt = 'Tag Browser (' .. #filtered .. ' tags):',
    format_item = function(item)
      if item.meta ~= '' then
        return item.path .. '  (' .. item.meta .. ')'
      end
      return item.path
    end,
  }, function(choice)
    if choice then
      vim.cmd('edit ' .. vim.fn.fnameescape(choice.file))
    end
  end)
end, {
  nargs = '?',
  desc = 'Browse Ignition tags (ignition-git-module format)',
})

vim.api.nvim_create_user_command('IgnitionTabify', function()
  local changed = spaces_to_tabs()
  vim.notify(
    string.format('Converted %d lines from spaces to tabs', changed),
    vim.log.levels.INFO,
    { title = 'Ignition.nvim' }
  )
end, { desc = 'Convert leading spaces to tabs (Ignition Jython convention)' })

-- Default highlight groups for Ignition treesitter queries
vim.api.nvim_set_hl(0, '@ignition.script_key', { default = true, link = 'Special' })

-- Highlight groups for component tree sidebar
vim.api.nvim_set_hl(0, 'IgnitionTreeIcon', { default = true, link = 'Directory' })
vim.api.nvim_set_hl(0, 'IgnitionTreeName', { default = true, link = 'Identifier' })
vim.api.nvim_set_hl(0, 'IgnitionTreeType', { default = true, link = 'Comment' })
vim.api.nvim_set_hl(0, 'IgnitionTreeScript', { default = true, link = 'WarningMsg' })

-- Create augroup for plugin autocommands
local augroup = vim.api.nvim_create_augroup('Ignition', { clear = true })

-- Note: File type detection is handled by ftdetect/ignition.lua

-- Configure Python files in Ignition projects for tab indentation.
-- Ignition's Jython convention uses tabs, not spaces.
vim.api.nvim_create_autocmd('FileType', {
  group = augroup,
  pattern = 'python',
  callback = function(args)
    if not vim.fs.root(args.buf, 'project.json') then
      return
    end
    -- Use tabs for indentation, displayed as 4 characters wide
    vim.bo[args.buf].expandtab = false
    vim.bo[args.buf].tabstop = 4
    vim.bo[args.buf].shiftwidth = 4
    vim.bo[args.buf].softtabstop = 4
  end,
})

-- Auto-convert spaces to tabs on save for Python files in Ignition projects.
-- Catches files that were originally space-indented.
vim.api.nvim_create_autocmd('BufWritePre', {
  group = augroup,
  pattern = '*.py',
  callback = function(args)
    if vim.fs.root(args.buf, 'project.json') then
      spaces_to_tabs(args.buf)
    end
  end,
})

-- Suppress false-positive pyright/basedpyright diagnostics in Ignition projects.
-- Ignition's Jython runtime injects globals (system, event, project libraries)
-- that pyright flags as "is not defined" or "is not accessed".
--
-- Static builtins: always available in every Ignition script context.
local ignition_builtins = {
  -- Core scripting API
  system = true,
  logger = true,
  shared = true,
  project = true,
  -- Tag change scripts
  initialChange = true,
  newValue = true,
  previousValue = true,
  currentValue = true,
  tagPath = true,
  executionCount = true,
  -- Event scripts (Vision, Perspective, Gateway)
  event = true,
  source = true,
  -- Message handlers
  payload = true,
}

-- Framework-injected parameters that can't be removed even if unused.
-- Suppresses "X is not accessed" warnings for these names.
local ignition_framework_params = {
  initialChange = true,
  newValue = true,
  previousValue = true,
  currentValue = true,
  tagPath = true,
  executionCount = true,
  event = true,
  source = true,
  payload = true,
}

-- Cache for project script library packages (top-level names under script-python/)
local _project_packages_cache = {}

--- Discover top-level script library packages in an Ignition project.
--- E.g., script-python/core/ -> "core", script-python/project-library/ -> "project"
local function get_project_packages(project_root)
  if _project_packages_cache[project_root] then
    return _project_packages_cache[project_root]
  end

  local packages = {}
  local script_python = project_root .. '/ignition/script-python'
  local ok, entries = pcall(vim.fn.readdir, script_python)
  if ok then
    for _, entry in ipairs(entries) do
      -- Ignition convention: "project-library" -> top-level name is first segment
      local top = entry:match('^([^-]+)')
      if top then
        packages[top] = true
      end
    end
  end

  _project_packages_cache[project_root] = packages
  return packages
end

--- Check if a name is a known Ignition runtime global or project package.
local function is_ignition_name(name, project_root)
  if ignition_builtins[name] then
    return true
  end
  if project_root then
    return get_project_packages(project_root)[name] or false
  end
  return false
end

local orig_publish_diagnostics = vim.lsp.handlers['textDocument/publishDiagnostics']
vim.lsp.handlers['textDocument/publishDiagnostics'] = function(err, result, ctx, config)
  local client = vim.lsp.get_client_by_id(ctx.client_id)
  if client and (client.name == 'pyright' or client.name == 'basedpyright') and result and result.diagnostics then
    local path = vim.uri_to_fname(result.uri)
    local project_root = vim.fs.root(path, 'project.json')
    if project_root then
      result.diagnostics = vim.tbl_filter(function(d)
        if not d.message then return true end
        -- Suppress '"X" is not defined' for builtins and project packages
        local undefined = d.message:match('^"([%w_]+)" is not defined')
        if undefined and is_ignition_name(undefined, project_root) then
          return false
        end
        -- Suppress '"X" is not accessed' for framework-injected params
        local unused = d.message:match('^"([%w_]+)" is not accessed')
        if unused and ignition_framework_params[unused] then
          return false
        end
        return true
      end, result.diagnostics)
    end
  end
  return orig_publish_diagnostics(err, result, ctx, config)
end

-- Disable external Python linters (ruff, flake8, etc.) for Ignition projects.
-- Ignition scripts are Jython with implicit globals — standard Python linters
-- produce noisy false positives. Our ignition LSP handles diagnostics instead.
do
  local ok, lint = pcall(require, 'lint')
  if ok and lint.try_lint then
    local orig_try_lint = lint.try_lint
    lint.try_lint = function(...)
      local buf = vim.api.nvim_get_current_buf()
      if vim.bo[buf].filetype == 'python' and vim.fs.root(buf, 'project.json') then
        return
      end
      return orig_try_lint(...)
    end
  end
end

-- Disable conform/black for Python files in Ignition projects.
-- Black enforces spaces but Ignition convention is tabs. Our BufWritePre
-- autocmd handles the space→tab conversion instead.
do
  local ok, conform = pcall(require, 'conform')
  if ok then
    local orig_format = conform.format
    conform.format = function(opts, ...)
      opts = opts or {}
      local buf = opts.bufnr or vim.api.nvim_get_current_buf()
      if vim.bo[buf].filetype == 'python' and vim.fs.root(buf, 'project.json') then
        return
      end
      return orig_format(opts, ...)
    end
  end
end
