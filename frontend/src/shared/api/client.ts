import { getBackendOrigin } from "../config";
import { getMode } from "../mode";
import { getCsrfToken } from "./csrf";

export type ApiErrorKind =
  | "unconfigured"
  | "network"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "server";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public kind: ApiErrorKind,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function kindFor(status: number): ApiErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  return "server";
}

function defaultMessage(status: number): string {
  switch (status) {
    case 401:
      return "Your session has ended. Please sign in again.";
    case 403:
      return "You don't have permission to view this.";
    case 404:
      return "We couldn't find what you were looking for.";
    default:
      return `The conference server returned an error (${status}).`;
  }
}

export function apiUrl(path: string): string {
  const origin = getBackendOrigin();
  if (!origin) throw new ApiError(0, "No backend is configured.", "unconfigured");
  if (!path.startsWith("/") || !(path.split("?")[0] ?? "").endsWith("/")) {
    throw new Error(`API paths need a leading and trailing slash: ${path}`);
  }
  return `${origin}/api/v1${path}`;
}

export async function apiRequest<T>(
  path: string,
  options: { method?: "GET" | "POST"; body?: unknown } = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const url = apiUrl(path);
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    const token = getCsrfToken();
    if (token) headers["X-CSRFToken"] = token;
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      credentials: "include",
      headers,
      ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
    });
  } catch {
    throw new ApiError(
      0,
      "We couldn't reach the conference server. Check your connection and try again.",
      "network",
    );
  }

  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    const serverMsg =
      data && typeof data === "object" && "error" in data && typeof data.error === "string"
        ? data.error
        : null;
    throw new ApiError(res.status, serverMsg ?? defaultMessage(res.status), kindFor(res.status));
  }
  return data as T;
}

/** Load live data from Django, or labeled sample data when in preview mode. */
export function load<T>(path: string, demo: () => T): Promise<T> {
  if (getMode() === "demo") return Promise.resolve(demo());
  return apiRequest<T>(path);
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  return new ApiError(0, error instanceof Error ? error.message : "Something went wrong.", "server");
}

export const enc = encodeURIComponent;

