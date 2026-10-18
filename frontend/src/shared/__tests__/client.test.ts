import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest, ApiError, load } from "../api/client";
import { getMode } from "../mode";
import { setCsrfToken } from "../api/csrf";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  setCsrfToken(null);
});

describe("API client", () => {
  it("refuses to call the network when no backend origin is configured", async () => {
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

  it("live mode surfaces errors and never falls back to sample data", async () => {
    vi.stubEnv("VITE_OCP_API_URL", "https://api.example.com");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const demo = vi.fn(() => ({ results: [] }));
    await expect(load("/events/", demo)).rejects.toMatchObject({ kind: "network" });
    expect(demo).not.toHaveBeenCalled();
  });
});

describe("mode selection", () => {
  it("defaults to the demo when no backend is configured (first load, direct link or reload)", () => {
    vi.stubEnv("VITE_OCP_API_URL", "");
    expect(getMode()).toBe("demo");
    expect(getMode()).toBe("demo");
  });
  it("a configured backend takes precedence over the demo", () => {
    vi.stubEnv("VITE_OCP_API_URL", "https://api.example.com");
    expect(getMode()).toBe("live");
  });
  it("demo mode serves fixtures without calling the network", async () => {
    vi.stubEnv("VITE_OCP_API_URL", "");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(load("/events/", () => ({ results: [1] }))).resolves.toEqual({ results: [1] });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

