-- Quick diagnostic for LSP hover issues
-- Run with: :luafile dev-scripts/diagnose-hover.lua

local function log(msg)
  print("[HOVER-DIAG] " .. msg)
end

log("=== Ignition LSP Hover Diagnostic ===")

-- 1. Check buffer info
local bufnr = vim.api.nvim_get_current_buf()
local bufname = vim.api.nvim_buf_get_name(bufnr)
local filetype = vim.bo[bufnr].filetype

log("\n1. Buffer Info:")
log("   File: " .. bufname)
log("   Filetype: " .. filetype)

-- 2. Check LSP clients
local clients = vim.lsp.get_clients({ bufnr = bufnr })

log("\n2. LSP Clients Attached: " .. #clients)
if #clients == 0 then
  log("   ✗ NO LSP CLIENTS ATTACHED!")
  log("   Try: :LspStart ignition_lsp")
  log("   Or check if you're in an Ignition project (has project.json)")
  return
end

for _, client in ipairs(clients) do
  log("   ✓ " .. client.name .. " (id=" .. client.id .. ")")
  log("     root_dir: " .. (client.config.root_dir or "none"))

  local cap = client.server_capabilities
  log("     Capabilities:")
  log("       - hoverProvider: " .. tostring(cap.hoverProvider or false))
  log("       - completionProvider: " .. tostring(cap.completionProvider ~= nil))
  log("       - definitionProvider: " .. tostring(cap.definitionProvider or false))
end

-- 3. Check current word
local line = vim.api.nvim_get_current_line()
local col = vim.api.nvim_win_get_cursor(0)[2]
local word = vim.fn.expand('<cword>')

log("\n3. Current Cursor Position:")
log("   Line: " .. line)
log("   Column: " .. col)
log("   Word under cursor: '" .. word .. "'")

-- 4. Test hover request
log("\n4. Testing Hover Request...")
local params = vim.lsp.util.make_position_params()
log("   Position params: line=" .. params.position.line .. ", char=" .. params.position.character)

local hover_received = false
vim.lsp.buf_request(bufnr, 'textDocument/hover', params, function(err, result, ctx, config)
  hover_received = true
  if err then
    log("   ✗ Error: " .. vim.inspect(err))
  elseif result and result.contents then
    log("   ✓ Hover result received:")
    if type(result.contents) == 'string' then
      log("      " .. result.contents:gsub("\n", "\n      "))
    elseif result.contents.value then
      log("      " .. result.contents.value:gsub("\n", "\n      "))
    else
      log("      " .. vim.inspect(result.contents))
    end
  else
    log("   ✗ No hover information available for '" .. word .. "'")
    log("      (This might be expected if it's not an Ignition/Java symbol)")
  end
end)

-- Wait for response
vim.wait(2000, function() return hover_received end, 100)
if not hover_received then
  log("   ✗ Hover request timed out (LSP not responding)")
end

log("\n5. Server Logs:")
log("   Check /tmp/ignition-lsp.log for detailed server output")
log("   Run: tail -f /tmp/ignition-lsp.log")

log("\n=== Diagnostic Complete ===")
