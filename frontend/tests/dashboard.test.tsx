import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { KpiTiles } from "@/components/dashboard/kpi-tiles";
import { LevelProgress } from "@/components/dashboard/level-progress";
import { ReviewForecast } from "@/components/dashboard/review-forecast";
import type { SuccessRate, UpcomingReviews } from "@/lib/api/types";

const success: SuccessRate = {
  last_7_days: 0.756,
  last_30_days: 0.7,
  reviews_7_days: 41,
  reviews_30_days: 120,
  daily: [],
  tracking_since: "2026-10-18",
};

const upcoming: UpcomingReviews = {
  due_now: 12,
  due_today: 15,
  due_tomorrow: 8,
  due_next_7_days: 40,
  forecast: [
    { date: "2026-10-18", count: 15 },
    { date: "2026-10-19", count: 8 },
    { date: "2026-10-20", count: 0 },
    { date: "2026-10-21", count: 5 },
    { date: "2026-10-22", count: 4 },
    { date: "2026-10-23", count: 6 },
    { date: "2026-10-24", count: 2 },
  ],
};

describe("KpiTiles", () => {
  it("shows streak, success rate and reviews due", () => {
    render(
      <KpiTiles streak={{ current: 5, best: 9, studied_today: false }} successRate={success} upcoming={upcoming} />
    );
    expect(screen.getByText(/^5\sjours$/)).toBeInTheDocument();
    expect(screen.getByText(/^9\sjours$/)).toBeInTheDocument();
    expect(screen.getByText("Révise aujourd'hui pour la garder.")).toBeInTheDocument();
    expect(screen.getByText(/^76\s%$/)).toBeInTheDocument();
    expect(screen.getByText(/41\sréponses · 30\sj\s: 70\s%/)).toBeInTheDocument();
    expect(screen.getByText(/^12\smots$/)).toBeInTheDocument();
    expect(screen.getByText(/^Demain\s: 8 · 7\sjours\s: 40$/)).toBeInTheDocument();
  });

  it("handles a brand-new account", () => {
    render(
      <KpiTiles
        streak={{ current: 0, best: 0, studied_today: false }}
        successRate={{ ...success, last_7_days: null, last_30_days: null, reviews_7_days: 0, tracking_since: null }}
        upcoming={{ ...upcoming, due_now: 1 }}
      />
    );
    expect(screen.getAllByText(/^0\sjour$/)).toHaveLength(2);
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText(/^1\smot$/)).toBeInTheDocument();
  });
});

describe("LevelProgress", () => {
  it("summarises each level and details a segment on hover", () => {
    render(
      <LevelProgress
        levels={[
          { quiz_key: "HSK1", title: "HSK 1", level: 1, total: 150, mastered: 60, learning: 30, new: 60 },
          { quiz_key: "HSK2", title: "HSK 2", level: 2, total: 150, mastered: 0, learning: 0, new: 150 },
        ]}
      />
    );
    expect(screen.getByText("60 / 150 maîtrisés · 40 %")).toBeInTheDocument();
    expect(screen.getByText("0 / 150 maîtrisés · 0 %")).toBeInTheDocument();
    const bar = screen.getByRole("img", { name: /HSK 1 : 60 maîtrisés, 30 en cours, 60 nouveaux sur 150/ });
    fireEvent.mouseEnter(bar.children[1]);
    expect(screen.getByText("En cours : 30 (20 %)")).toBeInTheDocument();
  });
});

describe("ReviewForecast", () => {
  it("labels days and shows a day's count on hover", () => {
    render(<ReviewForecast upcoming={upcoming} />);
    expect(screen.getByText("40 mots à revoir sur 7 jours")).toBeInTheDocument();
    expect(screen.getByText("Auj.")).toBeInTheDocument();
    expect(screen.getByText("Dem.")).toBeInTheDocument();
    fireEvent.mouseEnter(screen.getByRole("button", { name: /Demain : 8 mots/ }));
    expect(screen.getByText("Demain : 8 mots")).toBeInTheDocument();
  });
});
