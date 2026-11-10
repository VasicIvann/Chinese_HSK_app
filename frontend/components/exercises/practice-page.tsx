"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Ban, Clock, History, Loader2, Play, Sparkles, TriangleAlert, Trophy } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { LevelPicker, useExerciseLevel } from "@/components/exercises/level-picker";
import { ExerciseRunner } from "@/components/exercises/runner";
import { HskVersionToggle } from "@/components/hsk-version-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import {
  generateExerciseSet,
  getCatalog,
  getExerciseSet,
  type CatalogPart,
  type ExerciseSet,
  type Section,
  type SentenceWords,
} from "@/lib/api/exercises";
import { cn } from "@/lib/utils";

const WORDS_KEY = "hsk.sentence-words";

/** Source of the imposed words (remembered on this device). */
function useSentenceWords(): [SentenceWords, (w: SentenceWords) => void] {
  const [words, setWordsState] = useState<SentenceWords>(() => {
    try {
      return typeof window !== "undefined" && window.localStorage.getItem(WORDS_KEY) === "weak" ? "weak" : "seen";
    } catch {
      return "seen";
    }
  });
  const setWords = (next: SentenceWords) => {
    setWordsState(next);
    try {
      window.localStorage.setItem(WORDS_KEY, next);
    } catch {
      // private mode: the choice just isn't remembered
    }
  };
  return [words, setWords];
}

const WORD_SOURCES: { value: SentenceWords; label: string; description: string; icon: typeof History }[] = [
  { value: "seen", label: "Mots déjà vus", description: "Un mot au hasard parmi ceux que tu as déjà vus (HSK 1 à 3).", icon: History },
  {
    value: "weak",
    label: "Mots à revoir",
    description: "Un mot au hasard parmi tes 50 mots « À revoir » au score le plus bas.",
    icon: TriangleAlert,
  },
];
import { useHskVersion, VERSION_INFO } from "@/lib/hsk-version";

const COPY: Record<Section, { title: string; intro: string; noun: string }> = {
  listening: {
    title: "Écoute",
    intro: "Les parties de l'épreuve d'écoute du vrai HSK, dans le même ordre et le même format. Chaque enregistrement est lu deux fois, comme à l'examen.",
    noun: "l'épreuve d'écoute",
  },
  writing: {
    title: "Écriture HSK",
    intro: "Les parties de l'épreuve d'écriture (书写) du vrai HSK : caractère d'après le pinyin, phrase à remettre dans l'ordre ou à écrire avec un mot imposé.",
    noun: "l'épreuve d'écriture",
  },
};

export function PracticePage({ section }: { section: Section }) {
  const { version } = useHskVersion();
  const [level, setLevel] = useExerciseLevel();
  const [active, setActive] = useState<{ set: ExerciseSet; part: string } | null>(null);
  const [words, setWords] = useSentenceWords();
  const copy = COPY[section];

  const catalog = useQuery({
    queryKey: ["exercise-catalog", section, level, version],
    queryFn: () => getCatalog(section, level, version),
  });

  const start = useMutation({
    mutationFn: ({ part, fresh }: { part: string; fresh: boolean }) =>
      fresh ? generateExerciseSet(section, level, part, version) : getExerciseSet(section, level, part, version, words),
    retry: 0,
    onSuccess: (set, { part }) => {
      if (set.parts.length === 0) {
        toast.error("Aucune question disponible pour ce choix.");
        return;
      }
      setActive({ set, part });
      if (set.quota_remaining !== undefined) toast.success(`Nouvelle série prête (encore ${set.quota_remaining} aujourd'hui).`);
      const short = set.parts.find((p) => p.word_source && p.items.length < p.count);
      if (short) {
        toast.info(
          `Seulement ${short.items.length} mot${short.items.length > 1 ? "s" : ""} ${short.word_source === "weak" ? "à revoir" : "déjà vu" + (short.items.length > 1 ? "s" : "")} : la partie ${short.part.slice(1)} aura ${short.items.length} question${short.items.length > 1 ? "s" : ""}.`
        );
      }
    },
    onError: (error) =>
      toast.error(error instanceof ApiError && error.detail ? error.detail : "Impossible de charger la série."),
  });

  if (active) {
    return (
      <ExerciseRunner
        key={active.set.parts.map((p) => p.items.map((i) => i.id).join()).join("|")}
        set={active.set}
        onExit={() => setActive(null)}
        onRestart={() => start.mutate({ part: active.part, fresh: false })}
      />
    );
  }

  const parts = catalog.data?.parts ?? [];
  const playable = parts.filter(
    (p) => p.type !== "unavailable" && (p.word_counts ? p.word_counts[words] > 0 : p.available > 0)
  );
  const totalQuestions = playable.reduce((n, p) => n + p.count, 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{copy.title}</h1>
          <p className="mt-1 text-muted-foreground">{copy.intro}</p>
        </div>
        <HskVersionToggle />
      </div>

      <LevelPicker level={level} onChange={setLevel} />
      <p className="-mt-3 text-sm text-muted-foreground">
        Format {VERSION_INFO[version].label} — {VERSION_INFO[version].hint}
      </p>

      {catalog.isLoading ? (
        <div className="grid gap-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      ) : catalog.isError ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">Impossible de charger les exercices.</CardContent>
        </Card>
      ) : parts.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            Le HSK {level} ({VERSION_INFO[version].label}) n&apos;a pas d&apos;épreuve d&apos;écriture : elle commence au HSK 2 dans
            le nouveau format et au HSK 3 dans l&apos;ancien.
          </CardContent>
        </Card>
      ) : (
        <>
          {playable.length > 1 && (
            <Card className="border-primary/40">
              <CardHeader className="flex-row flex-wrap items-center justify-between gap-4">
                <div className="flex flex-col gap-1.5">
                  <CardTitle>Faire toute {copy.noun}</CardTitle>
                  <CardDescription>
                    {`${totalQuestions} questions, toutes les parties à la suite, comme le jour de l'examen.`}
                    {parts.some((p) => p.word_counts) &&
                      ` Phrases avec le mot donné : ${words === "weak" ? "mots à revoir" : "mots déjà vus"}.`}
                  </CardDescription>
                </div>
                <Button onClick={() => start.mutate({ part: "all", fresh: false })} disabled={start.isPending}>
                  {start.isPending && start.variables?.part === "all" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  Commencer
                </Button>
              </CardHeader>
            </Card>
          )}
          <div className="grid gap-4">
            {parts.map((part) => (
              <PartCard
                key={part.part}
                part={part}
                busy={start.isPending ? start.variables : undefined}
                onStart={(fresh) => start.mutate({ part: part.part, fresh })}
                words={words}
                onWords={setWords}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function PartCard({
  part,
  busy,
  onStart,
  words,
  onWords,
}: {
  part: CatalogPart;
  busy?: { part: string; fresh: boolean };
  onStart: (fresh: boolean) => void;
  words: SentenceWords;
  onWords: (w: SentenceWords) => void;
}) {
  const unavailable = part.type === "unavailable";
  const counts = part.word_counts;
  const loading = (fresh: boolean) => busy?.part === part.part && busy.fresh === fresh;
  return (
    <Card>
      <CardHeader className="gap-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Partie {part.part.slice(1)}</span>
          <span>Questions {part.numbers.replace("-", "–")}</span>
          <span>{part.count} questions</span>
          {part.best && (
            <span className="inline-flex items-center gap-1">
              <Trophy className="h-3.5 w-3.5" />
              Meilleur : {part.best.score}/{part.best.total}
            </span>
          )}
          {part.last && (
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              Dernier : {part.last.score}/{part.last.total}
            </span>
          )}
        </div>
        <CardTitle className="text-lg">{part.title}</CardTitle>
        <CardDescription>{part.how}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-2">
        {unavailable ? (
          <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <Ban className="h-4 w-4" /> Non reproduite
          </p>
        ) : counts ? (
          <div className="flex w-full flex-col gap-3">
            <div role="radiogroup" aria-label="Mots imposés" className="grid gap-2 sm:grid-cols-2">
              {WORD_SOURCES.map((s) => {
                const Icon = s.icon;
                const n = counts[s.value];
                return (
                  <button
                    key={s.value}
                    type="button"
                    role="radio"
                    aria-checked={words === s.value}
                    onClick={() => onWords(s.value)}
                    className={cn(
                      "rounded-lg border-2 p-3 text-left transition-colors",
                      words === s.value ? "border-primary bg-accent/50" : "border-border hover:border-primary/50"
                    )}
                  >
                    <span className="flex items-center gap-2 font-semibold">
                      <Icon className="h-4 w-4 text-primary" />
                      {s.label}
                    </span>
                    <span className="mt-1 block text-sm text-muted-foreground">{s.description}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {n} mot{n > 1 ? "s" : ""}
                      {s.value === "weak" && n > 0 && n < part.count ? ` · série de ${n}` : ""}
                    </span>
                  </button>
                );
              })}
            </div>
            {counts[words] === 0 && (
              <p className="text-sm text-destructive">
                {words === "weak"
                  ? "Aucun mot « À revoir » (score sous 0,5) dans tes mots des HSK 1 à 3. Choisis « Mots déjà vus »."
                  : "Tu n'as encore vu aucun mot des HSK 1 à 3 : fais d'abord quelques quiz dans Compréhension."}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={() => onStart(false)} disabled={!!busy || counts[words] === 0}>
                {loading(false) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                S&apos;entraîner
              </Button>
              <span className="text-xs text-muted-foreground">Claude corrige chaque phrase.</span>
            </div>
          </div>
        ) : (
          <>
            <Button onClick={() => onStart(false)} disabled={!!busy || part.available === 0}>
              {loading(false) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              S&apos;entraîner
            </Button>
            <Button variant="outline" onClick={() => onStart(true)} disabled={!!busy}>
              {loading(true) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {loading(true) ? "Claude écrit la série…" : "Nouvelle série (Claude)"}
            </Button>
            <span className="text-xs text-muted-foreground">{part.available} questions dans la banque</span>
          </>
        )}
      </CardContent>
    </Card>
  );
}
