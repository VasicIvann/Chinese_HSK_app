"use client";

import { CalendarClock, Flame, Target, Trophy } from "lucide-react";

import type { StreakSummary, SuccessRate, UpcomingReviews } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const NBSP = "\u00a0"; // keeps "62 %" or "7 jours : 66" from wrapping mid-value
const plural = (n: number, one: string, many: string) => `${n}${NBSP}${n > 1 ? many : one}`;
const pct = (rate: number | null) => (rate === null ? "—" : `${Math.round(rate * 100)}${NBSP}%`);

type Props = {
  streak: StreakSummary;
  successRate: SuccessRate;
  upcoming: UpcomingReviews;
};

/** The four headline numbers at the top of the dashboard. */
export function KpiTiles({ streak, successRate, upcoming }: Props) {
  const streakHint =
    streak.current === 0
      ? "Fais un quiz aujourd'hui pour la lancer."
      : streak.studied_today
        ? "Objectif du jour atteint."
        : "Révise aujourd'hui pour la garder.";

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Tile
        icon={<Flame className="h-4 w-4" />}
        label="Série actuelle"
        value={plural(streak.current, "jour", "jours")}
        hint={streakHint}
        highlight={streak.current > 0 && !streak.studied_today}
      />
      <Tile
        icon={<Trophy className="h-4 w-4" />}
        label="Meilleure série"
        value={plural(streak.best, "jour", "jours")}
        hint={successRate.tracking_since ? `Depuis le ${shortDate(successRate.tracking_since)}` : "Pas encore de révision enregistrée."}
      />
      <Tile
        icon={<Target className="h-4 w-4" />}
        label="Réussite (7 jours)"
        value={pct(successRate.last_7_days)}
        hint={
          successRate.reviews_7_days
            ? `${plural(successRate.reviews_7_days, "réponse", "réponses")} · 30${NBSP}j${NBSP}: ${pct(successRate.last_30_days)}`
            : "Aucune réponse cette semaine."
        }
      />
      <Tile
        icon={<CalendarClock className="h-4 w-4" />}
        label="À réviser maintenant"
        value={plural(upcoming.due_now, "mot", "mots")}
        hint={`Demain${NBSP}: ${upcoming.due_tomorrow} · 7${NBSP}jours${NBSP}: ${upcoming.due_next_7_days}`}
      />
    </div>
  );
}

function shortDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
}

function Tile({
  icon,
  label,
  value,
  hint,
  highlight = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4",
        highlight ? "border-primary/60" : "border-border"
      )}
    >
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}
