import { useSyncExternalStore } from "react";

import { getBackendOrigin, isDemoEnvEnabled } from "./config";

/**
 * live: a Django backend origin is configured — only real data is shown.
 * demo: no backend, visitor explicitly opted into the labeled sample preview.
 * unconfigured: no backend — show the setup screen.
 */
export type AppMode = "live" | "demo" | "unconfigured";

let demoOptIn = false;
const listeners = new Set<() => void>();

export function getMode(): AppMode {
  if (getBackendOrigin()) return "live";
  if (demoOptIn || isDemoEnvEnabled()) return "demo";
  return "unconfigured";
}

export function enableDemoMode() {
  demoOptIn = true;
  listeners.forEach((l) => l());
}

export function disableDemoMode() {
  demoOptIn = false;
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useMode(): AppMode {
  return useSyncExternalStore(subscribe, getMode, getMode);
}

