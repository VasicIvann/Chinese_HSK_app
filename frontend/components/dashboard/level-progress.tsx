"use client";

import { useState } from "react";

import { MASTERY_COLORS } from "@/components/charts/mastery-donut";
import type { LevelProgress as LevelProgressItem } from "@/lib/api/types";

const SEGMENTS = [
  { key: "mastered", label: "Maîtrisés", color: MASTERY_COLORS.mastered },
  { key: "learning", label: "En cours", color: MASTERY_COLORS.learning },
  { key: "new", label: "Nouveaux", color: MASTERY_COLORS.new },
] as const;

type SegmentKey = (typeof SEGMENTS)[number]["key"];

const pct = (part: number, total: number) => (total ? Math.round((part / total) * 100) : 0);

/** One stacked bar per HSK level: mastered / learning / new, as a share of the level. */
export function LevelProgress({ levels }: { levels: LevelProgressItem[] }) {
  const [hover, setHover] = useState<{ level: string; key: SegmentKey } | null>(null);

  if (levels.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">Aucun niveau disponible.</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-label="Légende">
        {SEGMENTS.map((s) => (
          <li key={s.key} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: s.color }} aria-hidden />
            {s.label}
          </li>
        ))}
      </ul>

      {levels.map((level) => {
        const active = hover?.level === level.quiz_key ? hover.key : null;
        const activeSeg = SEGMENTS.find((s) => s.key === active);
        return (
          <div key={level.quiz_key}>
            <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
              <span className="font-medium">{level.title}</span>
              <span className="tabular-nums text-muted-foreground">
                {activeSeg
                  ? `${activeSeg.label} : ${level[activeSeg.key]} (${pct(level[activeSeg.key], level.total)} %)`
                  : `${level.mastered} / ${level.total} maîtrisés · ${pct(level.mastered, level.total)} %`}
              </span>
            </div>
            <div
              className="flex h-3 w-full gap-0.5"
              role="img"
              aria-label={`${level.title} : ${SEGMENTS.map((s) => `${level[s.key]} ${s.label.toLowerCase()}`).join(", ")} sur ${level.total}`}
              onMouseLeave={() => setHover(null)}
            >
              {SEGMENTS.map((s) => {
                const value = level[s.key];
                if (value === 0) return null;
                const visible = SEGMENTS.filter((x) => level[x.key] > 0);
                const first = visible[0]?.key === s.key;
                const last = visible[visible.length - 1]?.key === s.key;
                return (
                  <div
                    key={s.key}
                    className="h-full transition-opacity"
                    style={{
                      width: `${(value / level.total) * 100}%`,
                      minWidth: 4,
                      backgroundColor: s.color,
                      borderTopLeftRadius: first ? 4 : 0,
                      borderBottomLeftRadius: first ? 4 : 0,
                      borderTopRightRadius: last ? 4 : 0,
                      borderBottomRightRadius: last ? 4 : 0,
                      opacity: active && active !== s.key ? 0.45 : 1,
                    }}
                    onMouseEnter={() => setHover({ level: level.quiz_key, key: s.key })}
                    onClick={() =>
                      setHover((h) => (h?.level === level.quiz_key && h.key === s.key ? null : { level: level.quiz_key, key: s.key }))
                    }
                  />
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
