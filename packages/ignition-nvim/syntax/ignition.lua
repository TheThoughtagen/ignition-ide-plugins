-- Syntax highlighting for Ignition files
-- This provides basic syntax highlighting with support for JSON and Python

-- Skip legacy syntax when treesitter is active
if vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()] then
  return
end

-- Only load once per buffer
if vim.b.current_syntax then
  return
end

-- Start with JSON syntax as base (most Ignition files are JSON)
vim.cmd('runtime! syntax/json.vim')

-- Unlet current_syntax so we can add more
vim.b.current_syntax = nil

-- Add Python syntax support for inline scripts
-- This will be more useful once we implement the decoder
vim.cmd('syntax include @Python syntax/python.vim')

-- Define regions for embedded Python scripts (base64 encoded)
-- Match common Ignition script field patterns
vim.cmd([[
  syntax region ignitionScript start=/"script":\s*"/ end=/"/ contains=@Python
  syntax region ignitionEventScript start=/"eventScript":\s*"/ end=/"/ contains=@Python
  syntax region ignitionCode start=/"code":\s*"/ end=/"/ contains=@Python
]])

-- Highlight Ignition-specific keywords in JSON
vim.cmd([[
  syntax keyword ignitionKeyword scope moduleId resourceType typeId componentType
  syntax keyword ignitionKeyword eventScripts params props meta custom root
  syntax keyword ignitionScope Gateway Application Session
  syntax keyword ignitionResourceType perspective-view vision-window
]])

-- Define highlight groups
vim.cmd([[
  highlight default link ignitionKeyword Keyword
  highlight default link ignitionScope Type
  highlight default link ignitionResourceType Type
  highlight default link ignitionScript String
  highlight default link ignitionEventScript String
  highlight default link ignitionCode String
]])

-- Special highlighting for Ignition module identifiers
vim.cmd([[
  syntax match ignitionModuleId /"com\.inductiveautomation\.[^"]*"/
  highlight default link ignitionModuleId Identifier
]])

-- Highlight Ignition system function calls
vim.cmd([[
  syntax match ignitionSystemCall /\<system\.\w\+\>/
  syntax match ignitionSharedCall /\<shared\.\w\+\>/
  highlight default link ignitionSystemCall Function
  highlight default link ignitionSharedCall Function
]])

vim.b.current_syntax = 'ignition'
