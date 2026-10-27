import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { averagePerDay, NewWordsChart } from "@/components/charts/new-words-chart";

const day = (d: number, n: number) => ({ date: `2026-10-${String(d).padStart(2, "0")}`, new: n });

describe("new words per day", () => {
  it("averages from the first day with new words, days off included", () => {
    // Started on the 25th: 20, then a day off, then 10 -> 30 / 3 days.
    const days = [day(23, 0), day(24, 0), day(25, 20), day(26, 0), day(27, 10)];
    expect(averagePerDay(days)).toEqual({ average: 10, days: 3 });
    expect(averagePerDay([day(1, 0)])).toEqual({ average: 0, days: 0 });
  });

  it("shows today's count, the average and the total", () => {
    render(<NewWordsChart days={[day(25, 20), day(26, 0), day(27, 10)]} />);
    expect(screen.getByText(/aujourd'hui · moyenne/).parentElement).toHaveTextContent("10 aujourd'hui · moyenne 10 par jour · 30 en 3 jours");
  });

  it("has an empty state", () => {
    render(<NewWordsChart days={[day(26, 0), day(27, 0)]} />);
    expect(screen.getByText("Pas encore de nouveau mot sur cette période.")).toBeInTheDocument();
  });
});
