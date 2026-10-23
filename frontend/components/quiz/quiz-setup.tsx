"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Check, Lock, Play, Sparkles } from "lucide-react";
import { useState } from "react";

import { HskVersionToggle } from "@/components/hsk-version-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { getQuizzes, getStats, MAX_SESSION_SIZE } from "@/lib/api/endpoints";
import type { QuizMode } from "@/lib/hooks/use-quiz-session";
import { quizLabel, useHskVersion, usePinyinLock, VERSION_INFO } from "@/lib/hsk-version";
import { cn } from "@/lib/utils";

export type QuizStartParams = {
  quizzes: string[];
  count: number;
  mode: QuizMode;
  onlyNew: boolean;
};

type Props = {
  onStart: (params: QuizStartParams) => void;
  isLoading?: boolean;
};

const COUNT_OPTIONS = [10, 20, 50];

type CountChoice = number | "max" | "custom";

const MODES: { value: QuizMode; label: string; description: string }[] = [
  {
    value: "auto-assess",
    label: "Auto-évaluation",
    description: "Tu juges si tu connais ou pas. Le plus rapide, parfait sur mobile.",
  },
  {
    value: "pinyin-input",
    label: "Saisie pinyin",
    description: "Tu tapes le pinyin avant de juger. Force la production active.",
  },
];

export function QuizSetup({ onStart, isLoading }: Props) {
  const { version } = useHskVersion();
  // Selection kept per version: switching back restores it.
  const [selectionByVersion, setSelectionByVersion] = useState<Record<string, string[]>>({});
  const selectedQuizzes = selectionByVersion[version] ?? [];
  const setSelectedQuizzes = (update: (current: string[]) => string[]) =>
    setSelectionByVersion((all) => ({ ...all, [version]: update(all[version] ?? []) }));
  const [countChoice, setCountChoice] = useState<CountChoice>(10);
  const [customCount, setCustomCount] = useState("");
  const [onlyNew, setOnlyNew] = useState(false);
  const [mode, setMode] = useState<QuizMode>("auto-assess");
  const pinyinLock = usePinyinLock();
  // Showing the pinyin would give the answer away when it has to be typed.
  const lockApplies = mode === "auto-assess";

  const quizzesQuery = useQuery({ queryKey: ["quizzes", version], queryFn: () => getQuizzes(version) });
  const statsQuery = useQuery({
    queryKey: ["srs-stats", version, ...selectedQuizzes],
    queryFn: () => getStats(selectedQuizzes),
    enabled: !quizzesQuery.isLoading,
  });

  const toggleQuiz = (key: string) => {
    const order = quizzesQuery.data?.map((q) => q.key) ?? [];
    setSelectedQuizzes((current) =>
      current.includes(key)
        ? current.filter((k) => k !== key)
        : [...current, key].sort((a, b) => order.indexOf(a) - order.indexOf(b))
    );
  };

  const stats = statsQuery.data;
  const hasSelection = selectedQuizzes.length > 0;
  // Words the session can draw from with the current settings (null until stats load).
  const available =
    hasSelection && stats ? (onlyNew ? stats.new : stats.due + stats.new + stats.upcoming) : null;
  const maxCount = available === null ? null : Math.min(available, MAX_SESSION_SIZE);

  const parsedCustom = /^\d+$/.test(customCount.trim()) ? Number(customCount.trim()) : NaN;
  const requested =
    countChoice === "max"
      ? maxCount
      : countChoice === "custom"
        ? Number.isFinite(parsedCustom) && parsedCustom >= 1
          ? Math.min(parsedCustom, MAX_SESSION_SIZE)
          : null
        : countChoice;
  const finalCount = requested !== null && maxCount !== null ? Math.min(requested, maxCount) : requested;

  const customInvalid = countChoice === "custom" && customCount.trim() !== "" && requested === null;
  const nothingLeft = available === 0;
  const canStart =
    hasSelection && !isLoading && finalCount !== null && finalCount >= 1 && !nothingLeft;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="flex flex-col gap-6"
    >
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Compréhension écrite
        </h1>
        <p className="mt-1 text-muted-foreground">
          Configure ta session. L&apos;algorithme FSRS choisit les mots à voir en priorité.
        </p>
      </div>

      {statsQuery.data && (
        <div className="grid grid-cols-3 gap-3 sm:max-w-md">
          <StatTile label="À réviser" value={statsQuery.data.due} tone="text-primary" />
          <StatTile label="Nouveaux" value={statsQuery.data.new} tone="text-emerald-600 dark:text-emerald-400" />
          <StatTile label="À venir" value={statsQuery.data.upcoming} tone="text-muted-foreground" />
        </div>
      )}

      <Card>
        <CardHeader className="flex-row flex-wrap items-start justify-between gap-x-4 gap-y-3">
          <div className="flex min-w-0 flex-col gap-1.5">
            <CardTitle>Choisis tes niveaux</CardTitle>
            <CardDescription>
              Un ou plusieurs niveaux HSK : les mots sont mélangés dans la même session.
              <span className="block">{VERSION_INFO[version].hint}</span>
            </CardDescription>
          </div>
          <HskVersionToggle />
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {quizzesQuery.isLoading ? (
            <>
              <Skeleton className="h-11 w-24" />
              <Skeleton className="h-11 w-24" />
              <Skeleton className="h-11 w-24" />
            </>
          ) : (
            quizzesQuery.data?.map((quiz) => {
              const active = selectedQuizzes.includes(quiz.key);
              return (
                <Button
                  key={quiz.key}
                  type="button"
                  variant={active ? "default" : "outline"}
                  size="lg"
                  aria-pressed={active}
                  onClick={() => toggleQuiz(quiz.key)}
                >
                  {active && <Check className="h-4 w-4" />}
                  {quiz.title}
                </Button>
              );
            })
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <button
            type="button"
            role="switch"
            aria-checked={onlyNew}
            onClick={() => setOnlyNew((v) => !v)}
            className="flex w-full items-center justify-between gap-4 text-left"
          >
            <span>
              <span className="flex items-center gap-2 font-semibold">
                <Sparkles className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                Nouveaux mots uniquement
              </span>
              <span className="mt-1 block text-sm text-muted-foreground">
                Seulement des mots que tu n&apos;as jamais vus dans tes quiz précédents.
              </span>
            </span>
            <SwitchTrack on={onlyNew} />
          </button>
          {onlyNew && hasSelection && nothingLeft && (
            <p className="mt-3 text-sm text-destructive">
              Tu as déjà vu tous les mots de ces niveaux. Désactive ce mode ou ajoute un niveau.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Mode</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 sm:flex-row sm:gap-3">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              onClick={() => setMode(m.value)}
              className={cn(
                "flex-1 rounded-lg border-2 p-4 text-left transition-colors",
                mode === m.value
                  ? "border-primary bg-accent/50"
                  : "border-border hover:border-primary/50"
              )}
            >
              <p className="font-semibold">{m.label}</p>
              <p className="mt-1 text-sm text-muted-foreground">{m.description}</p>
            </button>
          ))}
        </CardContent>
        <CardContent className="border-t border-border pt-4">
          <button
            type="button"
            role="switch"
            aria-checked={lockApplies && pinyinLock.locked}
            disabled={!lockApplies}
            onClick={pinyinLock.toggle}
            className="flex w-full items-center justify-between gap-4 text-left disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span>
              <span className="flex items-center gap-2 font-semibold">
                <Lock className="h-4 w-4 text-primary" />
                Pinyin toujours affiché
              </span>
              <span className="mt-1 block text-sm text-muted-foreground">
                {lockApplies
                  ? "Le pinyin apparaît sous chaque mot dès le début de la carte. Réglage gardé sur ton compte."
                  : "Indisponible en saisie pinyin : le pinyin affiché donnerait la réponse."}
              </span>
            </span>
            <SwitchTrack on={lockApplies && pinyinLock.locked} />
          </button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Nombre de questions</CardTitle>
          {available !== null && (
            <CardDescription>
              {available} mot{available > 1 ? "s" : ""} disponible{available > 1 ? "s" : ""}
              {onlyNew ? " jamais vus" : ""} dans {selectedQuizzes.map(quizLabel).join(" + ")} ({VERSION_INFO[version].label}).
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            {COUNT_OPTIONS.map((opt) => (
              <Button
                key={opt}
                type="button"
                variant={countChoice === opt ? "default" : "outline"}
                onClick={() => setCountChoice(opt)}
                size="lg"
              >
                {opt}
              </Button>
            ))}
            <Button
              type="button"
              variant={countChoice === "max" ? "default" : "outline"}
              onClick={() => setCountChoice("max")}
              size="lg"
              disabled={!hasSelection}
            >
              MAX{maxCount !== null ? ` (${maxCount})` : ""}
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              placeholder="Autre nombre (ex. 27)"
              aria-label="Nombre de questions personnalisé"
              value={customCount}
              onFocus={() => setCountChoice("custom")}
              onChange={(e) => {
                setCustomCount(e.target.value.replace(/[^0-9]/g, ""));
                setCountChoice("custom");
              }}
              className={cn(
                "max-w-56",
                countChoice === "custom" && "border-primary",
                customInvalid && "border-destructive"
              )}
            />
          </div>
          {countChoice === "custom" &&
            requested !== null &&
            maxCount !== null &&
            requested > maxCount && (
              <p className="text-sm text-muted-foreground">
                Seulement {maxCount} mots disponibles : la session en aura {maxCount}.
              </p>
            )}
        </CardContent>
      </Card>

      <div className="sticky bottom-4 mt-2 sm:static">
        <Button
          size="xl"
          className="w-full"
          disabled={!canStart}
          onClick={() =>
            canStart &&
            finalCount !== null &&
            onStart({ quizzes: selectedQuizzes, count: finalCount, mode, onlyNew })
          }
        >
          <Play className="h-5 w-5" />
          {isLoading
            ? "Préparation…"
            : finalCount !== null && hasSelection
              ? `Lancer la session (${finalCount})`
              : "Lancer la session"}
        </Button>
      </div>
    </motion.div>
  );
}

function SwitchTrack({ on }: { on: boolean }) {
  return (
    <span
      aria-hidden
      className={cn("relative h-7 w-12 shrink-0 rounded-full transition-colors", on ? "bg-primary" : "bg-muted")}
    >
      <span
        className={cn(
          "absolute top-1 h-5 w-5 rounded-full bg-background shadow transition-transform",
          on ? "translate-x-6" : "translate-x-1"
        )}
      />
    </span>
  );
}

function StatTile({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3 text-center">
      <p className={cn("text-2xl font-semibold", tone)}>{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}
