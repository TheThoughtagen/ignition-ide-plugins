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
 * Search all resources across the workspace using LSP workspace symbols.
 */
export async function searchResources(): Promise<void> {
  const client = getClient();
  if (!client) {
    vscode.window.showWarningMessage("LSP client not connected");
    return;
  }

  // Fetch all workspace symbols (empty query = return all)
  const symbols: vscode.SymbolInformation[] = await client.sendRequest(
    "workspace/symbol",
    { query: "" }
  );

  if (!symbols || symbols.length === 0) {
    vscode.window.showInformationMessage("No resources found. Is an Ignition project open?");
    return;
  }

  const items = symbols.map((sym) => ({
    label: `$(${symbolIcon(sym.kind)}) ${sym.name}`,
    description: sym.containerName ?? "",
    detail: sym.location.uri.fsPath,
    symbol: sym,
  }));

  const selected = await vscode.window.showQuickPick(items, {
    placeHolder: "Search resources (scripts, views, queries...)",
    matchOnDescription: true,
    matchOnDetail: true,
  });

  if (selected) {
    const uri = selected.symbol.location.uri;
    const line = selected.symbol.location.range.start.line;
    const doc = await vscode.workspace.openTextDocument(uri);
    const editor = await vscode.window.showTextDocument(doc);
    const pos = new vscode.Position(line, 0);
    editor.selection = new vscode.Selection(pos, pos);
    editor.revealRange(
      new vscode.Range(pos, pos),
      vscode.TextEditorRevealType.InCenter
    );
  }
}

function symbolIcon(kind: vscode.SymbolKind): string {
  switch (kind) {
    case vscode.SymbolKind.Module: return "symbol-module";
    case vscode.SymbolKind.Function: return "symbol-function";
    case vscode.SymbolKind.Event: return "symbol-event";
    default: return "symbol-misc";
  }
}

/**
 * Copy the qualified script path for the current symbol.
 *
 * Uses LSP workspace symbols to find the module path for the current file.
 */
export async function copyQualifiedPath(): Promise<void> {
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

  const fileUri = editor.document.uri.toString();

  // Find symbols matching the current file
  const symbols: vscode.SymbolInformation[] = await client.sendRequest(
    "workspace/symbol",
    { query: "" }
  );

  const match = symbols?.find((s) => s.location.uri.toString() === fileUri);
  if (match) {
    await vscode.env.clipboard.writeText(match.name);
    vscode.window.showInformationMessage(`Copied: ${match.name}`);
  } else {
    // Fallback: derive from file path
    const relativePath = vscode.workspace.asRelativePath(editor.document.uri);
    await vscode.env.clipboard.writeText(relativePath);
    vscode.window.showInformationMessage(`Copied: ${relativePath}`);
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
    "  Ignition: Format Ignition JSON",
    "  Ignition: Open with Kindling",
    "  Ignition: Debug LSP",
  ];

  const doc = await vscode.workspace.openTextDocument({
    content: lines.join("\n"),
    language: "plaintext",
  });
  await vscode.window.showTextDocument(doc);
}

/**
 * Format Ignition JSON with smart indentation.
 *
 * Respects JSON structure while keeping each existing line as a unit.
 * Ports the IgnitionFormat command from ignition-nvim.
 */
export async function formatIgnitionJson(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active editor");
    return;
  }

  const doc = editor.document;
  if (!doc.fileName.endsWith(".json")) {
    vscode.window.showWarningMessage("Not a JSON file");
    return;
  }

  const text = doc.getText();
  let formatted: string;
  try {
    const parsed = JSON.parse(text);
    formatted = JSON.stringify(parsed, null, 2);
  } catch {
    vscode.window.showErrorMessage("Invalid JSON — cannot format");
    return;
  }

  // Convert to tabs (Ignition convention for JSON)
  formatted = formatted.replace(/^( +)/gm, (match) => {
    const spaces = match.length;
    const tabs = Math.floor(spaces / 2);
    const remaining = spaces % 2;
    return "\t".repeat(tabs) + " ".repeat(remaining);
  });

  const fullRange = new vscode.Range(
    doc.positionAt(0),
    doc.positionAt(text.length)
  );

  const edit = new vscode.WorkspaceEdit();
  edit.replace(doc.uri, fullRange, formatted);
  await vscode.workspace.applyEdit(edit);

  vscode.window.showInformationMessage("Formatted Ignition JSON");
}

/**
 * Show LSP debug information for troubleshooting.
 *
 * Ports the IgnitionDebugLSP command from ignition-nvim.
 */
export async function debugLsp(): Promise<void> {
  const client = getClient();
  const editor = vscode.window.activeTextEditor;

  const lines: string[] = [
    "=== Ignition LSP Debug Info ===",
    "",
    `LSP Client: ${client ? "Active" : "Not connected"}`,
  ];

  if (client) {
    lines.push(`  State: ${client.state}`);
    lines.push(`  Server: ${client.outputChannel.name}`);
  }

  lines.push("");

  if (editor) {
    const doc = editor.document;
    lines.push(`Active Document:`);
    lines.push(`  URI: ${doc.uri.toString()}`);
    lines.push(`  Language: ${doc.languageId}`);
    lines.push(`  Scheme: ${doc.uri.scheme}`);
    lines.push(`  File: ${doc.fileName}`);
    lines.push(`  Lines: ${doc.lineCount}`);
  } else {
    lines.push("No active editor");
  }

  lines.push("");

  // Check workspace info
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (workspaceFolders) {
    lines.push("Workspace Folders:");
    for (const folder of workspaceFolders) {
      lines.push(`  ${folder.name}: ${folder.uri.fsPath}`);
    }
  }

  lines.push("");

  // Check for Ignition project markers
  const projectFiles = await vscode.workspace.findFiles(
    "**/project.json",
    "**/node_modules/**",
    5
  );
  lines.push(`Ignition Projects Found: ${projectFiles.length}`);
  for (const f of projectFiles) {
    lines.push(`  ${vscode.workspace.asRelativePath(f)}`);
  }

  const doc = await vscode.workspace.openTextDocument({
    content: lines.join("\n"),
    language: "plaintext",
  });
  await vscode.window.showTextDocument(doc);
}
