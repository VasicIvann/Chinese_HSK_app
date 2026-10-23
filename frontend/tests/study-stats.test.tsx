import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StudyStatsSection } from "@/components/dashboard/study-stats";
import type { StudyStats } from "@/lib/api/stats";

const getStudyStats = vi.fn();
vi.mock("@/lib/api/stats", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/stats")>()),
  getStudyStats: (...args: unknown[]) => getStudyStats(...args),
}));
vi.mock("@/lib/api/endpoints", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/endpoints")>()),
  getAccountSettings: async () => ({ hsk_version: "3.0", pinyin_locked: false }),
}));

const zero = { vocab: 0, listening: 0, writing: 0, grammar: 0, classifiers: 0, expression: 0, drawings: 0 };

function stats(days: number): StudyStats {
  const dates = Array.from({ length: days }, (_, i) => `2026-10-${String(18 - days + 1 + i).padStart(2, "0")}`);
  return {
    days,
    from_date: dates[0],
    to_date: dates[dates.length - 1],
    version: "3.0",
    active_days: 2,
    totals: { ...zero, vocab: 120, listening: 30, classifiers: 10 },
    activity: dates.map((date, i) => ({
      date,
      ...zero,
      vocab: i === days - 1 ? 80 : i === days - 2 ? 40 : 0,
      listening: i === days - 1 ? 30 : 0,
      classifiers: i === days - 2 ? 10 : 0,
    })),
    words: {
      per_day: dates.map((date, i) => ({ date, new: i === days - 1 ? 25 : 0, seen: i === days - 1 ? 325 : 300 })),
      seen_before: 300,
      seen_total: 325,
      new_in_period: 25,
      reviewed_in_period: 90,
      level_totals: [
        { level: 1, total: 300 },
        { level: 2, total: 500 },
        { level: 3, total: 1000 },
      ],
    },
    time: {
      per_day: dates.map((date, i) => ({ date, minutes: i === days - 1 ? 42 : 0, cards: i === days - 1 ? 80 : 0 })),
      total_minutes: 42,
      by_hour: Array.from({ length: 24 }, (_, hour) => ({ hour, count: hour === 21 ? 100 : hour === 8 ? 30 : 0 })),
      by_weekday: Array.from({ length: 7 }, (_, weekday) => ({ weekday, count: weekday === 6 ? 130 : 0 })),
    },
  };
}

describe("StudyStatsSection", () => {
  beforeEach(() => {
    getStudyStats.mockReset().mockImplementation(async (days: number) => stats(days));
  });

  it("shows one chart per active tab, words and habits, and switches period", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <StudyStatsSection />
      </QueryClientProvider>
    );
    expect(await screen.findByText(/2 jours actifs sur 30/)).toBeInTheDocument();
    expect(getStudyStats).toHaveBeenCalledWith(30, "3.0");

    for (const label of ["Vocabulaire par jour", "Écoute par jour", "Classificateurs par jour"]) {
      expect(screen.getByRole("figure", { name: label })).toBeInTheDocument();
    }
    expect(screen.queryByRole("figure", { name: "Grammaire par jour" })).not.toBeInTheDocument();
    expect(screen.getByText(/Rien sur la période : Écriture HSK, Grammaire, Expression, Dessins/)).toBeInTheDocument();
    expect(screen.getByText("+25")).toBeInTheDocument();
    expect(screen.getByText("325")).toBeInTheDocument();
    expect(screen.getAllByText("42 min")).toHaveLength(2); // total and per quiz day
    expect(screen.getByText("21 h")).toBeInTheDocument();
    expect(screen.getByText(/heure la plus active, surtout le dimanche/)).toBeInTheDocument();

    fireEvent.click(screen.getByText("Voir les données en tableau"));
    expect(screen.getAllByRole("row")).toHaveLength(3); // header + 2 active days

    fireEvent.click(screen.getByRole("radio", { name: "7 jours" }));
    await waitFor(() => expect(getStudyStats).toHaveBeenCalledWith(7, "3.0"));
    expect(await screen.findByText(/sur 7/)).toBeInTheDocument();
  });
});
