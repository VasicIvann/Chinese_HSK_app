"use client";

import { useState } from "react";

import type { UpcomingReviews } from "@/lib/api/types";

function dayLabel(iso: string, index: number) {
  if (index === 0) return "Auj.";
  if (index === 1) return "Dem.";
  return new Date(`${iso}T00:00:00`)
    .toLocaleDateString("fr-FR", { weekday: "short" })
    .replace(".", "");
}

function fullDay(iso: string, index: number) {
  if (index === 0) return "Aujourd'hui (retards compris)";
  if (index === 1) return "Demain";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

/** Words that FSRS will ask to review each of the next 7 days. */
export function ReviewForecast({ upcoming }: { upcoming: UpcomingReviews }) {
  const [active, setActive] = useState<number | null>(null);
  const max = Math.max(1, ...upcoming.forecast.map((d) => d.count));
  const activeDay = active !== null ? upcoming.forecast[active] : null;

  return (
    <div className="flex flex-col gap-3">
      <p className="h-5 text-sm text-muted-foreground" aria-live="polite">
        {activeDay
          ? `${fullDay(activeDay.date, active!)} : ${activeDay.count} mot${activeDay.count > 1 ? "s" : ""}`
          : `${upcoming.due_next_7_days} mot${upcoming.due_next_7_days > 1 ? "s" : ""} à revoir sur 7 jours`}
      </p>
      <div className="flex h-36 items-end gap-2" onMouseLeave={() => setActive(null)}>
        {upcoming.forecast.map((day, i) => (
          <button
            key={day.date}
            type="button"
            className="group flex h-full flex-1 flex-col items-center justify-end gap-1 focus-visible:outline-none"
            onMouseEnter={() => setActive(i)}
            onFocus={() => setActive(i)}
            onClick={() => setActive((a) => (a === i ? null : i))}
            aria-label={`${fullDay(day.date, i)} : ${day.count} mots`}
          >
            <span className="text-xs tabular-nums text-muted-foreground">{day.count > 0 ? day.count : ""}</span>
            <span
              className="w-full max-w-10 rounded-t bg-primary transition-opacity group-focus-visible:ring-2 group-focus-visible:ring-ring"
              style={{
                height: day.count > 0 ? `${Math.max(4, (day.count / max) * 100)}%` : 2,
                opacity: day.count === 0 ? 0.25 : active !== null && active !== i ? 0.45 : 1,
              }}
            />
          </button>
        ))}
      </div>
      <div className="flex gap-2 border-t border-border pt-1.5">
        {upcoming.forecast.map((day, i) => (
          <span key={day.date} className="flex-1 text-center text-xs capitalize text-muted-foreground">
            {dayLabel(day.date, i)}
          </span>
        ))}
      </div>
    </div>
  );
}
