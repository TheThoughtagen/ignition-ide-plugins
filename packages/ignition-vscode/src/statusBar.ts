import * as vscode from "vscode";
import { getClient } from "./lspClient";

let statusBarItem: vscode.StatusBarItem;
let updateInterval: ReturnType<typeof setInterval>;

/**
 * Create and register the Ignition status bar item.
 *
 * Shows LSP connection state in the bottom status bar.
 */
export function createStatusBar(context: vscode.ExtensionContext): void {
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    50
  );
  statusBarItem.command = "ignition.debugLsp";
  statusBarItem.tooltip = "Ignition LSP Status (click for details)";
  context.subscriptions.push(statusBarItem);

  updateStatus();

  // Refresh status periodically and on editor change
  updateInterval = setInterval(updateStatus, 5000);
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(updateStatus)
  );
  context.subscriptions.push({
    dispose: () => clearInterval(updateInterval),
  });
}

function updateStatus(): void {
  const client = getClient();
  const editor = vscode.window.activeTextEditor;

  // Only show for relevant file types
  if (editor) {
    const lang = editor.document.languageId;
    const scheme = editor.document.uri.scheme;
    const relevant =
      lang === "python" ||
      lang === "json" ||
      lang === "ignition" ||
      scheme === "ignition-script";

    if (!relevant) {
      statusBarItem.hide();
      return;
    }
  }

  if (client) {
    statusBarItem.text = "$(flame) Ignition LSP";
    statusBarItem.backgroundColor = undefined;
  } else {
    statusBarItem.text = "$(flame) Ignition LSP (offline)";
    statusBarItem.backgroundColor = new vscode.ThemeColor(
      "statusBarItem.warningBackground"
    );
  }

  statusBarItem.show();
}
