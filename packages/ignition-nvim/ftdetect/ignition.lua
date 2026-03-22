-- File type detection for Ignition files
-- This file is automatically sourced by Neovim when detecting file types

-- Gateway Backup files
vim.filetype.add({
  extension = {
    gwbk = 'ignition',
    proj = 'ignition',
  },
  filename = {
    -- Common Ignition resource files
    ['resource.json'] = 'ignition',
    ['tags.json'] = 'ignition',
    ['data.json'] = 'ignition',
    ['project.json'] = 'ignition',
  },
  pattern = {
    -- Ignition project structure patterns
    ['.*/com%.inductiveautomation%..*%.json'] = 'ignition',
    ['.*/ignition/.*%.json'] = 'ignition',

    -- Vision and Perspective components
    ['.*/vision/.*%.json'] = 'ignition',
    ['.*/perspective/.*%.json'] = 'ignition',

    -- Tag provider files
    ['.*/tags/.*%.json'] = 'ignition',

    -- Script library files
    ['.*/script%-python/.*%.json'] = 'ignition',
  },
})

-- Content-based detection for JSON files that might be Ignition resources
vim.api.nvim_create_autocmd({ 'BufRead', 'BufNewFile' }, {
  pattern = '*.json',
  callback = function(args)
    -- Don't override if filetype is already set to ignition
    if vim.bo[args.buf].filetype == 'ignition' then
      return
    end

    -- Read first few lines to detect Ignition-specific content
    local lines = vim.api.nvim_buf_get_lines(args.buf, 0, 50, false)
    local content = table.concat(lines, '\n')

    -- Check for Ignition-specific JSON markers
    local ignition_markers = {
      '"scope":%s*"[AG]"', -- Gateway or Application scope
      '"moduleId":%s*"com%.inductiveautomation%.',
      '"resourceType":', -- Perspective/Vision resources
      '"eventScripts":', -- Event script definitions
      '"script":%s*"[A-Za-z0-9+/]', -- Base64 encoded scripts
      '"params":%s*%[', -- Parameter definitions (Perspective)
      '"root":%s*{', -- Vision component root
      '"typeId":', -- Component type identifiers
    }

    for _, pattern in ipairs(ignition_markers) do
      if content:match(pattern) then
        vim.bo[args.buf].filetype = 'ignition'
        return
      end
    end
  end,
})
