import { describe, it, expect } from "vitest";
import {
  getPrimaryCandidates,
  isKindlingFile,
  getResourceTypeLabel,
  RESOURCE_TYPES,
  KINDLING_EXTENSIONS,
} from "../src/lib/projectFiles.js";

describe("getPrimaryCandidates", () => {
  it("returns code.py for script-python", () => {
    expect(getPrimaryCandidates("script-python")).toEqual(["code.py"]);
  });

  it("returns view.json for perspective-views", () => {
    expect(getPrimaryCandidates("perspective-views")).toEqual(["view.json"]);
  });

  it("returns query.sql first for named-query", () => {
    const candidates = getPrimaryCandidates("named-query");
    expect(candidates[0]).toBe("query.sql");
    expect(candidates).toContain("resource.json");
  });

  it("returns default list for unknown type", () => {
    const candidates = getPrimaryCandidates("unknown-type");
    expect(candidates).toContain("code.py");
    expect(candidates).toContain("view.json");
    expect(candidates).toContain("resource.json");
  });
});

describe("isKindlingFile", () => {
  it("accepts .gwbk files", () => {
    expect(isKindlingFile(".gwbk")).toBe(true);
  });

  it("accepts .modl files", () => {
    expect(isKindlingFile(".modl")).toBe(true);
  });

  it("accepts .idb files", () => {
    expect(isKindlingFile(".idb")).toBe(true);
  });

  it("accepts .log files", () => {
    expect(isKindlingFile(".log")).toBe(true);
  });

  it("is case insensitive", () => {
    expect(isKindlingFile(".GWBK")).toBe(true);
    expect(isKindlingFile(".Modl")).toBe(true);
  });

  it("rejects .json files", () => {
    expect(isKindlingFile(".json")).toBe(false);
  });

  it("rejects .py files", () => {
    expect(isKindlingFile(".py")).toBe(false);
  });
});

describe("getResourceTypeLabel", () => {
  it("returns label for known types", () => {
    expect(getResourceTypeLabel("script-python")).toBe("Script Libraries");
    expect(getResourceTypeLabel("perspective-views")).toBe("Perspective Views");
    expect(getResourceTypeLabel("named-query")).toBe("Named Queries");
  });

  it("returns dir name for unknown types", () => {
    expect(getResourceTypeLabel("custom-stuff")).toBe("custom-stuff");
  });
});

describe("RESOURCE_TYPES", () => {
  it("has all standard Ignition resource types", () => {
    expect(RESOURCE_TYPES).toHaveProperty("script-python");
    expect(RESOURCE_TYPES).toHaveProperty("perspective-views");
    expect(RESOURCE_TYPES).toHaveProperty("vision-windows");
    expect(RESOURCE_TYPES).toHaveProperty("named-query");
    expect(RESOURCE_TYPES).toHaveProperty("tags");
  });
});

describe("KINDLING_EXTENSIONS", () => {
  it("includes .gwbk", () => {
    expect(KINDLING_EXTENSIONS).toContain(".gwbk");
  });

  it("includes .modl", () => {
    expect(KINDLING_EXTENSIONS).toContain(".modl");
  });
});
