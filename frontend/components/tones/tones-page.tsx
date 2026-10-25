"use client";

import { useQuery } from "@tanstack/react-query";
import { Eye, Headphones } from "lucide-react";
import { useState } from "react";

import { LevelPicker, useExerciseLevel } from "@/components/exercises/level-picker";
import { HskVersionToggle } from "@/components/hsk-version-toggle";
import { ToneSession, type ToneMode } from "@/components/tones/tone-session";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getQuizEntries, getQuizzes } from "@/lib/api/endpoints";
import { postExerciseResult, type ExerciseLevel } from "@/lib/api/exercises";
import type { HskVersion } from "@/lib/api/types";
import { useHskVersion, VERSION_INFO } from "@/lib/hsk-version";
import { toToneWord, type ToneWord } from "@/lib/tones";
import { cn } from "@/lib/utils";

const SIZES = [10, 20] as const;

/** Every word of levels 1..level of the version, split into syllables and tones. */
async function loadWords(level: ExerciseLevel, version: HskVersion): Promise<ToneWord[]> {
  const quizzes = (await getQuizzes(version)).filter((q) => (q.level ?? 99) <= level);
  const lists = await Promise.all(quizzes.map((q) => getQuizEntries(q.key)));
  const seen = new Set<number>();
  const words: ToneWord[] = [];
  for (const entry of lists.flat()) {
    if (seen.has(entry.id)) continue;
    seen.add(entry.id);
    const word = toToneWord(entry);
    if (word) words.push(word);
  }
  return words;
}

function sample<T>(items: T[], n: number): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy.slice(0, n);
}

const MODES: Record<ToneMode, { title: string; icon: typeof Eye; text: string; tip: string }> = {
  read: {
    title: "Trouve le ton",
    icon: Eye,
    text: "Le mot s'affiche en caractères : donne le ton de chaque syllabe avec les 5 boutons (1, 2, 3, 4 ou neutre).",
    tip: "Un bouton affiche le pinyin sans le ton si tu ne connais pas la prononciation.",
  },
  listen: {
    title: "Dictée",
    icon: Headphones,
    text: "Tu entends un mot sans le voir : écris le pinyin de chaque syllabe et choisis son ton.",
    tip: "Réécoute autant que tu veux, y compris au ralenti.",
  },
};

export function TonesPage() {
  const { version } = useHskVersion();
  const [level, setLevel] = useExerciseLevel();
  const [size, setSize] = useState<(typeof SIZES)[number]>(10);
  const [session, setSession] = useState<{ mode: ToneMode; words: ToneWord[]; n: number } | null>(null);

  const query = useQuery({ queryKey: ["tone-words", level, version], queryFn: () => loadWords(level, version), staleTime: 10 * 60_000 });
  const words = query.data ?? [];
  const pool = (mode: ToneMode) => (mode === "listen" ? words.filter((w) => w.audioSafe) : words);
  // `n` makes each new series a fresh session (new key).
  const start = (mode: ToneMode) => setSession((prev) => ({ mode, words: sample(pool(mode), size), n: (prev?.n ?? 0) + 1 }));

  if (session) {
    return (
      <ToneSession
        key={session.n}
        mode={session.mode}
        words={session.words}
        title={`${MODES[session.mode].title} · HSK ${level}`}
        onExit={() => setSession(null)}
        onRestart={() => start(session.mode)}
        onFinish={(answers) => {
          // Saved for the Account statistics; a failure only loses that data point.
          postExerciseResult({ section: "tones", version, level, part: session.mode, answers }).catch(() => undefined);
        }}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Tons</h1>
          <p className="mt-1 text-muted-foreground">
            Les quatre tons et le ton neutre, sur les mots du niveau choisi et des niveaux précédents ({VERSION_INFO[version].label}).
            La réponse attendue est le pinyin de la liste HSK.
          </p>
        </div>
        <HskVersionToggle />
      </div>
      <LevelPicker level={level} onChange={setLevel} />

      <Card>
        <CardContent className="grid grid-cols-5 gap-2 pt-6 text-center">
          {[
            ["1", "mā", "haut et plat", "ˉ"],
            ["2", "má", "montant", "ˊ"],
            ["3", "mǎ", "descend puis remonte", "ˇ"],
            ["4", "mà", "descendant", "ˋ"],
            ["∅", "ma", "neutre, court", "·"],
          ].map(([n, ex, how, sign]) => (
            <div key={n} className="flex flex-col items-center gap-0.5">
              <span className="text-lg font-semibold">
                {n} <span className="text-muted-foreground">{sign}</span>
              </span>
              <span className="text-base">{ex}</span>
              <span className="text-[11px] leading-tight text-muted-foreground">{how}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">Mots par série :</span>
        {SIZES.map((n) => (
          <Button key={n} size="sm" variant={size === n ? "default" : "outline"} onClick={() => setSize(n)}>
            {n}
          </Button>
        ))}
        <span className="text-xs text-muted-foreground">· un mot raté revient une fois dans la série</span>
      </div>

      {query.isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : query.isError ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">Impossible de charger les mots.</CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {(Object.keys(MODES) as ToneMode[]).map((mode) => {
            const m = MODES[mode];
            const Icon = m.icon;
            const available = pool(mode).length;
            return (
              <Card key={mode} className="flex flex-col">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Icon className="h-5 w-5 text-primary" />
                    {m.title}
                  </CardTitle>
                  <CardDescription>{m.text}</CardDescription>
                </CardHeader>
                <CardContent className="mt-auto flex flex-col gap-3">
                  <p className="text-sm text-muted-foreground">{m.tip}</p>
                  <p className={cn("text-xs text-muted-foreground")}>{available} mots disponibles</p>
                  <Button size="lg" onClick={() => start(mode)} disabled={available === 0}>
                    <Icon className="h-4 w-4" />
                    Commencer ({Math.min(size, available)} mots)
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
