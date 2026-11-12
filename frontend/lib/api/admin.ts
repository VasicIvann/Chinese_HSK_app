/** Read-only Admin page (reserved to ADMIN_EMAILS on the server). */

import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/lib/api/client";
import { getMe } from "@/lib/api/endpoints";
import type { StatPeriod, StudyStats } from "@/lib/api/stats";
import type { HskVersion } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/auth-context";

export const ADMIN_SECTIONS = ["listening", "writing", "grammar", "classifiers", "tones"] as const;
export type AdminSection = (typeof ADMIN_SECTIONS)[number];

export type AdminUser = {
  id: number;
  email: string;
  created_at: string;
  hsk_version: HskVersion;
  last_active_at: string | null;
  active_days_30: number;
  active_today: boolean;
  words_seen: number;
  words_mastered: number;
  reviews: number;
  reviews_7d: number;
  questions: Record<AdminSection, number>;
  expressions: number;
  drawings: number;
  claude_calls: number;
  claude_tokens: number;
};

export type AdminOverview = {
  summary: {
    users: number;
    signups_7d: number;
    signups_30d: number;
    active_today: number;
    active_7d: number;
    active_30d: number;
    reviews_7d: number;
    claude_tokens: number;
  };
  signups_per_week: { week: string; count: number }[];
  users: AdminUser[];
};

export type AdminUserStats = {
  user: { id: number; email: string; created_at: string; hsk_version: HskVersion };
  stats: StudyStats;
};

export function getAdminUsers() {
  return apiRequest<AdminOverview>("/v1/admin/users");
}

export function getAdminUserStats(userId: number, days: StatPeriod) {
  return apiRequest<AdminUserStats>(`/v1/admin/users/${userId}/stats?days=${days}`);
}

/** Fresh from the server (the flag is not trusted from local storage); false while unknown. */
export function useIsAdmin(): boolean {
  const { isAuthenticated, user } = useAuth();
  const query = useQuery({ queryKey: ["me", user?.id], queryFn: () => getMe(), enabled: isAuthenticated, staleTime: 5 * 60_000 });
  return isAuthenticated && !!query.data?.is_admin;
}
