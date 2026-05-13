"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type TrendPoint = {
  date: string;
  value: number;
};

type Props = {
  data: TrendPoint[];
  yDomain?: [number, number];
  unit?: string;
  emptyMessage?: string;
};

export function TrendChart({
  data,
  yDomain,
  unit = "",
  emptyMessage = "Pas encore de données.",
}: Props) {
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis
            dataKey="date"
            tickFormatter={(value: string) => value.slice(5)} // MM-DD
            stroke="var(--color-muted-foreground)"
            fontSize={11}
          />
          <YAxis
            domain={yDomain ?? ["auto", "auto"]}
            stroke="var(--color-muted-foreground)"
            fontSize={11}
            tickFormatter={(value: number) => `${value}${unit}`}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-popover)",
              border: "1px solid var(--color-border)",
              borderRadius: "8px",
              fontSize: 13,
            }}
            labelStyle={{ color: "var(--color-popover-foreground)" }}
            itemStyle={{ color: "var(--color-popover-foreground)" }}
            formatter={(value) => [`${value as number}${unit}`, "valeur"]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--color-primary)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--color-primary)" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
