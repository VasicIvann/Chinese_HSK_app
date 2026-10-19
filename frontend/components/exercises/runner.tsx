"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, RotateCcw, X } from "lucide-react";
import { useMemo, useState } from "react";

import { QuestionView, type QuestionResult } from "@/components/exercises/questions";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  postExerciseResult,
  type ExerciseItem,
  type ExerciseLevel,
  type ExerciseSet,
  type PartInfo,
} from "@/lib/api/exercises";
import { cn } from "@/lib/utils";

type Question = {
  key: string; // answer id sent to the API (group questions: "<group id>#<n>")
  partIndex: number;
  number: number; // question number on the paper
  item: ExerciseItem;
  sub?: number;
};

export function flattenSet(set: ExerciseSet): Question[] {
  const questions: Question[] = [];
  set.parts.forEach((part, partIndex) => {
    let number = Number(part.numbers.split("-")[0]) || 1;
    for (const item of part.items) {
      if (item.type === "pic_match" || item.type === "word_match") {
        item.items.forEach((_, sub) => questions.push({ key: `${item.id}#${sub}`, partIndex, number: number++, item, sub }));
      } else {
        questions.push({ key: item.id, partIndex, number: number++, item });
      }
    }
  });
  return questions;
}

/** Runs a practice set question by question, then shows and saves the score. */
export function ExerciseRunner({
  set,
  onExit,
  onRestart,
}: {
  set: ExerciseSet;
  onExit: () => void;
  onRestart?: () => void;
}) {
  const queryClient = useQueryClient();
  const questions = useMemo(() => flattenSet(set), [set]);
  const [index, setIndex] = useState(0);
  const [results, setResults] = useState<Record<string, QuestionResult>>({});
  const [pinyinOverride, setPinyinOverride] = useState<boolean | null>(null);
  const [finished, setFinished] = useState(false);

  const save = useMutation({
    mutationFn: async () => {
      // One result per part, so each part of the catalog shows its own score.
      await Promise.all(
        set.parts.map((part, partIndex) => {
          const answers = questions
            .filter((q) => q.partIndex === partIndex && results[q.key])
            .map((q) => ({ id: q.key, correct: results[q.key].correct }));
          return answers.length
            ? postExerciseResult({
                section: set.section,
                version: set.version,
                level: set.level as ExerciseLevel,
                part: part.part,
                answers,
              })
            : Promise.resolve(null);
        })
      );
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["exercise-catalog"] }),
  });

  if (questions.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
          <p className="text-muted-foreground">Pas encore de questions pour cette partie. Essaie « Nouvelle série ».</p>
          <Button variant="outline" onClick={onExit}>
            Retour
          </Button>
        </CardContent>
      </Card>
    );
  }

  const question = questions[index];
  const part: PartInfo = set.parts[question.partIndex];
  const showPinyin = pinyinOverride ?? part.pinyin;
  const result = results[question.key];
  const answeredCount = Object.keys(results).length;

  const finish = () => {
    setFinished(true);
    save.mutate();
  };

  if (finished) {
    return <Summary set={set} questions={questions} results={results} onExit={onExit} onRestart={onRestart} saving={save.isPending} />;
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">
            {part.part.startsWith("L") ? "Écoute" : "Écriture"} · partie {part.part.slice(1)} · question {question.number}
          </p>
          <p className="text-sm text-muted-foreground">{part.title}</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--primary)]"
              checked={showPinyin}
              onChange={(e) => setPinyinOverride(e.target.checked)}
            />
            Pinyin
          </label>
          <Button variant="ghost" size="sm" onClick={onExit}>
            Quitter
          </Button>
        </div>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
        <div className="h-full bg-primary transition-all" style={{ width: `${(answeredCount / questions.length) * 100}%` }} />
      </div>

      <QuestionView
        key={question.key}
        item={question.item}
        sub={question.sub}
        level={set.level as ExerciseLevel}
        showPinyin={showPinyin}
        result={result}
        onAnswer={(r) => setResults((all) => ({ ...all, [question.key]: r }))}
      />

      {result && (
        <Button size="lg" onClick={() => (index + 1 < questions.length ? setIndex(index + 1) : finish())} autoFocus>
          {index + 1 < questions.length ? "Question suivante" : "Voir mon score"}
          <ArrowRight className="h-4 w-4" />
        </Button>
      )}
      <p className="text-center text-xs text-muted-foreground">
        {index + 1} / {questions.length}
        {question.item.generated ? " · question générée par Claude" : ""}
      </p>
    </div>
  );
}

function Summary({
  set,
  questions,
  results,
  onExit,
  onRestart,
  saving,
}: {
  set: ExerciseSet;
  questions: Question[];
  results: Record<string, QuestionResult>;
  onExit: () => void;
  onRestart?: () => void;
  saving: boolean;
}) {
  const score = questions.filter((q) => results[q.key]?.correct).length;
  const pct = Math.round((score / questions.length) * 100);
  return (
    <div className="flex flex-col gap-5">
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
          <p className="text-sm text-muted-foreground">Ton score</p>
          <p className="text-5xl font-semibold">
            {score}
            <span className="text-2xl text-muted-foreground"> / {questions.length}</span>
          </p>
          <p className={cn("text-sm font-medium", pct >= 60 ? "text-emerald-600 dark:text-emerald-400" : "text-primary")}>
            {pct} % {pct >= 60 ? "· au-dessus des 60 % qu'il faut viser à l'examen" : "· vise au moins 60 %"}
          </p>
          <p className="text-xs text-muted-foreground">{saving ? "Enregistrement…" : "Score enregistré."}</p>
        </CardContent>
      </Card>

      {set.parts.length > 1 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {set.parts.map((part, partIndex) => {
            const qs = questions.filter((q) => q.partIndex === partIndex);
            const ok = qs.filter((q) => results[q.key]?.correct).length;
            return (
              <div key={part.part} className="flex items-center justify-between rounded-lg border border-border px-4 py-3 text-sm">
                <span>
                  Partie {part.part.slice(1)} · {part.title}
                </span>
                <span className="font-medium">
                  {ok} / {qs.length}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap gap-1.5" aria-label="Détail des réponses">
        {questions.map((q) => (
          <span
            key={q.key}
            title={`Question ${q.number}`}
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-md text-xs font-medium",
              results[q.key]?.correct ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" : "bg-destructive/15 text-destructive"
            )}
          >
            {results[q.key]?.correct ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
          </span>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {onRestart && (
          <Button onClick={onRestart}>
            <RotateCcw className="h-4 w-4" />
            Nouvelle série
          </Button>
        )}
        <Button variant="outline" onClick={onExit}>
          Retour aux parties
        </Button>
      </div>
    </div>
  );
}
