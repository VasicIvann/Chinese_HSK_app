/**
 * Tiny typed fetch wrapper for the HSK API.
 *
 * Types are auto-generated from /openapi.json into ./types.ts via the
 * `npm run gen:api` script. The runtime here is intentionally minimal:
 * - Adds the JSON content-type
 * - Attaches the Bearer token from localStorage when available
 * - Throws an `ApiError` with the parsed detail on non-2xx responses
 */

import { getStoredToken } from "@/lib/auth/storage";

const DEFAULT_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  /** Bearer token to use. Falls back to the one in localStorage. */
  token?: string | null;
  /** Pass `false` to call an unauthenticated endpoint (e.g. /healthz). */
  withAuth?: boolean;
  /** Forwarded to fetch(). */
  signal?: AbortSignal;
};

export async function apiRequest<TResponse>(
  path: string,
  options: RequestOptions = {}
): Promise<TResponse> {
  const { method = "GET", body, token, withAuth = true, signal } = options;
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (withAuth) {
    const bearer = token ?? (typeof window !== "undefined" ? getStoredToken() : null);
    if (bearer) {
      headers["Authorization"] = `Bearer ${bearer}`;
    }
  }

  const res = await fetch(`${DEFAULT_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!res.ok) {
    let detail = "";
    try {
      const payload = await res.json();
      detail =
        typeof payload?.detail === "string"
          ? payload.detail
          : JSON.stringify(payload);
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) {
    return undefined as TResponse;
  }
  return (await res.json()) as TResponse;
}

export function apiUrl(path: string): string {
  return `${DEFAULT_BASE_URL}${path}`;
}
