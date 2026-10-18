import { afterEach, describe, expect, it, vi } from "vitest";

import { getRepoLinks, PROJECT, repoLinksFrom } from "../config";

afterEach(() => vi.unstubAllEnvs());

describe("source repository links", () => {
  it("default to the canonical public repository", () => {
    vi.stubEnv("VITE_OCP_REPO_URL", "");
    expect(getRepoLinks()).toEqual({
      sourceUrl: "https://github.com/crewcrew/open-conference-platform",
      downloadUrl: "https://github.com/crewcrew/open-conference-platform/archive/refs/heads/main.zip",
    });
  });
  it("a fork can override the repository", () => {
    vi.stubEnv("VITE_OCP_REPO_URL", "https://github.com/someone/ocp-fork");
    expect(getRepoLinks()?.downloadUrl).toBe("https://github.com/someone/ocp-fork/archive/refs/heads/main.zip");
  });
  it("an invalid override falls back to the canonical repository, never a dead link", () => {
    vi.stubEnv("VITE_OCP_REPO_URL", "#");
    expect(getRepoLinks()?.sourceUrl).toBe("https://github.com/crewcrew/open-conference-platform");
  });
  it("link View source to the repo root and Download to main.zip", () => {
    expect(repoLinksFrom(PROJECT.repoUrl)).toEqual({
      sourceUrl: "https://github.com/crewcrew/open-conference-platform",
      downloadUrl: "https://github.com/crewcrew/open-conference-platform/archive/refs/heads/main.zip",
    });
  });
  it("normalize trailing slashes and .git", () => {
    expect(repoLinksFrom("https://github.com/crewcrew/open-conference-platform.git/")?.sourceUrl).toBe(
      "https://github.com/crewcrew/open-conference-platform",
    );
  });
  it("reject placeholders and non-GitHub URLs", () => {
    for (const bad of ["#", "github.com/a/b", "http://github.com/a/b", "https://example.com/a/b", "https://github.com/a"]) {
      expect(repoLinksFrom(bad)).toBeNull();
    }
  });
  it("the project is MIT licensed", () => {
    expect(PROJECT.license).toBe("MIT");
  });
});

