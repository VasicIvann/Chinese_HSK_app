"use client";

import { motion } from "framer-motion";
import { RotateCw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { RatingEnum } from "@/lib/api/types";
import type { HistoryItem } from "@/lib/hooks/use-quiz-session";

const RATING_LABEL: Record<RatingEnum, string> = {
  again: "Faux",
  hard: "Difficile",
  good: "Juste",
  easy: "Je connais",
};

const RATING_TONE: Record<RatingEnum, string> = {
  again: "text-destructive",
  hard: "text-amber-600 dark:text-amber-400",
  good: "text-emerald-600 dark:text-emerald-400",
  easy: "text-sky-600 dark:text-sky-400",
};

function formatNextReview(iso: string | null | undefined): string {
  if (!iso) return "—";
  const due = new Date(iso);
  const now = new Date();
  const ms = due.getTime() - now.getTime();
  if (ms <= 0) return "tout de suite";
  const minutes = Math.round(ms / 60_000);
  if (minutes < 60) return `dans ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `dans ${hours} h`;
  const days = Math.round(hours / 24);
  if (days < 30) return `dans ${days} j`;
  const months = Math.round(days / 30);
  if (months < 12) return `dans ${months} mois`;
  const years = Math.round(days / 365);
  return `dans ${years} an(s)`;
}

export function QuizSummary({
  history,
  onRestart,
}: {
  history: HistoryItem[];
  onRestart: () => void;
}) {
  const total = history.length;
  const correct = history.filter((h) => h.rating === "good" || h.rating === "easy").length;
  const pct = total ? Math.round((correct / total) * 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-6"
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Session terminée
          </CardTitle>
          <CardDescription>
            {correct} / {total} maîtrisés ({pct}%). Les prochaines révisions sont déjà planifiées.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={onRestart} size="lg" className="w-full sm:w-auto">
            <RotateCw className="mr-1 h-4 w-4" />
            Nouvelle session
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Détail des mots vus</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/50 text-muted-foreground">
              <tr>
                <th className="px-4 py-2 text-left">Mot</th>
                <th className="px-4 py-2 text-left">Pinyin</th>
                <th className="px-4 py-2 text-left">Traduction</th>
                <th className="px-4 py-2 text-left">Rating</th>
                <th className="px-4 py-2 text-left">Prochaine</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.entry.id} className="border-b border-border last:border-0">
                  <td className="hanzi px-4 py-3 text-lg">{item.entry.hanzi}</td>
                  <td className="px-4 py-3 text-muted-foreground">{item.entry.pinyin}</td>
                  <td className="px-4 py-3">{item.entry.translation}</td>
                  <td className={`px-4 py-3 font-medium ${RATING_TONE[item.rating]}`}>
                    {RATING_LABEL[item.rating]}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatNextReview(item.nextReviewAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </motion.div>
  );
}
