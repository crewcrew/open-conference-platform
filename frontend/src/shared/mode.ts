import { getBackendOrigin } from "./config";

/**
 * live: a self-hoster configured VITE_OCP_API_URL — only real backend data, never fixtures.
 * demo: default with no backend — the public interactive demo with labeled sample data.
 * Derived purely from build-time env, so SSR and hydration always agree.
 */
export type AppMode = "live" | "demo";

export function getMode(): AppMode {
  return getBackendOrigin() ? "live" : "demo";
}

export function useMode(): AppMode {
  return getMode();
}

