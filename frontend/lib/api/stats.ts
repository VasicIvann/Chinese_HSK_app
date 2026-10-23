/** Study statistics shown on the Account page (GET /v1/account/stats). */

import { apiRequest } from "@/lib/api/client";
import type { HskVersion } from "@/lib/api/types";

export const STAT_PERIODS = [7, 30, 90] as const;
export type StatPeriod = (typeof STAT_PERIODS)[number];

export const TABS = ["vocab", "listening", "writing", "grammar", "classifiers", "expression", "drawings"] as const;
export type StatTab = (typeof TABS)[number];

export type TabCounts = Record<StatTab, number>;

export type StudyStats = {
  days: number;
  from_date: string;
  to_date: string;
  version: HskVersion;
  active_days: number;
  totals: TabCounts;
  activity: ({ date: string } & TabCounts)[];
  words: {
    per_day: { date: string; new: number; seen: number }[];
    seen_before: number;
    seen_total: number;
    new_in_period: number;
    reviewed_in_period: number;
    level_totals: { level: number; total: number }[];
  };
  time: {
    per_day: { date: string; minutes: number; cards: number }[];
    total_minutes: number;
    by_hour: { hour: number; count: number }[];
    by_weekday: { weekday: number; count: number }[];
  };
};

export function getStudyStats(days: StatPeriod, version: HskVersion) {
  return apiRequest<StudyStats>(`/v1/account/stats?days=${days}&version=${version}`);
}
