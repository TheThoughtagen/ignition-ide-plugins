import * as vscode from "vscode";
import { startLspClient, stopLspClient } from "./lspClient";
import {
  ScriptFileSystemProvider,
  SCHEME,
} from "./scriptDocProvider";
import { IgnitionCodeLensProvider } from "./codeLensProvider";
import {
  ComponentTreeProvider,
  registerComponentTree,
} from "./componentTreeProvider";
import {
  ProjectBrowserProvider,
  registerProjectBrowser,
} from "./projectBrowserProvider";
import { openWithKindling } from "./kindling";
import {
  openScript,
  decodeScriptAtCursor,
  decodeAllScripts,
  listScripts,
  showInfo,
  formatIgnitionJson,
  debugLsp,
  searchResources,
  copyQualifiedPath,
} from "./commands";

let scriptFsProvider: ScriptFileSystemProvider;
let codeLensProvider: IgnitionCodeLensProvider;
let componentTreeProvider: ComponentTreeProvider;
let projectBrowserProvider: ProjectBrowserProvider;

export async function activate(
  context: vscode.ExtensionContext
): Promise<void> {
  // Initialize providers
  scriptFsProvider = new ScriptFileSystemProvider();
  codeLensProvider = new IgnitionCodeLensProvider();
  componentTreeProvider = new ComponentTreeProvider();

  // Register the virtual filesystem (editable virtual documents)
  context.subscriptions.push(
    vscode.workspace.registerFileSystemProvider(SCHEME, scriptFsProvider, {
      isCaseSensitive: true,
    })
  );

  // Register CodeLens provider for JSON files
  context.subscriptions.push(
    vscode.languages.registerCodeLensProvider(
      { scheme: "file", language: "json" },
      codeLensProvider
    )
  );

  // Register Component Tree view
  const treeView = vscode.window.createTreeView("ignitionComponentTree", {
    treeDataProvider: componentTreeProvider,
    showCollapseAll: true,
  });
  context.subscriptions.push(treeView);
  registerComponentTree(context, componentTreeProvider, scriptFsProvider);

  // Register Project Browser view
  projectBrowserProvider = new ProjectBrowserProvider();
  const projectTreeView = vscode.window.createTreeView("ignitionProjectBrowser", {
    treeDataProvider: projectBrowserProvider,
    showCollapseAll: true,
  });
  context.subscriptions.push(projectTreeView);
  registerProjectBrowser(context, projectBrowserProvider);

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ignition.openScript",
      (sourceUri: string, key: string, line: number) =>
        openScript(scriptFsProvider, sourceUri, key, line)
    ),
    vscode.commands.registerCommand("ignition.decodeScript", () =>
      decodeScriptAtCursor(scriptFsProvider)
    ),
    vscode.commands.registerCommand("ignition.decodeAll", () =>
      decodeAllScripts(scriptFsProvider)
    ),
    vscode.commands.registerCommand("ignition.listScripts", () =>
      listScripts(scriptFsProvider)
    ),
    vscode.commands.registerCommand("ignition.showInfo", () => showInfo()),
    vscode.commands.registerCommand("ignition.formatJson", () =>
      formatIgnitionJson()
    ),
    vscode.commands.registerCommand("ignition.debugLsp", () => debugLsp()),
    vscode.commands.registerCommand("ignition.openWithKindling", (uri?: vscode.Uri) =>
      openWithKindling(uri)
    ),
    vscode.commands.registerCommand("ignition.refreshComponentTree", () =>
      componentTreeProvider.refresh()
    ),
    vscode.commands.registerCommand("ignition.searchResources", () =>
      searchResources()
    ),
    vscode.commands.registerCommand("ignition.copyQualifiedPath", () =>
      copyQualifiedPath()
    ),
    vscode.commands.registerCommand("ignition.refreshProjectBrowser", () =>
      projectBrowserProvider.refresh()
    )
  );

  // Refresh CodeLens when a virtual script is saved (source JSON changed)
  context.subscriptions.push(
    scriptFsProvider.onDidChangeFile(() => {
      codeLensProvider.refresh();
    })
  );

  // Refresh CodeLens when config changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("ignition")) {
        codeLensProvider.refresh();
      }
    })
  );

  // Configure Python files to use tabs (Ignition convention)
  try {
    await configureIgnitionDefaults();
  } catch (err) {
    // Don't let config errors prevent extension activation
    console.error("Ignition: failed to set defaults:", err);
  }

  // Auto-convert spaces to tabs when opening Python files
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((doc) => {
      const autoConvert = vscode.workspace
        .getConfiguration("ignition")
        .get<boolean>("autoConvertTabs", true);
      if (autoConvert && doc.languageId === "python" && doc.uri.scheme === "file") {
        convertIndentationToTabs(doc).catch((err) => {
          console.error("Ignition: tab conversion failed:", err);
        });
      }
    })
  );

  // Manual command for converting indentation
  context.subscriptions.push(
    vscode.commands.registerCommand("ignition.convertToTabs", async () => {
      const doc = vscode.window.activeTextEditor?.document;
      if (doc) {
        await convertIndentationToTabs(doc);
        vscode.window.showInformationMessage("Converted indentation to tabs");
      }
    })
  );

  // Start the LSP client
  const client = await startLspClient(context);
  if (client) {
    context.subscriptions.push({ dispose: () => stopLspClient() });

    // Refresh CodeLens once LSP is ready (for JSON files already open)
    codeLensProvider.refresh();
  }
}

/**
 * Set workspace-level editor settings for Ignition projects.
 * Ignition stores Python scripts with tab indentation.
 */
async function configureIgnitionDefaults(): Promise<void> {
  const editorConfig = vscode.workspace.getConfiguration(
    "editor",
    { languageId: "python" }
  );

  // Only set if not already configured by the user at workspace level
  const inspect = editorConfig.inspect<boolean>("insertSpaces");
  if (
    inspect?.workspaceLanguageValue === undefined &&
    inspect?.workspaceFolderLanguageValue === undefined
  ) {
    await editorConfig.update("insertSpaces", false, vscode.ConfigurationTarget.Workspace, true);
    await editorConfig.update("tabSize", 4, vscode.ConfigurationTarget.Workspace, true);
  }
}

/**
 * Convert space indentation to tabs in a Python document.
 * Ignition expects tab-indented Python — this silently converts
 * when a file is opened so the user doesn't have to do it manually.
 */
async function convertIndentationToTabs(
  doc: vscode.TextDocument
): Promise<void> {
  // Only convert if the file has space indentation
  const firstIndentedLine = findFirstIndentedLine(doc);
  if (firstIndentedLine === -1) {
    return; // No indentation to convert
  }

  const lineText = doc.lineAt(firstIndentedLine).text;
  if (lineText.startsWith("\t")) {
    return; // Already using tabs
  }

  // Detect indent size (count leading spaces on first indented line)
  const spaces = lineText.match(/^( +)/)?.[1]?.length ?? 4;
  const indentSize = Math.min(spaces, 8); // Sanity cap

  const edit = new vscode.WorkspaceEdit();
  for (let i = 0; i < doc.lineCount; i++) {
    const line = doc.lineAt(i);
    const text = line.text;

    // Only convert leading whitespace
    const match = text.match(/^( +)/);
    if (!match) {
      continue;
    }

    const leadingSpaces = match[1].length;
    const tabCount = Math.floor(leadingSpaces / indentSize);
    const remainingSpaces = leadingSpaces % indentSize;
    const newIndent = "\t".repeat(tabCount) + " ".repeat(remainingSpaces);

    if (newIndent !== match[1]) {
      edit.replace(
        doc.uri,
        new vscode.Range(i, 0, i, leadingSpaces),
        newIndent
      );
    }
  }

  if (edit.size > 0) {
    await vscode.workspace.applyEdit(edit);
  }
}

function findFirstIndentedLine(doc: vscode.TextDocument): number {
  for (let i = 0; i < Math.min(doc.lineCount, 200); i++) {
    const text = doc.lineAt(i).text;
    if (text.startsWith(" ") || text.startsWith("\t")) {
      return i;
    }
  }
  return -1;
}

export function deactivate(): Thenable<void> | undefined {
  return stopLspClient();
}
