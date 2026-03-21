import * as vscode from "vscode";
import { ScriptFileSystemProvider } from "./scriptDocProvider";
import { openScript } from "./commands";
import {
  type ComponentNode,
  isPerspectiveView,
  parseViewJson,
} from "./lib/componentTree.js";

export { type ComponentNode };

export class ComponentTreeItem extends vscode.TreeItem {
  constructor(
    public readonly node: ComponentNode,
    public readonly sourceUri: vscode.Uri,
    collapsibleState: vscode.TreeItemCollapsibleState
  ) {
    super(node.name, collapsibleState);

    this.description = node.shortType;
    this.tooltip = `${node.name} (${node.type})`;

    if (node.hasScripts) {
      this.description += "  [scripts]";
      this.contextValue = "componentWithScripts";
    } else {
      this.contextValue = "component";
    }

    // Click navigates to component in source
    this.command = {
      command: "ignition.componentTree.reveal",
      title: "Go to Component",
      arguments: [this],
    };
  }
}

/**
 * Provides a tree view of Perspective component hierarchy.
 *
 * Uses pure parsing logic from lib/componentTree.ts (shared with tests).
 */
export class ComponentTreeProvider
  implements vscode.TreeDataProvider<ComponentTreeItem>
{
  private _onDidChangeTreeData = new vscode.EventEmitter<
    ComponentTreeItem | undefined | void
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private rootNode: ComponentNode | undefined;
  private sourceUri: vscode.Uri | undefined;

  refresh(): void {
    this.rootNode = undefined;
    this.sourceUri = undefined;

    const editor = vscode.window.activeTextEditor;
    if (editor && editor.document.fileName.endsWith(".json")) {
      try {
        const data = JSON.parse(editor.document.getText());
        if (isPerspectiveView(data)) {
          this.sourceUri = editor.document.uri;
          this.rootNode = parseViewJson(editor.document.getText());
        }
      } catch {
        // Not valid JSON
      }
    }

    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: ComponentTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: ComponentTreeItem): ComponentTreeItem[] {
    if (!this.rootNode || !this.sourceUri) {
      return [];
    }

    const children = element ? element.node.children : [this.rootNode];
    return children.map((child) => {
      const state =
        child.children.length > 0
          ? vscode.TreeItemCollapsibleState.Expanded
          : vscode.TreeItemCollapsibleState.None;
      return new ComponentTreeItem(child, this.sourceUri!, state);
    });
  }

  dispose(): void {
    this._onDidChangeTreeData.dispose();
  }
}

/**
 * Register component tree commands and event handlers.
 */
export function registerComponentTree(
  context: vscode.ExtensionContext,
  provider: ComponentTreeProvider,
  scriptFsProvider: ScriptFileSystemProvider
): void {
  // Reveal component in source editor
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ignition.componentTree.reveal",
      async (item: ComponentTreeItem) => {
        try {
          const doc = await vscode.workspace.openTextDocument(item.sourceUri);
          const editor = await vscode.window.showTextDocument(doc, {
            preserveFocus: true,
            viewColumn: vscode.ViewColumn.One,
          });

          const text = doc.getText();
          const pattern = `"name"\\s*:\\s*"${escapeRegex(item.node.name)}"`;
          const match = text.match(new RegExp(pattern));
          if (match && match.index !== undefined) {
            const pos = doc.positionAt(match.index);
            editor.selection = new vscode.Selection(pos, pos);
            editor.revealRange(
              new vscode.Range(pos, pos),
              vscode.TextEditorRevealType.InCenter
            );
          }
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : String(err);
          vscode.window.showErrorMessage(`Failed to reveal component: ${message}`);
        }
      }
    )
  );

  // Decode scripts for a component
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ignition.componentTree.decodeScripts",
      async (item: ComponentTreeItem) => {
        try {
          if (!item.node.hasScripts) {
            vscode.window.showInformationMessage(
              "No scripts on this component"
            );
            return;
          }

          const doc = await vscode.workspace.openTextDocument(item.sourceUri);
          const text = doc.getText();
          const pattern = `"name"\\s*:\\s*"${escapeRegex(item.node.name)}"`;
          const match = text.match(new RegExp(pattern));
          if (match && match.index !== undefined) {
            const pos = doc.positionAt(match.index);
            const line = pos.line + 1; // 1-based

            const { getClient } = await import("./lspClient.js");
            const client = getClient();
            if (!client) {
              vscode.window.showWarningMessage("LSP client not connected");
              return;
            }

            interface ScriptInfo {
              key: string;
              line: number;
              context: string;
            }

            const scripts: ScriptInfo[] = await client.sendRequest(
              "ignition/findScripts",
              { uri: item.sourceUri.toString() }
            );

            const nearby = scripts.filter(
              (s) => Math.abs(s.line - line) < 50
            );

            for (const script of nearby) {
              await openScript(
                scriptFsProvider,
                item.sourceUri.toString(),
                script.key,
                script.line
              );
            }

            if (nearby.length === 0) {
              vscode.window.showInformationMessage(
                "No scripts found near this component"
              );
            }
          }
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : String(err);
          vscode.window.showErrorMessage(`Failed to decode component scripts: ${message}`);
        }
      }
    )
  );

  // Refresh on active editor change
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(() => {
      provider.refresh();
    })
  );

  // Refresh on document save
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(() => {
      provider.refresh();
    })
  );

  // Initial refresh
  provider.refresh();
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
