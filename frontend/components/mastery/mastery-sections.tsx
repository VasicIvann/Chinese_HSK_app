"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpenCheck, GraduationCap, RotateCw } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getMastery, getQuizzes } from "@/lib/api/endpoints";
import type { MasteryItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type Bucket = "mastered" | "known" | "review";

const MASTERED_THRESHOLD = 0.9;
const KNOWN_THRESHOLD = 0.5;

const BUCKETS: { id: Bucket; label: string; icon: typeof BookOpenCheck; tone: string }[] = [
  {
    id: "mastered",
    label: "Maîtrisés",
    icon: BookOpenCheck,
    tone: "text-emerald-600 dark:text-emerald-400",
  },
  {
    id: "known",
    label: "Connus",
    icon: GraduationCap,
    tone: "text-sky-600 dark:text-sky-400",
  },
  {
    id: "review",
    label: "À revoir",
    icon: RotateCw,
    tone: "text-destructive",
  },
];

function bucketOf(score: number): Bucket {
  if (score > MASTERED_THRESHOLD) return "mastered";
  if (score >= KNOWN_THRESHOLD) return "known";
  return "review";
}

function formatNextReview(iso: string | null): string {
  if (!iso) return "—";
  const due = new Date(iso);
  const now = new Date();
  const ms = due.getTime() - now.getTime();
  if (ms <= 0) return "Maintenant";
  const minutes = Math.round(ms / 60_000);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} j`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months} mois`;
  return `${Math.round(days / 365)} an(s)`;
}

export function MasterySections() {
  const [activeBucket, setActiveBucket] = useState<Bucket>("mastered");
  const [quizFilter, setQuizFilter] = useState<string>("ALL");

  const quizzesQuery = useQuery({ queryKey: ["quizzes"], queryFn: getQuizzes });
  const masteryQuery = useQuery({
    queryKey: ["mastery", quizFilter],
    queryFn: () => getMastery(quizFilter === "ALL" ? undefined : quizFilter),
  });

  const buckets = useMemo(() => {
    const result: Record<Bucket, MasteryItem[]> = { mastered: [], known: [], review: [] };
    if (!masteryQuery.data) return result;
    for (const item of masteryQuery.data) {
      result[bucketOf(item.confidence_score)].push(item);
    }
    // Sort by hanzi within each bucket for stable display.
    for (const key of Object.keys(result) as Bucket[]) {
      result[key].sort((a, b) => a.hanzi.localeCompare(b.hanzi));
    }
    return result;
  }, [masteryQuery.data]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mes mots par niveau de maîtrise</CardTitle>
        <CardDescription>
          Maîtrisés : score &gt; 0,9 · Connus : entre 0,5 et 0,9 · À revoir : sous 0,5.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">Filtrer :</span>
          <Button
            type="button"
            size="sm"
            variant={quizFilter === "ALL" ? "default" : "outline"}
            onClick={() => setQuizFilter("ALL")}
          >
            Tous
          </Button>
          {quizzesQuery.data?.map((quiz) => (
            <Button
              key={quiz.key}
              type="button"
              size="sm"
              variant={quizFilter === quiz.key ? "default" : "outline"}
              onClick={() => setQuizFilter(quiz.key)}
            >
              {quiz.title}
            </Button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2 border-b border-border pb-3">
          {BUCKETS.map((bucket) => {
            const Icon = bucket.icon;
            const count = buckets[bucket.id].length;
            const isActive = activeBucket === bucket.id;
            return (
              <button
                key={bucket.id}
                type="button"
                onClick={() => setActiveBucket(bucket.id)}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                )}
              >
                <Icon className={cn("h-4 w-4", isActive ? bucket.tone : "")} />
                <span>{bucket.label}</span>
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {masteryQuery.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : buckets[activeBucket].length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {activeBucket === "mastered" && "Aucun mot encore maîtrisé. Continue tes révisions."}
            {activeBucket === "known" && "Aucun mot dans la zone intermédiaire."}
            {activeBucket === "review" && "Aucun mot en difficulté. 🎉"}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-medium">Quiz</th>
                  <th className="px-3 py-2 font-medium">Hanzi</th>
                  <th className="px-3 py-2 font-medium">Pinyin</th>
                  <th className="px-3 py-2 font-medium">Traduction</th>
                  <th className="px-3 py-2 text-right font-medium">Score</th>
                  <th className="px-3 py-2 text-right font-medium">Reviews</th>
                  <th className="px-3 py-2 font-medium">Prochaine</th>
                </tr>
              </thead>
              <tbody>
                {buckets[activeBucket].map((item) => (
                  <tr
                    key={item.entry_id}
                    className="border-b border-border last:border-0 hover:bg-accent/30"
                  >
                    <td className="px-3 py-2 text-muted-foreground">{item.quiz_key}</td>
                    <td className="hanzi px-3 py-2 text-lg">{item.hanzi}</td>
                    <td className="px-3 py-2 text-muted-foreground">{item.pinyin}</td>
                    <td className="px-3 py-2">{item.translation}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {item.confidence_score.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                      {item.review_count}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      {formatNextReview(item.next_review_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
