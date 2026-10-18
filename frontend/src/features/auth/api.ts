import { queryOptions, useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/shared/api/client";
import { setCsrfToken } from "@/shared/api/csrf";
import type { Session } from "@/shared/api/types";
import { demoSession, setDemoSignedIn } from "@/shared/demo/fixtures";
import { getMode, useMode, type AppMode } from "@/shared/mode";

export async function fetchSession(): Promise<Session> {
  if (getMode() === "demo") return demoSession();
  const session = await apiRequest<Session>("/session/");
  setCsrfToken(session.csrf_token);
  return session;
}

export function sessionQuery(mode: AppMode) {
  return queryOptions({
    queryKey: [mode, "session"],
    queryFn: fetchSession,
    enabled: mode !== "unconfigured",
    staleTime: 60_000,
  });
}

export function useSession() {
  const mode = useMode();
  return useQuery(sessionQuery(mode));
}

/** Fetch a fresh session (CSRF token) immediately before logging in. Password is never stored. */
export async function login(email: string, password: string): Promise<Session> {
  if (getMode() === "demo") {
    setDemoSignedIn(true);
    return demoSession();
  }
  await fetchSession();
  const session = await apiRequest<Session>("/auth/login/", { method: "POST", body: { email, password } });
  setCsrfToken(session.csrf_token);
  return session;
}

export async function logout(): Promise<void> {
  if (getMode() === "demo") {
    setDemoSignedIn(false);
    return;
  }
  try {
    await apiRequest("/auth/logout/", { method: "POST" });
  } finally {
    setCsrfToken(null);
  }
}

