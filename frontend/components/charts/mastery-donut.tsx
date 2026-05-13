"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { MasteryDistribution } from "@/lib/api/types";

type Props = {
  data: MasteryDistribution;
};

const COLORS = {
  mastered: "var(--color-primary)",
  learning: "oklch(0.65 0.15 60)", // amber
  new: "oklch(0.72 0.04 60)",       // muted
};

export function MasteryDonut({ data }: Props) {
  const chartData = [
    { name: "Maîtrisés", value: data.mastered, color: COLORS.mastered },
    { name: "En cours", value: data.learning, color: COLORS.learning },
    { name: "Nouveaux", value: data.new, color: COLORS.new },
  ].filter((d) => d.value > 0);

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Aucune donnée encore. Lance ta première session de quiz.
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-6">
      <div className="h-64 w-full sm:w-1/2">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={2}
              startAngle={90}
              endAngle={-270}
            >
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} stroke="none" />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "var(--color-popover)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
              }}
              labelStyle={{ color: "var(--color-popover-foreground)" }}
              itemStyle={{ color: "var(--color-popover-foreground)" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-1 flex-col gap-3">
        {chartData.map((d) => (
          <div key={d.name} className="flex items-center justify-between gap-3 text-sm">
            <div className="flex items-center gap-2">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: d.color }}
                aria-hidden
              />
              <span>{d.name}</span>
            </div>
            <strong>{d.value}</strong>
          </div>
        ))}
        <div className="mt-2 border-t border-border pt-2 text-xs text-muted-foreground">
          {data.total_entries} mots HSK au total
        </div>
      </div>
    </div>
  );
}
