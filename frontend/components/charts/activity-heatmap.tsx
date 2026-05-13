"use client";

import { useMemo } from "react";

import type { ActivityCell } from "@/lib/api/types";

type Props = {
  data: ActivityCell[];
};

/**
 * GitHub-style heatmap. Renders the last ~90 days as a 7×N grid (rows = day of
 * week, columns = weeks). Cell intensity scales with the count.
 */
export function ActivityHeatmap({ data }: Props) {
  const { weeks, maxCount } = useMemo(() => {
    if (data.length === 0) return { weeks: [], maxCount: 0 };

    const max = Math.max(...data.map((d) => d.count), 1);
    const padded: (ActivityCell | null)[] = [];

    // Align the first column to the first day of the week (Monday).
    const firstDate = new Date(data[0].date);
    const firstDow = (firstDate.getDay() + 6) % 7; // 0=Monday
    for (let i = 0; i < firstDow; i++) padded.push(null);
    padded.push(...data);

    // Group into weeks of 7 cells.
    const grouped: ((ActivityCell | null)[])[] = [];
    for (let i = 0; i < padded.length; i += 7) {
      grouped.push(padded.slice(i, i + 7));
    }
    return { weeks: grouped, maxCount: max };
  }, [data]);

  if (weeks.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
        Pas encore d&apos;activité.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto pb-2">
      <div className="inline-flex gap-1">
        {weeks.map((week, weekIdx) => (
          <div key={weekIdx} className="flex flex-col gap-1">
            {Array.from({ length: 7 }).map((_, dayIdx) => {
              const cell = week[dayIdx];
              if (!cell) {
                return <div key={dayIdx} className="h-3 w-3 rounded-sm bg-transparent" />;
              }
              const intensity = cell.count === 0 ? 0 : Math.min(cell.count / maxCount, 1);
              return (
                <div
                  key={dayIdx}
                  title={`${cell.date}: ${cell.count} mot${cell.count > 1 ? "s" : ""} revu${cell.count > 1 ? "s" : ""}`}
                  className="h-3 w-3 rounded-sm"
                  style={{
                    backgroundColor:
                      cell.count === 0
                        ? "var(--color-muted)"
                        : `color-mix(in oklch, var(--color-primary) ${Math.max(15, intensity * 100)}%, transparent)`,
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        {data.length} jours · max {maxCount} mots/jour
      </p>
    </div>
  );
}
