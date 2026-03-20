-- Component tree view for Ignition Perspective views
-- Displays a navigable sidebar showing the component hierarchy

local M = {}

local SCRIPT_KEYS_SET = {}
for _, key in ipairs(require('ignition.json_parser').SCRIPT_KEYS) do
  SCRIPT_KEYS_SET[key] = true
end

-- Default config, overridden by setup()
M.config = {
  width = 40,
  position = 'left',
}

-- State per source buffer
-- { [source_bufnr] = { tree_bufnr, tree_winid, nodes, flat_nodes, source_bufnr } }
local state = {}

--- Build a node from a component table.
--- @param component table Raw JSON component
--- @param depth number Nesting depth
--- @return table node
function M.build_node(component, depth)
  local meta = component.meta or {}
  local name = meta.name or '(unnamed)'
  local comp_type = component.type or ''
  local short_type = comp_type:match('^ia%.(.+)$') or comp_type
  local has_scripts = M.detect_scripts(component)

  return {
    name = name,
    type = comp_type,
    short_type = short_type,
    has_scripts = has_scripts,
    depth = depth or 0,
    expanded = true,
    children = {},
  }
end

--- Check if a component has any scripts in its events table.
--- @param component table
--- @return boolean
function M.detect_scripts(component)
  local events = component.events
  if type(events) ~= 'table' then
    return false
  end
  for key, val in pairs(events) do
    if SCRIPT_KEYS_SET[key] then
      return true
    end
    -- events can be nested: events.onActionPerformed.script
    if type(val) == 'table' then
      for sub_key, _ in pairs(val) do
        if SCRIPT_KEYS_SET[sub_key] then
          return true
        end
      end
    end
  end
  return false
end

--- Check if parsed JSON is a Perspective view (root.type starts with "ia.").
--- @param data table Parsed JSON
--- @return boolean
function M.is_perspective_view(data)
  if type(data) ~= 'table' then
    return false
  end
  local root = data.root
  if type(root) ~= 'table' then
    return false
  end
  local root_type = root.type
  if type(root_type) ~= 'string' then
    return false
  end
  return root_type:match('^ia%.') ~= nil
end

--- Recursively walk a component and its children, building the tree.
--- @param component table
--- @param depth number
--- @return table node
local function walk(component, depth)
  local node = M.build_node(component, depth)
  local children = component.children
  if type(children) == 'table' then
    for _, child in ipairs(children) do
      table.insert(node.children, walk(child, depth + 1))
    end
  end
  return node
end

--- Parse a Perspective view.json into a component tree.
--- @param json_str string Raw JSON string
--- @return table|nil root_node
--- @return string|nil error
function M.parse_view_json(json_str)
  local ok, data = pcall(vim.json.decode, json_str)
  if not ok then
    return nil, 'Failed to parse JSON'
  end
  if not M.is_perspective_view(data) then
    return nil, 'Not a Perspective view'
  end
  return walk(data.root, 0), nil
end

--- Render a single tree line for a node.
--- @param node table
--- @return string
function M.render_node_line(node)
  local indent = string.rep('  ', node.depth)
  local icon
  if #node.children > 0 then
    icon = node.expanded and '▾ ' or '▸ '
  else
    icon = '  '
  end
  local scripts_tag = node.has_scripts and ' [scripts]' or ''
  local type_suffix = node.short_type ~= '' and ('  ‹' .. node.short_type .. '›') or ''
  return indent .. icon .. node.name .. type_suffix .. scripts_tag
end

--- Flatten the tree into an ordered list of visible nodes (respecting expanded state).
--- @param node table root node
--- @return table[] flat list of nodes
function M.flatten(node)
  local result = {}
  local function recurse(n)
    table.insert(result, n)
    if n.expanded and n.children then
      for _, child in ipairs(n.children) do
        recurse(child)
      end
    end
  end
  recurse(node)
  return result
end

--- Render the tree into buffer lines.
--- @param root_node table
--- @return string[] lines
--- @return table[] flat_nodes (parallel array)
local function render_tree(root_node)
  local flat = M.flatten(root_node)
  local lines = {}
  for _, node in ipairs(flat) do
    table.insert(lines, M.render_node_line(node))
  end
  return lines, flat
end

--- Find the line number in the source buffer for a component by its meta.name.
--- @param source_bufnr number
--- @param name string
--- @return number|nil 1-based line number
local function find_component_line(source_bufnr, name)
  local lines = vim.api.nvim_buf_get_lines(source_bufnr, 0, -1, false)
  -- JSON-escape internal double quotes before building the pattern
  local json_escaped_name = name:gsub('"', '\\"')
  local pattern = '"name"%s*:%s*"' .. vim.pesc(json_escaped_name) .. '"'
  for i, line in ipairs(lines) do
    if line:find(pattern) then
      return i
    end
  end
  return nil
end

--- Refresh the tree sidebar for a given source buffer.
local function refresh(source_bufnr)
  local s = state[source_bufnr]
  if not s or not vim.api.nvim_buf_is_valid(s.tree_bufnr) then
    return
  end

  local lines_content = vim.api.nvim_buf_get_lines(source_bufnr, 0, -1, false)
  local json_str = table.concat(lines_content, '\n')
  local root_node, err = M.parse_view_json(json_str)
  if not root_node then
    -- Clear stale state so keymaps don't act on outdated nodes
    s.flat_nodes = nil
    s.root_node = nil
    vim.api.nvim_buf_set_option(s.tree_bufnr, 'modifiable', true)
    vim.api.nvim_buf_set_lines(s.tree_bufnr, 0, -1, false, { err or 'Error parsing view' })
    vim.api.nvim_buf_set_option(s.tree_bufnr, 'modifiable', false)
    return
  end

  s.root_node = root_node
  local buf_lines, flat = render_tree(root_node)
  s.flat_nodes = flat

  vim.api.nvim_buf_set_option(s.tree_bufnr, 'modifiable', true)
  vim.api.nvim_buf_set_lines(s.tree_bufnr, 0, -1, false, buf_lines)
  vim.api.nvim_buf_set_option(s.tree_bufnr, 'modifiable', false)
end

--- Get the node under the cursor in the tree buffer.
--- @param tree_bufnr number
--- @return table|nil node
--- @return number|nil source_bufnr
local function get_cursor_node(tree_bufnr)
  for src_bufnr, s in pairs(state) do
    if s.tree_bufnr == tree_bufnr then
      local row = vim.api.nvim_win_get_cursor(0)[1]
      local node = s.flat_nodes and s.flat_nodes[row]
      return node, src_bufnr
    end
  end
  return nil, nil
end

--- Set up keybindings for the tree buffer.
--- @param tree_bufnr number
local function setup_keymaps(tree_bufnr)
  local opts = { buffer = tree_bufnr, silent = true, noremap = true }

  -- Enter: jump to component in source
  vim.keymap.set('n', '<CR>', function()
    local node, src_bufnr = get_cursor_node(tree_bufnr)
    if not node or not src_bufnr then return end
    local line = find_component_line(src_bufnr, node.name)
    if not line then return end
    -- Focus the source window
    local s = state[src_bufnr]
    if not s then return end
    -- Find a window showing the source buffer
    for _, winid in ipairs(vim.api.nvim_list_wins()) do
      if vim.api.nvim_win_get_buf(winid) == src_bufnr then
        vim.api.nvim_set_current_win(winid)
        vim.api.nvim_win_set_cursor(winid, { line, 0 })
        vim.cmd('normal! zz')
        return
      end
    end
  end, opts)

  -- o / Space: toggle expand/collapse
  for _, key in ipairs({ 'o', '<Space>' }) do
    vim.keymap.set('n', key, function()
      local node, src_bufnr = get_cursor_node(tree_bufnr)
      if not node or #node.children == 0 then return end
      node.expanded = not node.expanded
      refresh(src_bufnr)
    end, opts)
  end

  -- d: decode scripts for component
  vim.keymap.set('n', 'd', function()
    local node, src_bufnr = get_cursor_node(tree_bufnr)
    if not node or not src_bufnr then return end
    if not node.has_scripts then
      vim.notify('No scripts on this component', vim.log.levels.INFO, { title = 'Ignition' })
      return
    end
    -- Find the component line and trigger decode from source window
    local line = find_component_line(src_bufnr, node.name)
    if not line then return end
    for _, winid in ipairs(vim.api.nvim_list_wins()) do
      if vim.api.nvim_win_get_buf(winid) == src_bufnr then
        vim.api.nvim_set_current_win(winid)
        vim.api.nvim_win_set_cursor(winid, { line, 0 })
        vim.cmd('IgnitionDecode')
        return
      end
    end
  end, opts)

  -- q: close tree
  vim.keymap.set('n', 'q', function()
    for src_bufnr, s in pairs(state) do
      if s.tree_bufnr == tree_bufnr then
        M.close(src_bufnr)
        return
      end
    end
  end, opts)

  -- R: refresh
  vim.keymap.set('n', 'R', function()
    local _, src_bufnr = get_cursor_node(tree_bufnr)
    if src_bufnr then
      refresh(src_bufnr)
    end
  end, opts)
end

--- Open the component tree sidebar for the current buffer.
function M.open()
  local source_bufnr = vim.api.nvim_get_current_buf()

  -- If already open, focus the tree window
  local s = state[source_bufnr]
  if s and vim.api.nvim_win_is_valid(s.tree_winid) then
    vim.api.nvim_set_current_win(s.tree_winid)
    return
  end

  -- Parse current buffer
  local lines_content = vim.api.nvim_buf_get_lines(source_bufnr, 0, -1, false)
  local json_str = table.concat(lines_content, '\n')
  local root_node, err = M.parse_view_json(json_str)
  if not root_node then
    vim.notify(err or 'Failed to parse view', vim.log.levels.WARN, { title = 'Ignition' })
    return
  end

  -- Get config
  local cfg = M.config
  local ignition_ok, ignition = pcall(require, 'ignition')
  if ignition_ok and ignition.config.component_tree then
    cfg = vim.tbl_deep_extend('force', cfg, ignition.config.component_tree)
  end

  -- Create the split
  local split_cmd = cfg.position == 'right' and 'botright' or 'topleft'
  vim.cmd(split_cmd .. ' ' .. cfg.width .. 'vnew')
  local tree_winid = vim.api.nvim_get_current_win()
  local tree_bufnr = vim.api.nvim_get_current_buf()

  -- Configure tree buffer
  vim.api.nvim_buf_set_name(tree_bufnr, 'ignition://component-tree/' .. source_bufnr)
  vim.bo[tree_bufnr].buftype = 'nofile'
  vim.bo[tree_bufnr].bufhidden = 'wipe'
  vim.bo[tree_bufnr].swapfile = false
  vim.bo[tree_bufnr].filetype = 'ignition_tree'
  vim.bo[tree_bufnr].modifiable = false

  -- Configure tree window
  vim.wo[tree_winid].number = false
  vim.wo[tree_winid].relativenumber = false
  vim.wo[tree_winid].signcolumn = 'no'
  vim.wo[tree_winid].foldcolumn = '0'
  vim.wo[tree_winid].cursorline = true
  vim.wo[tree_winid].wrap = false
  vim.wo[tree_winid].winfixwidth = true

  -- Store state
  local buf_lines, flat = render_tree(root_node)
  state[source_bufnr] = {
    tree_bufnr = tree_bufnr,
    tree_winid = tree_winid,
    root_node = root_node,
    flat_nodes = flat,
    source_bufnr = source_bufnr,
  }

  -- Render
  vim.api.nvim_buf_set_option(tree_bufnr, 'modifiable', true)
  vim.api.nvim_buf_set_lines(tree_bufnr, 0, -1, false, buf_lines)
  vim.api.nvim_buf_set_option(tree_bufnr, 'modifiable', false)

  -- Keymaps
  setup_keymaps(tree_bufnr)

  -- Auto-refresh on source buffer write
  local augroup = vim.api.nvim_create_augroup('IgnitionComponentTree_' .. source_bufnr, { clear = true })
  vim.api.nvim_create_autocmd('BufWritePost', {
    group = augroup,
    buffer = source_bufnr,
    callback = function()
      refresh(source_bufnr)
    end,
  })

  -- Clean up when tree buffer is wiped
  vim.api.nvim_create_autocmd('BufWipeout', {
    group = augroup,
    buffer = tree_bufnr,
    callback = function()
      state[source_bufnr] = nil
      pcall(vim.api.nvim_del_augroup_by_name, 'IgnitionComponentTree_' .. source_bufnr)
    end,
  })
end

--- Close the component tree sidebar for a source buffer.
--- @param source_bufnr number|nil defaults to current buffer
function M.close(source_bufnr)
  source_bufnr = source_bufnr or vim.api.nvim_get_current_buf()

  -- Also check if current buffer IS a tree buffer
  for src_bufnr, s in pairs(state) do
    if s.tree_bufnr == source_bufnr then
      source_bufnr = src_bufnr
      break
    end
  end

  local s = state[source_bufnr]
  if not s then return end

  if vim.api.nvim_win_is_valid(s.tree_winid) then
    vim.api.nvim_win_close(s.tree_winid, true)
  end
  state[source_bufnr] = nil
  pcall(vim.api.nvim_del_augroup_by_name, 'IgnitionComponentTree_' .. source_bufnr)
end

--- Toggle the component tree sidebar.
function M.toggle()
  local source_bufnr = vim.api.nvim_get_current_buf()

  -- Check if current buffer is a tree buffer
  for src_bufnr, s in pairs(state) do
    if s.tree_bufnr == source_bufnr then
      M.close(src_bufnr)
      return
    end
  end

  local s = state[source_bufnr]
  if s and vim.api.nvim_win_is_valid(s.tree_winid) then
    M.close(source_bufnr)
  else
    M.open()
  end
end

return M
