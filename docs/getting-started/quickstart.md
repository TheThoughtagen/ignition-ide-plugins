# Edit an embedded script

[Watch the recorded walkthroughs](../demos.md) to see the tools in use.

Open a Perspective `view.json` that contains an event script or script transform. Keep it in a project checkout so you can inspect the diff after saving.

## Extract the script

| Editor | Action |
| --- | --- |
| VS Code | Run `Ignition: Decode Script at Cursor` from the Command Palette. |
| Neovim | Run `:IgnitionDecode` and select the script when prompted. |
| Zed | Use the `Ignition: Decode …` code action on the JSON resource. |

The extracted script can use API completions and hover documentation. Lint feedback requires the linter dependency, which needs Python 3.10+.

## Save the edit

In Neovim, save the extracted buffer with `:w`, then save the source JSON buffer. In VS Code, save the decoded script and inspect its source resource. In Zed, use `Ignition: Save … back to JSON` on the extracted file.

Review the source diff before committing. Editor checks do not execute the script on a gateway; test runtime behavior in your development project separately.

## If the script does not open

Check that the resource contains an embedded script, rather than only resource metadata. Confirm the language server is running and that your editor opened the project folder. Zed requires `project.json` at the worktree root.

See [script editing](../guides/script-editing.md) for extraction behavior and [installation](installation.md) for editor-specific links.
