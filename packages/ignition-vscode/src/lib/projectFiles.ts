/**
 * Pure logic for Ignition project file detection and mapping.
 *
 * No VS Code dependency — testable in plain Node.
 */

/** Known resource type directories and their display labels. */
export const RESOURCE_TYPES: Record<string, string> = {
  "script-python": "Script Libraries",
  "perspective-views": "Perspective Views",
  "vision-windows": "Vision Windows",
  "named-query": "Named Queries",
  "tags": "Tags",
  "alarm-pipelines": "Alarm Pipelines",
  "sfc": "Sequential Function Charts",
  "reports": "Reports",
  "global-props": "Global Props",
  "scheduled": "Scheduled Scripts",
};

/**
 * Maps resource type to the primary file the user wants to edit.
 * Checked in order — first match wins.
 */
export const PRIMARY_FILES: Record<string, string[]> = {
  "script-python": ["code.py"],
  "perspective-views": ["view.json"],
  "perspective-view": ["view.json"],
  "vision-windows": ["resource.json"],
  "vision-window": ["resource.json"],
  "named-query": ["query.sql", "resource.json"],
  "tags": ["tags.json"],
  "scheduled": ["resource.json"],
};

/** Fallback order for any resource type. */
export const DEFAULT_PRIMARY = [
  "code.py",
  "view.json",
  "query.sql",
  "resource.json",
  "data.json",
  "tags.json",
];

/**
 * Get the ordered list of candidate primary files for a resource type.
 */
export function getPrimaryCandidates(resourceType: string): string[] {
  return PRIMARY_FILES[resourceType] ?? DEFAULT_PRIMARY;
}

/**
 * File extensions that Kindling can open.
 */
export const KINDLING_EXTENSIONS = [".gwbk", ".modl", ".idb", ".log"];

/**
 * Check if a file extension is supported by Kindling.
 */
export function isKindlingFile(ext: string): boolean {
  return KINDLING_EXTENSIONS.includes(ext.toLowerCase());
}

/**
 * Derive a human-readable resource type label from a directory name.
 */
export function getResourceTypeLabel(dirName: string): string {
  return RESOURCE_TYPES[dirName] ?? dirName;
}
