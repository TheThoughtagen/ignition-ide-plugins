-- Tests for Ignition LSP client module
-- Run with: nvim --headless -u tests/minimal_init.lua -c "PlenaryBustedFile tests/lsp_spec.lua"

local lsp = require('ignition.lsp')
local eq = assert.are.equal

-- ──────────────────────────────────────────────
-- Helpers for mocking vim.fn functions
-- ──────────────────────────────────────────────

-- Saved originals for safe restore
local _saved_fn = {}
local _saved_lsp = {}

--- Mock vim.fn functions, saving originals for restore
local function mock_fn(overrides)
  for name, fn in pairs(overrides) do
    _saved_fn[name] = vim.fn[name]
    vim.fn[name] = fn
  end
end

--- Mock lsp module functions
local function mock_lsp_fn(overrides)
  for name, fn in pairs(overrides) do
    _saved_lsp[name] = lsp[name]
    lsp[name] = fn
  end
end

--- Restore all mocked functions
local function restore_all()
  for name, fn in pairs(_saved_fn) do
    vim.fn[name] = fn
  end
  _saved_fn = {}
  for name, fn in pairs(_saved_lsp) do
    lsp[name] = fn
  end
  _saved_lsp = {}
end

--- Helper: wipeout a buffer
local function wipe(bufnr)
  if bufnr and vim.api.nvim_buf_is_valid(bufnr) then
    vim.cmd('silent! bwipeout! ' .. bufnr)
  end
end

-- ──────────────────────────────────────────────
-- find_lsp_server — server discovery logic
-- ──────────────────────────────────────────────
describe('find_lsp_server', function()
  after_each(restore_all)

  it('returns venv python + server path when both exist', function()
    mock_fn({
      executable = function(path)
        if path:match('venv/bin/python$') then return 1 end
        return 0
      end,
      filereadable = function(path)
        if path:match('server%.py$') then return 1 end
        return 0
      end,
      exepath = function() return '' end,
    })

    local cmd = lsp.find_lsp_server()
    assert.is_not_nil(cmd)
    eq(2, #cmd)
    assert.is_truthy(cmd[1]:find('venv/bin/python'))
    assert.is_truthy(cmd[2]:find('server%.py'))
  end)

  it('falls back to system ignition-lsp when venv not found', function()
    mock_fn({
      executable = function() return 0 end,
      filereadable = function() return 0 end,
      exepath = function(name)
        if name == 'ignition-lsp' then return '/usr/local/bin/ignition-lsp' end
        return ''
      end,
    })

    local cmd = lsp.find_lsp_server()
    assert.is_not_nil(cmd)
    eq(1, #cmd)
    eq('/usr/local/bin/ignition-lsp', cmd[1])
  end)

  it('returns nil when no server can be found', function()
    mock_fn({
      executable = function() return 0 end,
      filereadable = function() return 0 end,
      exepath = function() return '' end,
    })

    local cmd = lsp.find_lsp_server()
    assert.is_nil(cmd)
  end)

  it('prefers venv binary over system install', function()
    mock_fn({
      executable = function(path)
        -- Both venv ignition-lsp binary and system binary available
        if path:match('venv/bin/ignition%-lsp$') then return 1 end
        return 0
      end,
      filereadable = function() return 0 end,
      exepath = function(name)
        if name == 'ignition-lsp' then return '/usr/local/bin/ignition-lsp' end
        return ''
      end,
    })

    local cmd = lsp.find_lsp_server()
    assert.is_not_nil(cmd)
    -- Should be venv binary (step 1), not system install (step 2)
    eq(1, #cmd)
    assert.is_truthy(cmd[1]:find('venv/bin/ignition%-lsp'))
  end)
end)

-- ──────────────────────────────────────────────
-- start_lsp_for_buffer — guard clauses
-- ──────────────────────────────────────────────
describe('start_lsp_for_buffer', function()
  after_each(restore_all)

  it('returns nil when cmd is not configured', function()
    -- Mock find_lsp_server BEFORE setup so setup() stores nil cmd
    mock_lsp_fn({
      find_lsp_server = function() return nil end,
    })

    lsp.setup({ cmd = nil, enabled = true, auto_start = false })

    local result = lsp.start_lsp_for_buffer()
    assert.is_nil(result)
  end)

  it('checks for existing clients on a buffer', function()
    local buf = vim.api.nvim_create_buf(true, false)
    vim.api.nvim_buf_set_name(buf, '/tmp/lsp_test_no_attach.json')

    -- No ignition_lsp clients should be attached to a fresh buffer
    -- vim.lsp.get_clients (0.10+) or vim.lsp.get_active_clients (older)
    local get_clients = vim.lsp.get_clients or vim.lsp.get_active_clients
    local all_clients = get_clients({ bufnr = buf })
    local ignition_clients = {}
    for _, c in ipairs(all_clients) do
      if c.name == 'ignition_lsp' then
        table.insert(ignition_clients, c)
      end
    end
    eq(0, #ignition_clients)

    wipe(buf)
  end)
end)

-- ──────────────────────────────────────────────
-- Root directory detection
-- ──────────────────────────────────────────────
describe('root directory detection', function()
  it('vim.fs.root finds project.json as root marker', function()
    -- Create a temp directory structure with project.json
    local tmpdir = vim.fn.tempname()
    vim.fn.mkdir(tmpdir, 'p')
    -- Resolve symlinks (macOS: /var -> /private/var)
    tmpdir = vim.fn.resolve(tmpdir)

    local project_json = tmpdir .. '/project.json'
    vim.fn.writefile({ '{}' }, project_json)

    local nested_dir = tmpdir .. '/views/overview'
    vim.fn.mkdir(nested_dir, 'p')
    local view_file = nested_dir .. '/view.json'
    vim.fn.writefile({ '{"script": "pass"}' }, view_file)

    local buf = vim.api.nvim_create_buf(true, false)
    vim.api.nvim_buf_set_name(buf, view_file)

    local root = vim.fs.root(buf, { 'project.json', '.git' })
    assert.is_not_nil(root)
    -- Resolve both sides to handle macOS /var -> /private/var
    eq(vim.fn.resolve(tmpdir), vim.fn.resolve(root))

    wipe(buf)
    vim.fn.delete(tmpdir, 'rf')
  end)

  it('returns nil when no marker files found', function()
    local tmpdir = vim.fn.tempname()
    vim.fn.mkdir(tmpdir, 'p')
    local file = tmpdir .. '/standalone.json'
    vim.fn.writefile({ '{}' }, file)

    local buf = vim.api.nvim_create_buf(true, false)
    vim.api.nvim_buf_set_name(buf, file)

    local root = vim.fs.root(buf, { 'project.json' })
    assert.is_nil(root)

    wipe(buf)
    vim.fn.delete(tmpdir, 'rf')
  end)
end)

-- ──────────────────────────────────────────────
-- setup
-- ──────────────────────────────────────────────
describe('setup', function()
  after_each(restore_all)

  it('uses provided cmd without calling find_lsp_server', function()
    local find_called = false
    mock_lsp_fn({
      find_lsp_server = function()
        find_called = true
        return nil
      end,
    })

    lsp.setup({
      cmd = { '/usr/bin/python3', '/path/to/server.py' },
      enabled = true,
      auto_start = false,
    })

    -- find_lsp_server should NOT have been called when cmd is explicitly provided
    assert.is_false(find_called)
  end)

  it('calls find_lsp_server when cmd is not provided', function()
    local find_called = false
    mock_lsp_fn({
      find_lsp_server = function()
        find_called = true
        return { '/mock/python', '/mock/server.py' }
      end,
    })

    lsp.setup({
      enabled = true,
      auto_start = false,
    })

    assert.is_true(find_called)
  end)
end)

