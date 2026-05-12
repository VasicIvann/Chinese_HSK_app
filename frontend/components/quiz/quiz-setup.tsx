"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Play } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { getQuizzes, getStats } from "@/lib/api/endpoints";
import type { QuizMode } from "@/lib/hooks/use-quiz-session";
import { cn } from "@/lib/utils";

type Props = {
  onStart: (params: { quiz: string; count: number; mode: QuizMode }) => void;
  isLoading?: boolean;
};

const COUNT_OPTIONS = [5, 10, 15, 20];

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
  const [selectedQuiz, setSelectedQuiz] = useState<string | null>(null);
  const [count, setCount] = useState(10);
  const [mode, setMode] = useState<QuizMode>("auto-assess");

  const quizzesQuery = useQuery({ queryKey: ["quizzes"], queryFn: getQuizzes });
  const statsQuery = useQuery({
    queryKey: ["srs-stats", selectedQuiz ?? "all"],
    queryFn: () => getStats(selectedQuiz ?? undefined),
    enabled: !quizzesQuery.isLoading,
  });

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
        <CardHeader>
          <CardTitle>Choisis ton quiz</CardTitle>
          <CardDescription>Le niveau HSK que tu veux travailler.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {quizzesQuery.isLoading ? (
            <>
              <Skeleton className="h-11 w-24" />
              <Skeleton className="h-11 w-24" />
              <Skeleton className="h-11 w-24" />
            </>
          ) : (
            quizzesQuery.data?.map((quiz) => (
              <Button
                key={quiz.key}
                type="button"
                variant={selectedQuiz === quiz.key ? "default" : "outline"}
                size="lg"
                onClick={() => setSelectedQuiz(quiz.key)}
              >
                {quiz.title}
              </Button>
            ))
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
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Nombre de questions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {COUNT_OPTIONS.map((opt) => (
            <Button
              key={opt}
              type="button"
              variant={count === opt ? "default" : "outline"}
              onClick={() => setCount(opt)}
              size="lg"
            >
              {opt}
            </Button>
          ))}
        </CardContent>
      </Card>

      <div className="sticky bottom-4 mt-2 sm:static">
        <Button
          size="xl"
          className="w-full"
          disabled={!selectedQuiz || isLoading}
          onClick={() => selectedQuiz && onStart({ quiz: selectedQuiz, count, mode })}
        >
          <Play className="h-5 w-5" />
          {isLoading ? "Préparation…" : "Lancer la session"}
        </Button>
      </div>
    </motion.div>
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
