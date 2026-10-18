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

export function isDemoEnvEnabled(): boolean {
  return import.meta.env["VITE_OCP_DEMO_MODE"] === "true";
}

