"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { QuizQuestion } from "@/components/quiz/quiz-question";
import { QuizSetup } from "@/components/quiz/quiz-setup";
import { QuizSummary } from "@/components/quiz/quiz-summary";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { getDueEntries, postRate } from "@/lib/api/endpoints";
import type { DueEntry, MasterySnapshotResponse, RatingEnum } from "@/lib/api/types";
import { useQuizSession, type QuizMode } from "@/lib/hooks/use-quiz-session";

type Phase = "setup" | "loading" | "running" | "summary";

type SessionConfig = {
  quiz: string;
  count: number;
  mode: QuizMode;
};

export default function ComprehensionPage() {
  const [phase, setPhase] = useState<Phase>("setup");
  const [config, setConfig] = useState<SessionConfig | null>(null);
  const [questions, setQuestions] = useState<DueEntry[]>([]);
  const queryClient = useQueryClient();

  const session = useQuizSession(questions);

  const rateMutation = useMutation({
    mutationFn: ({ entryId, rating }: { entryId: number; rating: RatingEnum }) =>
      postRate({ entry_id: entryId, rating }),
    onSuccess: (snapshot: MasterySnapshotResponse) => {
      session.attachSnapshot(snapshot.entry_id, {
        nextReviewAt: snapshot.next_review_at,
        stabilityDays: snapshot.stability_days,
      });
      // Invalidate cached stats so the next setup screen shows fresh counts.
      queryClient.invalidateQueries({ queryKey: ["srs-stats"] });
      queryClient.invalidateQueries({ queryKey: ["mastery"] });
    },
    onError: (error: unknown) => {
      const detail = error instanceof ApiError ? error.detail : "Erreur réseau";
      toast.error(`Rating non sauvegardé : ${detail}`, {
        description: "L'enregistrement réessaiera automatiquement à la prochaine action.",
      });
    },
    retry: 2,
  });

  const handleStart = useCallback(
    async (cfg: SessionConfig) => {
      setPhase("loading");
      try {
        const entries = await getDueEntries(cfg.quiz, cfg.count);
        if (entries.length === 0) {
          toast.info("Aucune carte à étudier pour ce quiz.");
          setPhase("setup");
          return;
        }
        setConfig(cfg);
        setQuestions(entries);
        session.reset(entries);
        setPhase("running");
      } catch (error) {
        const detail = error instanceof ApiError ? error.detail : "Erreur réseau";
        toast.error(`Impossible de charger la session : ${detail}`);
        setPhase("setup");
      }
    },
    [session]
  );

  const handleRate = useCallback(
    (rating: RatingEnum, meta?: { userInput?: string; inputCorrect?: boolean }) => {
      const entry = session.currentEntry;
      if (!entry) return;
      session.recordRating(rating, meta);
      rateMutation.mutate({ entryId: entry.id, rating });
      // Once the last question is answered, switch to summary.
      if (session.state.currentIndex + 1 >= session.state.questions.length) {
        setPhase("summary");
      }
    },
    [session, rateMutation]
  );

  const handleRestart = useCallback(() => {
    setPhase("setup");
    setConfig(null);
    setQuestions([]);
  }, []);

  if (phase === "setup" || phase === "loading") {
    return <QuizSetup onStart={handleStart} isLoading={phase === "loading"} />;
  }

  if (phase === "summary") {
    return <QuizSummary history={session.state.history} onRestart={handleRestart} />;
  }

  // phase === "running"
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {config?.quiz} · Question {Math.min(session.state.currentIndex + 1, session.state.questions.length)} /{" "}
          {session.state.questions.length}
        </p>
        <Button variant="ghost" size="sm" onClick={handleRestart}>
          Quitter
        </Button>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full bg-primary"
          initial={false}
          animate={{ width: `${session.progress * 100}%` }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
      </div>

      {session.currentEntry && config && (
        <QuizQuestion
          entry={session.currentEntry}
          mode={config.mode}
          onRate={handleRate}
        />
      )}
    </div>
  );
}
