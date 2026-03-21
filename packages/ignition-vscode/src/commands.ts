import * as vscode from "vscode";
import { getClient } from "./lspClient";
import { buildScriptUri, ScriptFileSystemProvider, SCHEME } from "./scriptDocProvider";

interface ScriptInfo {
  key: string;
  line: number;
  content: string;
  context: string;
  decodedPreview: string;
}

/**
 * Open a decoded script in a virtual document tab.
 */
export async function openScript(
  provider: ScriptFileSystemProvider,
  sourceUri: string,
  key: string,
  line: number
): Promise<void> {
  const uri = buildScriptUri(sourceUri, key, line);

  // Preload the decoded content into the virtual filesystem
  await provider.preload(uri);

  // Open the virtual document — set language for syntax highlighting
  const doc = await vscode.workspace.openTextDocument(uri);
  const lang = key === "expression" ? "plaintext" : "python";
  await vscode.languages.setTextDocumentLanguage(doc, lang);
  await vscode.window.showTextDocument(doc, {
    preview: false,
    viewColumn: vscode.ViewColumn.Beside,
  });
}

/**
 * Decode the script closest to the cursor in the active editor.
 */
export async function decodeScriptAtCursor(
  provider: ScriptFileSystemProvider
): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active editor");
    return;
  }

  const client = getClient();
  if (!client) {
    vscode.window.showWarningMessage("LSP client not connected");
    return;
  }

  const scripts: ScriptInfo[] = await client.sendRequest(
    "ignition/findScripts",
    { uri: editor.document.uri.toString() }
  );

  if (scripts.length === 0) {
    vscode.window.showInformationMessage(
      "No embedded scripts found in this file"
    );
    return;
  }

  // Find the script closest to the cursor
  const cursorLine = editor.selection.active.line + 1; // 1-based
  let closest = scripts[0];
  let minDist = Math.abs(closest.line - cursorLine);

  for (const script of scripts) {
    const dist = Math.abs(script.line - cursorLine);
    if (dist < minDist) {
      closest = script;
      minDist = dist;
    }
  }

  await openScript(
    provider,
    editor.document.uri.toString(),
    closest.key,
    closest.line
  );
}

/**
 * Decode all scripts in the current file, opening each in a tab.
 */
export async function decodeAllScripts(
  provider: ScriptFileSystemProvider
): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active editor");
    return;
  }

  const client = getClient();
  if (!client) {
    vscode.window.showWarningMessage("LSP client not connected");
    return;
  }

  const scripts: ScriptInfo[] = await client.sendRequest(
    "ignition/findScripts",
    { uri: editor.document.uri.toString() }
  );

  if (scripts.length === 0) {
    vscode.window.showInformationMessage(
      "No embedded scripts found in this file"
    );
    return;
  }

  for (const script of scripts) {
    await openScript(
      provider,
      editor.document.uri.toString(),
      script.key,
      script.line
    );
  }

  vscode.window.showInformationMessage(
    `Opened ${scripts.length} script(s)`
  );
}

/**
 * Show a QuickPick listing all scripts in the workspace.
 */
export async function listScripts(
  provider: ScriptFileSystemProvider
): Promise<void> {
  const client = getClient();
  if (!client) {
    vscode.window.showWarningMessage("LSP client not connected");
    return;
  }

  // Find all JSON files in the workspace
  const jsonFiles = await vscode.workspace.findFiles(
    "**/*.json",
    "**/node_modules/**"
  );

  const allScripts: Array<{
    script: ScriptInfo;
    sourceUri: string;
    fileName: string;
  }> = [];

  for (const file of jsonFiles) {
    try {
      const scripts: ScriptInfo[] = await client.sendRequest(
        "ignition/findScripts",
        { uri: file.toString() }
      );

      for (const script of scripts) {
        allScripts.push({
          script,
          sourceUri: file.toString(),
          fileName: vscode.workspace.asRelativePath(file),
        });
      }
    } catch (err) {
      console.warn(`Ignition: failed to scan ${file.toString()}:`, err);
    }
  }

  if (allScripts.length === 0) {
    vscode.window.showInformationMessage(
      "No embedded scripts found in workspace"
    );
    return;
  }

  const items = allScripts.map((entry) => ({
    label: `$(symbol-event) ${entry.script.context}`,
    description: `${entry.script.key} @ line ${entry.script.line}`,
    detail: `${entry.fileName} — ${entry.script.decodedPreview}`,
    entry,
  }));

  const selected = await vscode.window.showQuickPick(items, {
    placeHolder: "Select a script to edit",
    matchOnDescription: true,
    matchOnDetail: true,
  });

  if (selected) {
    await openScript(
      provider,
      selected.entry.sourceUri,
      selected.entry.script.key,
      selected.entry.script.line
    );
  }
}

/**
 * Show extension info and LSP status.
 */
export async function showInfo(): Promise<void> {
  const client = getClient();
  const status = client ? "Connected" : "Not connected";

  const pkg = require("../../package.json");
  const lines = [
    `Ignition Dev Tools v${pkg.version}`,
    `LSP Status: ${status}`,
    "",
    "Commands:",
    "  Ignition: Decode Script at Cursor",
    "  Ignition: Decode All Scripts in File",
    "  Ignition: List All Scripts in Workspace",
  ];

  const doc = await vscode.workspace.openTextDocument({
    content: lines.join("\n"),
    language: "plaintext",
  });
  await vscode.window.showTextDocument(doc);
}
