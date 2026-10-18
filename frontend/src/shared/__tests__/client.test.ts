import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest, ApiError } from "../api/client";
import { setCsrfToken } from "../api/csrf";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  setCsrfToken(null);
});

describe("API client", () => {
  it("refuses to call when no backend origin is configured", async () => {
    vi.stubEnv("VITE_OCP_API_URL", "");
    await expect(apiRequest("/session/")).rejects.toMatchObject({ kind: "unconfigured" });
  });

  it("prefixes /api/v1, sends credentials and the in-memory CSRF token on POST", async () => {
    vi.stubEnv("VITE_OCP_API_URL", "https://api.example.com/");
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    setCsrfToken("tok123");
    await apiRequest("/auth/logout/", { method: "POST" });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://api.example.com/api/v1/auth/logout/");
    expect(init.credentials).toBe("include");
    expect(init.headers["X-CSRFToken"]).toBe("tok123");
  });

  it("surfaces the backend {error} message and maps 403 to forbidden", async () => {
    vi.stubEnv("VITE_OCP_API_URL", "https://api.example.com");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "No access" }), { status: 403 })));
    const err = (await apiRequest("/events/").catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.kind).toBe("forbidden");
    expect(err.message).toBe("No access");
  });

  it("maps a failed network request to a network error", async () => {
    vi.stubEnv("VITE_OCP_API_URL", "https://api.example.com");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(apiRequest("/events/")).rejects.toMatchObject({ kind: "network", status: 0 });
  });

  it("rejects paths without a trailing slash", async () => {
    vi.stubEnv("VITE_OCP_API_URL", "https://api.example.com");
    await expect(apiRequest("/events")).rejects.toThrow(/trailing slash/);
  });
});

