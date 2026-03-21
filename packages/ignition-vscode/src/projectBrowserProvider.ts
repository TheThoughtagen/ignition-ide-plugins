import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import {
  getResourceTypeLabel,
  getPrimaryCandidates,
  DEFAULT_PRIMARY,
} from "./lib/projectFiles.js";

/** Resource type display config (labels from lib, icons added here). */
const RESOURCE_TYPE_ICONS: Record<string, string> = {
  "script-python": "symbol-module",
  "perspective-views": "browser",
  "vision-windows": "window",
  "named-query": "database",
  "tags": "tag",
  "alarm-pipelines": "bell",
  "sfc": "git-merge",
  "reports": "file-text",
  "global-props": "globe",
  "scheduled": "clock",
  // com.inductiveautomation.* directories (ignition-git-module format)
  "com.inductiveautomation.perspective": "browser",
  "com.inductiveautomation.vision": "window",
  "com.inductiveautomation.reporting": "file-text",
  "com.inductiveautomation.alarm-notification": "bell",
  "com.inductiveautomation.webdev": "globe",
};

/** Map com.inductiveautomation.* dir names to display labels. */
const COM_IA_LABELS: Record<string, string> = {
  "com.inductiveautomation.perspective": "Perspective",
  "com.inductiveautomation.vision": "Vision",
  "com.inductiveautomation.reporting": "Reporting",
  "com.inductiveautomation.alarm-notification": "Alarm Notification",
  "com.inductiveautomation.webdev": "WebDev",
};

export type ProjectTreeItem = ProjectItem | ResourceTypeItem | ResourceItem;

/**
 * Root project node.
 */
export class ProjectItem extends vscode.TreeItem {
  constructor(
    public readonly projectPath: string,
    public readonly projectTitle: string
  ) {
    super(projectTitle, vscode.TreeItemCollapsibleState.Expanded);
    this.contextValue = "project";
    this.iconPath = new vscode.ThemeIcon("folder-library");
    this.tooltip = projectPath;
    this.description = path.basename(projectPath);
  }
}

/**
 * Resource type group (e.g., "Script Libraries", "Perspective Views").
 */
export class ResourceTypeItem extends vscode.TreeItem {
  constructor(
    public readonly projectPath: string,
    public readonly dirName: string,
    public readonly dirPath: string,
    childCount: number
  ) {
    const label = COM_IA_LABELS[dirName] ?? getResourceTypeLabel(dirName);
    const icon = RESOURCE_TYPE_ICONS[dirName] ?? "folder";
    super(label, vscode.TreeItemCollapsibleState.Collapsed);
    this.contextValue = "resourceType";
    this.iconPath = new vscode.ThemeIcon(icon);
    this.description = `${childCount}`;
    this.tooltip = dirPath;
  }
}

/**
 * Individual resource — represents a named directory like the Designer.
 *
 * Clicking opens the primary file (code.py, view.json, etc.).
 * Right-click "Reveal Files" shows individual files.
 */
export class ResourceItem extends vscode.TreeItem {
  public readonly resourcePath: string;
  public readonly primaryFilePath: string | undefined;
  public readonly parentType: string;
  public readonly hasChildResources: boolean;

  constructor(
    dirPath: string,
    parentType: string,
    childResourceCount: number,
    primaryFile: string | undefined
  ) {
    const name = path.basename(dirPath);
    const hasChildren = childResourceCount > 0;
    const state = hasChildren
      ? vscode.TreeItemCollapsibleState.Collapsed
      : vscode.TreeItemCollapsibleState.None;
    super(name, state);

    this.resourcePath = dirPath;
    this.parentType = parentType;
    this.hasChildResources = hasChildren;
    this.primaryFilePath = primaryFile;

    // Icon based on resource type
    if (parentType === "script-python") {
      this.iconPath = new vscode.ThemeIcon(
        hasChildren ? "symbol-package" : "symbol-method"
      );
    } else if (
      parentType === "perspective-views" ||
      parentType === "perspective-view"
    ) {
      this.iconPath = new vscode.ThemeIcon("browser");
    } else if (parentType === "named-query") {
      this.iconPath = new vscode.ThemeIcon("database");
    } else {
      this.iconPath = new vscode.ThemeIcon(
        hasChildren ? "folder" : "file"
      );
    }

    // Context value for menus
    this.contextValue = primaryFile ? "resourceWithFile" : "resourceFolder";
    this.tooltip = dirPath;

    // Click opens the primary file
    if (primaryFile) {
      this.command = {
        command: "vscode.open",
        title: "Open Resource",
        arguments: [vscode.Uri.file(primaryFile)],
      };
    }
  }
}

/**
 * Tree data provider for the Ignition Project Browser.
 *
 * Mirrors the Ignition Designer's project tree — resources are
 * directory names (leaves), clicking opens the primary file
 * (code.py, view.json, etc.).
 */
export class ProjectBrowserProvider
  implements vscode.TreeDataProvider<ProjectTreeItem>
{
  private _onDidChangeTreeData = new vscode.EventEmitter<
    ProjectTreeItem | undefined | void
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private projects: Array<{ path: string; title: string }> = [];

  constructor() {
    this.scanForProjects();
  }

  refresh(): void {
    this.scanForProjects();
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: ProjectTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: ProjectTreeItem): Promise<ProjectTreeItem[]> {
    if (!element) {
      if (this.projects.length === 0) {
        return [];
      }
      return this.projects.map((p) => new ProjectItem(p.path, p.title));
    }

    if (element instanceof ProjectItem) {
      return this.getResourceTypes(element.projectPath);
    }

    if (element instanceof ResourceTypeItem) {
      return this.getResourceChildren(element.dirPath, element.dirName);
    }

    if (element instanceof ResourceItem && element.hasChildResources) {
      return this.getResourceChildren(
        element.resourcePath,
        element.parentType
      );
    }

    return [];
  }

  // ── Project Discovery ──────────────────────────────────────────

  private scanForProjects(): void {
    this.projects = [];
    const folders = vscode.workspace.workspaceFolders;
    if (!folders) {
      return;
    }
    for (const folder of folders) {
      this.findProjectsIn(folder.uri.fsPath, 0);
    }
  }

  private findProjectsIn(dir: string, depth: number): void {
    if (depth > 3) {
      return;
    }
    const projectJson = path.join(dir, "project.json");
    if (fs.existsSync(projectJson)) {
      try {
        const data = JSON.parse(fs.readFileSync(projectJson, "utf-8"));
        this.projects.push({
          path: dir,
          title: data.title ?? path.basename(dir),
        });
      } catch (err) {
        console.warn(`Ignition: failed to parse ${projectJson}:`, err);
        this.projects.push({ path: dir, title: path.basename(dir) });
      }
      return;
    }
    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        if (
          entry.isDirectory() &&
          !entry.name.startsWith(".") &&
          entry.name !== "node_modules"
        ) {
          this.findProjectsIn(path.join(dir, entry.name), depth + 1);
        }
      }
    } catch (err) {
      console.warn(`Ignition: failed to read directory ${dir}:`, err);
    }
  }

  // ── Resource Type Groups ───────────────────────────────────────

  private getResourceTypes(projectPath: string): ResourceTypeItem[] {
    const items: ResourceTypeItem[] = [];

    // 1. Scan ignition/ subdirectory (standard Ignition project format)
    const ignitionDir = path.join(projectPath, "ignition");
    if (fs.existsSync(ignitionDir)) {
      try {
        const entries = fs.readdirSync(ignitionDir, { withFileTypes: true });
        for (const entry of entries) {
          if (!entry.isDirectory()) {
            continue;
          }
          const dirPath = path.join(ignitionDir, entry.name);
          const count = this.countChildResources(dirPath);
          if (count > 0) {
            items.push(
              new ResourceTypeItem(projectPath, entry.name, dirPath, count)
            );
          }
        }
      } catch (err) {
        console.warn(`Ignition: failed to read ignition/ dir:`, err);
      }
    }

    // 2. Scan com.inductiveautomation.* directories at project root
    //    (ignition-git-module format)
    try {
      const rootEntries = fs.readdirSync(projectPath, { withFileTypes: true });
      for (const entry of rootEntries) {
        if (
          !entry.isDirectory() ||
          !entry.name.startsWith("com.inductiveautomation.")
        ) {
          continue;
        }
        const dirPath = path.join(projectPath, entry.name);
        const count = this.countChildResources(dirPath);
        if (count > 0) {
          items.push(
            new ResourceTypeItem(projectPath, entry.name, dirPath, count)
          );
        }
      }
    } catch (err) {
      console.warn(`Ignition: failed to scan project root:`, err);
    }

    return items;
  }

  // ── Resource Children (Designer-style) ─────────────────────────

  /**
   * Get child resources for a directory.
   *
   * Each subdirectory is a resource. Only subdirectories are shown
   * as tree nodes (like the Designer). Files are hidden — the primary
   * file opens on click.
   */
  private getResourceChildren(
    dirPath: string,
    parentType: string
  ): ResourceItem[] {
    const items: ResourceItem[] = [];
    try {
      const entries = fs
        .readdirSync(dirPath, { withFileTypes: true })
        .filter((e) => e.isDirectory())
        .sort((a, b) => a.name.localeCompare(b.name));

      for (const entry of entries) {
        const childPath = path.join(dirPath, entry.name);
        const childResourceCount = this.countChildResources(childPath);
        const primaryFile = this.findPrimaryFile(childPath, parentType);
        items.push(
          new ResourceItem(
            childPath,
            parentType,
            childResourceCount,
            primaryFile
          )
        );
      }
    } catch (err) {
      console.warn(`Ignition: failed to read resources in ${dirPath}:`, err);
    }
    return items;
  }

  /**
   * Find the primary file for a resource directory.
   * This is the file opened when the user clicks the resource.
   */
  private findPrimaryFile(
    dirPath: string,
    resourceType: string
  ): string | undefined {
    const candidates = getPrimaryCandidates(resourceType);

    for (const filename of candidates) {
      const fullPath = path.join(dirPath, filename);
      if (fs.existsSync(fullPath)) {
        return fullPath;
      }
    }

    // Fallback: any .py, .json, or .sql file
    try {
      const entries = fs.readdirSync(dirPath);
      for (const ext of [".py", ".json", ".sql"]) {
        const match = entries.find((e) => e.endsWith(ext));
        if (match) {
          return path.join(dirPath, match);
        }
      }
    } catch (err) {
      console.warn(`Ignition: failed to scan ${dirPath} for files:`, err);
    }
    return undefined;
  }

  /**
   * Count subdirectories that are child resources (not files).
   */
  private countChildResources(dirPath: string): number {
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });
      return entries.filter((e) => e.isDirectory()).length;
    } catch (err) {
      console.warn(`Ignition: failed to count resources in ${dirPath}:`, err);
      return 0;
    }
  }

  dispose(): void {
    this._onDidChangeTreeData.dispose();
  }
}

/**
 * Register project browser commands.
 */
export function registerProjectBrowser(
  context: vscode.ExtensionContext,
  provider: ProjectBrowserProvider
): void {
  // Reveal files in a resource directory
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ignition.projectBrowser.revealFiles",
      async (item: ResourceItem) => {
        if (!item?.resourcePath) {
          return;
        }
        // Open the directory in the Explorer
        const uri = vscode.Uri.file(item.resourcePath);
        await vscode.commands.executeCommand("revealInExplorer", uri);
      }
    )
  );

  // View docs — find and open .md files in or near the resource directory
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "ignition.projectBrowser.viewDocs",
      async (item: ProjectItem | ResourceTypeItem | ResourceItem) => {
        let searchDir: string;
        if (item instanceof ProjectItem) {
          searchDir = item.projectPath;
        } else if (item instanceof ResourceTypeItem) {
          searchDir = item.dirPath;
        } else if (item instanceof ResourceItem) {
          searchDir = item.resourcePath;
        } else {
          return;
        }

        const mdFiles = findMarkdownFiles(searchDir);
        if (mdFiles.length === 0) {
          vscode.window.showInformationMessage("No documentation files found");
          return;
        }

        if (mdFiles.length === 1) {
          const doc = await vscode.workspace.openTextDocument(
            vscode.Uri.file(mdFiles[0])
          );
          await vscode.window.showTextDocument(doc);
          return;
        }

        // Multiple docs — show picker
        const items = mdFiles.map((f) => ({
          label: path.basename(f),
          description: path.relative(searchDir, f),
          filePath: f,
        }));

        const selected = await vscode.window.showQuickPick(items, {
          placeHolder: "Select documentation to view",
        });

        if (selected) {
          const doc = await vscode.workspace.openTextDocument(
            vscode.Uri.file(selected.filePath)
          );
          await vscode.window.showTextDocument(doc);
        }
      }
    )
  );

  // Watch filesystem for changes and refresh
  const watcher = vscode.workspace.createFileSystemWatcher(
    "**/{resource.json,view.json,code.py,project.json}"
  );
  watcher.onDidCreate(() => provider.refresh());
  watcher.onDidDelete(() => provider.refresh());
  context.subscriptions.push(watcher);
}

/**
 * Find .md files in a directory (non-recursive, max 2 levels deep).
 */
function findMarkdownFiles(dir: string, depth = 0): string[] {
  const results: string[] = [];
  if (depth > 2) {
    return results;
  }
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isFile() && entry.name.endsWith(".md")) {
        results.push(fullPath);
      } else if (
        entry.isDirectory() &&
        !entry.name.startsWith(".") &&
        entry.name !== "node_modules"
      ) {
        results.push(...findMarkdownFiles(fullPath, depth + 1));
      }
    }
  } catch (err) {
    console.warn(`Ignition: failed to scan ${dir} for docs:`, err);
  }
  return results;
}
