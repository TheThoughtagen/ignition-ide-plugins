import * as vscode from "vscode";

export interface IgnitionConfig {
  lspPath: string;
  ignitionVersion: string;
  codeLensEnabled: boolean;
  diagnosticsEnabled: boolean;
}

export function getConfig(): IgnitionConfig {
  const cfg = vscode.workspace.getConfiguration("ignition");
  return {
    lspPath: cfg.get<string>("lsp.path", ""),
    ignitionVersion: cfg.get<string>("ignitionVersion", "8.1"),
    codeLensEnabled: cfg.get<boolean>("codeLens.enabled", true),
    diagnosticsEnabled: cfg.get<boolean>("diagnostics.enabled", true),
  };
}
