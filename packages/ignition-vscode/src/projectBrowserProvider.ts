import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

/** Known resource type directories and their display names. */
const RESOURCE_TYPES: Record<string, { label: string; icon: string }> = {
  "script-python": { label: "Script Libraries", icon: "symbol-module" },
  "perspective-views": { label: "Perspective Views", icon: "browser" },
  "vision-windows": { label: "Vision Windows", icon: "window" },
  "named-query": { label: "Named Queries", icon: "database" },
  "tags": { label: "Tags", icon: "tag" },
  "alarm-pipelines": { label: "Alarm Pipelines", icon: "bell" },
  "sfc": { label: "Sequential Function Charts", icon: "git-merge" },
  "reports": { label: "Reports", icon: "file-text" },
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
    const meta = RESOURCE_TYPES[dirName] ?? {
      label: dirName,
      icon: "folder",
    };
    super(meta.label, vscode.TreeItemCollapsibleState.Collapsed);
    this.contextValue = "resourceType";
    this.iconPath = new vscode.ThemeIcon(meta.icon);
    this.description = `${childCount}`;
    this.tooltip = dirPath;
  }
}

/**
 * Individual resource (script module, view, query, etc.).
 */
export class ResourceItem extends vscode.TreeItem {
  public readonly resourcePath: string;
  public readonly isDirectory: boolean;

  constructor(
    public readonly itemPath: string,
    public readonly parentType: string,
    hasChildren: boolean
  ) {
    const name = path.basename(itemPath);
    const state = hasChildren
      ? vscode.TreeItemCollapsibleState.Collapsed
      : vscode.TreeItemCollapsibleState.None;
    super(name, state);

    this.resourcePath = itemPath;
    this.isDirectory = hasChildren;
    this.contextValue = hasChildren ? "resourceFolder" : "resource";
    this.tooltip = itemPath;

    // Set icon based on content
    if (hasChildren) {
      this.iconPath = new vscode.ThemeIcon("folder");
    } else if (name.endsWith(".py")) {
      this.iconPath = new vscode.ThemeIcon("symbol-method");
      this.description = "py";
    } else if (name === "view.json") {
      this.iconPath = new vscode.ThemeIcon("browser");
      this.description = "view";
    } else if (name === "resource.json") {
      this.iconPath = new vscode.ThemeIcon("json");
    } else if (name.endsWith(".json")) {
      this.iconPath = new vscode.ThemeIcon("json");
    } else {
      this.iconPath = new vscode.ThemeIcon("file");
    }

    // Click opens file
    if (!hasChildren) {
      this.command = {
        command: "vscode.open",
        title: "Open File",
        arguments: [vscode.Uri.file(itemPath)],
      };
    }
  }
}

/**
 * Tree data provider for the Ignition Project Browser.
 *
 * Scans workspace for project.json files and displays the resource
 * hierarchy grouped by type (scripts, views, queries, tags, etc.).
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
      // Root level — show projects
      if (this.projects.length === 0) {
        return [];
      }
      return this.projects.map(
        (p) => new ProjectItem(p.path, p.title)
      );
    }

    if (element instanceof ProjectItem) {
      return this.getResourceTypes(element.projectPath);
    }

    if (element instanceof ResourceTypeItem) {
      return this.getResources(element.dirPath, element.dirName);
    }

    if (element instanceof ResourceItem && element.isDirectory) {
      return this.getResources(element.resourcePath, element.parentType);
    }

    return [];
  }

  /**
   * Scan workspace for Ignition projects.
   */
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
      return; // Don't recurse too deep
    }

    const projectJson = path.join(dir, "project.json");
    if (fs.existsSync(projectJson)) {
      try {
        const data = JSON.parse(
          fs.readFileSync(projectJson, "utf-8")
        );
        this.projects.push({
          path: dir,
          title: data.title ?? path.basename(dir),
        });
      } catch {
        this.projects.push({
          path: dir,
          title: path.basename(dir),
        });
      }
      return; // Don't recurse into projects
    }

    // Look in subdirectories
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
    } catch {
      // Permission denied, etc.
    }
  }

  /**
   * Get resource type groups for a project.
   */
  private getResourceTypes(projectPath: string): ResourceTypeItem[] {
    const ignitionDir = path.join(projectPath, "ignition");
    if (!fs.existsSync(ignitionDir)) {
      return [];
    }

    const items: ResourceTypeItem[] = [];
    try {
      const entries = fs.readdirSync(ignitionDir, { withFileTypes: true });
      for (const entry of entries) {
        if (!entry.isDirectory()) {
          continue;
        }
        const dirPath = path.join(ignitionDir, entry.name);
        const count = this.countResources(dirPath);
        if (count > 0) {
          items.push(
            new ResourceTypeItem(projectPath, entry.name, dirPath, count)
          );
        }
      }
    } catch {
      // Can't read directory
    }

    return items;
  }

  /**
   * Get resources within a directory.
   */
  private getResources(
    dirPath: string,
    parentType: string
  ): ResourceItem[] {
    const items: ResourceItem[] = [];
    try {
      const entries = fs
        .readdirSync(dirPath, { withFileTypes: true })
        .sort((a, b) => {
          // Directories first, then files
          if (a.isDirectory() && !b.isDirectory()) {return -1;}
          if (!a.isDirectory() && b.isDirectory()) {return 1;}
          return a.name.localeCompare(b.name);
        });

      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);

        if (entry.isDirectory()) {
          // Show directory if it has meaningful content
          const hasContent = this.hasResourceContent(fullPath);
          if (hasContent) {
            items.push(new ResourceItem(fullPath, parentType, true));
          }
        } else if (
          entry.name.endsWith(".py") ||
          entry.name.endsWith(".json") ||
          entry.name.endsWith(".sql")
        ) {
          items.push(new ResourceItem(fullPath, parentType, false));
        }
      }
    } catch {
      // Can't read directory
    }
    return items;
  }

  /**
   * Count meaningful resources in a directory.
   */
  private countResources(dirPath: string): number {
    let count = 0;
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isDirectory()) {
          count++;
        } else if (
          entry.name.endsWith(".py") ||
          entry.name === "view.json" ||
          entry.name === "resource.json"
        ) {
          count++;
        }
      }
    } catch {
      // ignore
    }
    return count;
  }

  /**
   * Check if a directory has meaningful resource content.
   */
  private hasResourceContent(dirPath: string): boolean {
    try {
      const entries = fs.readdirSync(dirPath);
      return entries.some(
        (e) =>
          e.endsWith(".py") ||
          e.endsWith(".json") ||
          e.endsWith(".sql") ||
          fs.statSync(path.join(dirPath, e)).isDirectory()
      );
    } catch {
      return false;
    }
  }

  dispose(): void {
    this._onDidChangeTreeData.dispose();
  }
}
