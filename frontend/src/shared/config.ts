/**
 * Backend configuration. VITE_OCP_API_URL is the Django origin WITHOUT /api/v1,
 * e.g. https://api.example.com. Read at call time so tests can stub env.
 */
export function normalizeOrigin(raw: string | undefined | null): string | null {
  if (!raw) return null;
  let value = raw.trim();
  if (!value) return null;
  value = value.replace(/\/+$/, "");
  // Tolerate a mistakenly included API prefix.
  value = value.replace(/\/api\/v1$/, "");
  if (!/^https?:\/\//.test(value)) return null;
  return value;
}

export function getBackendOrigin(): string | null {
  return normalizeOrigin(import.meta.env["VITE_OCP_API_URL"] as string | undefined);
}

/**
 * Source repository metadata. Defaults to the canonical public repository;
 * forks can override with VITE_OCP_REPO_URL (must be a valid GitHub repo URL).
 */
export const PROJECT = {
  name: "Open Conference Platform",
  license: "MIT",
  repoUrl: "https://github.com/crewcrew/open-conference-platform",
} as const;

export interface RepoLinks {
  sourceUrl: string;
  downloadUrl: string;
}

export function repoLinksFrom(raw: string | undefined | null): RepoLinks | null {
  if (!raw) return null;
  const v = raw.trim().replace(/\/+$/, "").replace(/\.git$/, "");
  if (!/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(v)) return null;
  return { sourceUrl: v, downloadUrl: `${v}/archive/refs/heads/main.zip` };
}

export function getRepoLinks(): RepoLinks | null {
  return repoLinksFrom(import.meta.env["VITE_OCP_REPO_URL"] as string | undefined) ?? repoLinksFrom(PROJECT.repoUrl);
}

