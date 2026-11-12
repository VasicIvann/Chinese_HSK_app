"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getAccountSettings, putAccountSettings } from "@/lib/api/endpoints";
import type { AccountSettings, HskVersion } from "@/lib/api/types";

export const HSK_VERSIONS: HskVersion[] = ["2.0", "3.0"];
export const DEFAULT_HSK_VERSION: HskVersion = "3.0";
export const accountSettingsKey = ["account-settings"] as const;

export const VERSION_INFO: Record<HskVersion, { label: string; hint: string }> = {
  "2.0": { label: "HSK 2.0", hint: "Ancien format : examens jusqu'au 7 novembre 2026." },
  "3.0": { label: "HSK 3.0", hint: "Nouveau format : examens à partir du 13 décembre 2026." },
};

/** "HSK3" → "HSK 3", "HSK3-2.0" → "HSK 3" (the version is shown once, by the toggle). */
export function quizLabel(key: string): string {
  const match = /^HSK(\d+)(?:-\d\.\d)?$/.exec(key);
  return match ? `HSK ${match[1]}` : key;
}

/** Everything whose content depends on the HSK version. */
const VERSION_SCOPED_KEYS = [
  ["quizzes"],
  ["srs-stats"],
  ["account-overview"],
  ["mastery"],
  ["drawings-gallery"],
  ["exercise-catalog"],
  ["grammar"],
  ["classifiers"],
  ["study-stats"],
  ["tone-words"],
];

/** The user's HSK version (saved on the account) and a setter that refreshes the app. */
export function useHskVersion() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: accountSettingsKey, queryFn: getAccountSettings, staleTime: 5 * 60_000 });

  const mutation = useMutation({
    mutationFn: (version: HskVersion) => putAccountSettings({ hsk_version: version }),
    onMutate: async (version) => {
      await queryClient.cancelQueries({ queryKey: accountSettingsKey });
      const previous = queryClient.getQueryData<AccountSettings>(accountSettingsKey);
      queryClient.setQueryData<AccountSettings>(accountSettingsKey, {
        pinyin_locked: false,
        ...previous,
        hsk_version: version,
      });
      return { previous };
    },
    onError: (_error, _version, context) => {
      if (context?.previous) queryClient.setQueryData(accountSettingsKey, context.previous);
      toast.error("Impossible de changer de version. Vérifie ta connexion.");
    },
    onSettled: () => {
      for (const queryKey of VERSION_SCOPED_KEYS) queryClient.invalidateQueries({ queryKey });
    },
  });

  return {
    version: query.data?.hsk_version ?? DEFAULT_HSK_VERSION,
    isLoading: query.isLoading,
    setVersion: (version: HskVersion) => {
      if (version !== (query.data?.hsk_version ?? DEFAULT_HSK_VERSION)) mutation.mutate(version);
    },
    isSaving: mutation.isPending,
  };
}

/** "Pinyin toujours affiché" in the vocabulary quiz, saved on the account. */
export function usePinyinLock() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: accountSettingsKey, queryFn: getAccountSettings, staleTime: 5 * 60_000 });

  const mutation = useMutation({
    mutationFn: (locked: boolean) => putAccountSettings({ pinyin_locked: locked }),
    onMutate: async (locked) => {
      await queryClient.cancelQueries({ queryKey: accountSettingsKey });
      const previous = queryClient.getQueryData<AccountSettings>(accountSettingsKey);
      queryClient.setQueryData<AccountSettings>(accountSettingsKey, {
        hsk_version: DEFAULT_HSK_VERSION,
        ...previous,
        pinyin_locked: locked,
      });
      return { previous };
    },
    onError: (_error, _locked, context) => {
      if (context?.previous) queryClient.setQueryData(accountSettingsKey, context.previous);
      toast.error("Impossible d'enregistrer le réglage du pinyin. Vérifie ta connexion.");
    },
    onSuccess: (settings) => queryClient.setQueryData(accountSettingsKey, settings),
  });

  const locked = query.data?.pinyin_locked ?? false;
  return {
    locked,
    setLocked: (next: boolean) => {
      if (next !== locked) mutation.mutate(next);
    },
    toggle: () => mutation.mutate(!locked),
  };
}
