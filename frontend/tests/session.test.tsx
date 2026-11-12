import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest, ApiError } from "@/lib/api/client";
import { AuthProvider, useAuth } from "@/lib/auth/auth-context";
import { onUnauthorized } from "@/lib/auth/session-events";

const toastInfo = vi.fn();
vi.mock("sonner", () => ({ toast: { info: (m: string) => toastInfo(m), error: vi.fn() } }));

function mockFetch(status: number, body: unknown = {}) {
  const fn = vi.fn(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("apiRequest", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it("sends the browser time zone and the stored token", async () => {
    localStorage.setItem("hsk.access_token", "tok");
    const fetchFn = mockFetch(200, { ok: true });
    await apiRequest("/v1/anything");
    const headers = (fetchFn.mock.calls[0] as unknown as [string, RequestInit])[1].headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer tok");
    expect(headers["X-Timezone"]).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone);
  });

  it("signals an expired session on 401 for an authenticated call", async () => {
    localStorage.setItem("hsk.access_token", "expired");
    mockFetch(401, { detail: "Token invalide ou expiré." });
    const handler = vi.fn();
    const off = onUnauthorized(handler);
    await expect(apiRequest("/v1/account/overview")).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledTimes(1);
    off();
  });

  it("does not signal on a failed login (no token sent)", async () => {
    mockFetch(401, { detail: "Identifiants invalides." });
    const handler = vi.fn();
    const off = onUnauthorized(handler);
    await expect(apiRequest("/v1/auth/login", { method: "POST", body: {}, withAuth: false })).rejects.toThrow();
    expect(handler).not.toHaveBeenCalled();
    off();
  });
});

function Status() {
  const { isAuthenticated } = useAuth();
  return <p>{isAuthenticated ? "connecté" : "déconnecté"}</p>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    toastInfo.mockReset();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("clears the session when an API call returns 401", async () => {
    localStorage.setItem("hsk.access_token", "expired");
    localStorage.setItem("hsk.user", JSON.stringify({ id: 1, email: "i@i.com", locale: "fr" }));
    render(
      <AuthProvider>
        <Status />
      </AuthProvider>
    );
    expect(await screen.findByText("connecté")).toBeInTheDocument();

    mockFetch(401, { detail: "Token invalide ou expiré." });
    // Two calls failing at once must only sign out / toast once.
    await act(async () => {
      await Promise.allSettled([apiRequest("/v1/quizzes"), apiRequest("/v1/srs/stats")]);
    });

    expect(screen.getByText("déconnecté")).toBeInTheDocument();
    expect(localStorage.getItem("hsk.access_token")).toBeNull();
    expect(toastInfo).toHaveBeenCalledTimes(1);
  });
});
