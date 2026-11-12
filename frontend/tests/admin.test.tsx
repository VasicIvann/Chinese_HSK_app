import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminPage, ago } from "@/components/admin/admin-page";
import { ApiError } from "@/lib/api/client";

const getAdminUsers = vi.fn();
const getAdminUserStats = vi.fn();
vi.mock("@/lib/api/admin", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/admin")>()),
  getAdminUsers: () => getAdminUsers(),
  getAdminUserStats: (...args: unknown[]) => getAdminUserStats(...args),
}));
vi.mock("@/lib/api/endpoints", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/endpoints")>()),
  getAccountSettings: async () => ({ hsk_version: "3.0", pinyin_locked: false }),
}));

const q = { listening: 10, writing: 0, grammar: 3, classifiers: 0, tones: 20 };
const user = (id: number, email: string, extra = {}) => ({
  id,
  email,
  created_at: "2026-10-01T10:00:00",
  hsk_version: "3.0",
  last_active_at: null,
  active_days_30: 0,
  active_today: false,
  words_seen: 0,
  words_mastered: 0,
  reviews: 0,
  reviews_7d: 0,
  questions: { ...q },
  expressions: 0,
  drawings: 0,
  claude_calls: 0,
  claude_tokens: 0,
  ...extra,
});

function wrap() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AdminPage />
    </QueryClientProvider>
  );
}

describe("ago", () => {
  it("says how long ago, in French", () => {
    const now = Date.parse("2026-10-26T12:00:00Z");
    expect(ago(null, now)).toBe("jamais");
    expect(ago("2026-10-26T11:40:00", now)).toBe("il y a 20 min");
    expect(ago("2026-10-26T09:00:00", now)).toBe("il y a 3 h");
    expect(ago("2026-10-25T10:00:00", now)).toBe("hier");
    expect(ago("2026-10-14T12:00:00", now)).toBe("il y a 12 j");
  });
});

describe("AdminPage", () => {
  beforeEach(() => {
    getAdminUsers.mockReset().mockResolvedValue({
      summary: { users: 2, signups_7d: 1, signups_30d: 2, active_today: 1, active_7d: 1, active_30d: 2, reviews_7d: 120, claude_tokens: 4500 },
      signups_per_week: [{ week: "2026-10-19", count: 2 }],
      users: [
        user(1, "old@example.com", { words_seen: 900, last_active_at: "2026-09-01T10:00:00" }),
        user(2, "fresh@example.com", { words_seen: 40, reviews: 300, reviews_7d: 120, last_active_at: new Date().toISOString(), active_today: true }),
      ],
    });
    getAdminUserStats.mockReset().mockRejectedValue(new Error("not needed"));
  });

  it("lists the accounts, sorts, searches and opens one account", async () => {
    wrap();
    expect(await screen.findByText("comptes inscrits")).toBeInTheDocument();
    expect(screen.getByText("+1 en 7 j · +2 en 30 j")).toBeInTheDocument();
    const rows = () => screen.getAllByRole("row").slice(1).map((r) => r.textContent ?? "");
    expect(rows()[0]).toContain("fresh@example.com"); // most recent activity first
    expect(rows()[0]).toContain("33"); // questions: 10 + 3 + 20

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "words_seen" } });
    expect(rows()[0]).toContain("old@example.com");

    fireEvent.change(screen.getByPlaceholderText("Chercher un e-mail"), { target: { value: "fresh" } });
    expect(rows()).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "fresh@example.com" }));
    expect(await screen.findByRole("heading", { name: "fresh@example.com" })).toBeInTheDocument();
    await waitFor(() => expect(getAdminUserStats).toHaveBeenCalledWith(2, 30));
    fireEvent.click(screen.getByRole("button", { name: /Tous les comptes/ }));
    expect(await screen.findByText("comptes inscrits")).toBeInTheDocument();
  });

  it("explains a refused access", async () => {
    getAdminUsers.mockReset().mockRejectedValue(new ApiError(403, "Accès réservé à l'administrateur."));
    wrap();
    expect(await screen.findByText("Cette page est réservée à l'administrateur.")).toBeInTheDocument();
  });
});
