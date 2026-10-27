"use client";

import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Day = { date: string; new: number };

const longDate = (iso: unknown) =>
  typeof iso === "string"
    ? new Date(`${iso}T12:00:00`).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" })
    : "";

/**
 * Average of new words per calendar day, from the first day with new words in the period:
 * days off after that count as 0, days before the learner started do not count.
 */
export function averagePerDay(days: Day[]): { average: number; days: number } {
  const start = days.findIndex((d) => d.new > 0);
  if (start < 0) return { average: 0, days: 0 };
  const span = days.slice(start);
  return { average: span.reduce((n, d) => n + d.new, 0) / span.length, days: span.length };
}

/** Words seen for the first time each day, with the period's average as a dashed line. */
export function NewWordsChart({ days }: { days: Day[] }) {
  const total = days.reduce((n, d) => n + d.new, 0);
  if (total === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        Pas encore de nouveau mot sur cette période.
      </div>
    );
  }
  const { average: avg, days: counted } = averagePerDay(days);
  const today = days[days.length - 1];
  const rounded = Math.round(avg * 10) / 10;
  const peak = Math.max(...days.map((d) => d.new));
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm">
        <span className="font-semibold tabular-nums">{today?.new ?? 0}</span>{" "}
        <span className="text-muted-foreground">aujourd&apos;hui · moyenne</span>{" "}
        <span className="font-semibold tabular-nums">{rounded.toLocaleString("fr-FR")}</span>{" "}
        <span className="text-muted-foreground">
          par jour{counted < days.length ? ` (sur ${counted} jour${counted > 1 ? "s" : ""}, depuis ton premier nouveau mot)` : ""} ·{" "}
          {total.toLocaleString("fr-FR")} en {days.length} jours
        </span>
      </p>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={days} margin={{ top: 12, right: 8, left: -16, bottom: 0 }} barCategoryGap="15%">
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="date"
              tickFormatter={(value: string) => value.slice(5)} // MM-DD, like the charts next to it
              stroke="var(--color-muted-foreground)"
              fontSize={11}
              interval="preserveStartEnd"
              minTickGap={24}
            />
            <YAxis stroke="var(--color-muted-foreground)" fontSize={11} allowDecimals={false} />
            <Tooltip
              contentStyle={{
                background: "var(--color-popover)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                fontSize: 13,
              }}
              labelStyle={{ color: "var(--color-popover-foreground)", fontWeight: 600 }}
              itemStyle={{ color: "var(--color-popover-foreground)" }}
              cursor={{ fill: "var(--color-muted)", opacity: 0.6 }}
              labelFormatter={longDate}
              formatter={(value) => [`${value} nouveau${Number(value) > 1 ? "x" : ""} mot${Number(value) > 1 ? "s" : ""}`, "Ce jour-là"]}
            />
            <ReferenceLine
              y={avg}
              stroke="var(--color-foreground)"
              strokeDasharray="5 4"
              strokeOpacity={0.55}
              // Label on the line, unless the line sits too low (it would run into the axis).
              label={
                avg >= peak * 0.12
                  ? {
                      value: `moyenne ${rounded.toLocaleString("fr-FR")}`,
                      position: "insideTopRight",
                      fontSize: 11,
                      fill: "var(--color-muted-foreground)",
                    }
                  : undefined
              }
            />
            <Bar dataKey="new" fill="var(--viz-vocab)" radius={[3, 3, 0, 0]} maxBarSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
