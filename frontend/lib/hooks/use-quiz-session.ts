"use client";

import { useCallback, useMemo, useState } from "react";

import type { DueEntry, RatingEnum } from "@/lib/api/types";

export type QuizMode = "auto-assess" | "pinyin-input";

export type HistoryItem = {
  entry: DueEntry;
  rating: RatingEnum;
  userInput?: string;
  inputCorrect?: boolean;
  nextReviewAt?: string | null;
  stabilityDays?: number | null;
};

export type SessionState = {
  questions: DueEntry[];
  currentIndex: number;
  history: HistoryItem[];
};

/**
 * In-memory state machine for one quiz session. The optimistic UI logic lives
 * here: a `recordRating()` call advances the index immediately so the next
 * question renders before any network request resolves.
 */
export function useQuizSession(initialQuestions: DueEntry[]) {
  const [state, setState] = useState<SessionState>({
    questions: initialQuestions,
    currentIndex: 0,
    history: [],
  });

  const currentEntry = state.questions[state.currentIndex];
  const isFinished = state.currentIndex >= state.questions.length;
  const progress = state.questions.length
    ? Math.min((state.currentIndex + 1) / state.questions.length, 1)
    : 0;

  const recordRating = useCallback(
    (
      rating: RatingEnum,
      meta?: { userInput?: string; inputCorrect?: boolean }
    ) => {
      setState((prev) => {
        const entry = prev.questions[prev.currentIndex];
        if (!entry) return prev;
        const item: HistoryItem = {
          entry,
          rating,
          userInput: meta?.userInput,
          inputCorrect: meta?.inputCorrect,
        };
        return {
          ...prev,
          currentIndex: prev.currentIndex + 1,
          history: [...prev.history, item],
        };
      });
    },
    []
  );

  const attachSnapshot = useCallback(
    (entryId: number, snapshot: { nextReviewAt: string | null; stabilityDays: number | null }) => {
      setState((prev) => ({
        ...prev,
        history: prev.history.map((item) =>
          item.entry.id === entryId
            ? {
                ...item,
                nextReviewAt: snapshot.nextReviewAt,
                stabilityDays: snapshot.stabilityDays,
              }
            : item
        ),
      }));
    },
    []
  );

  const reset = useCallback((newQuestions: DueEntry[]) => {
    setState({ questions: newQuestions, currentIndex: 0, history: [] });
  }, []);

  const score = useMemo(
    () => state.history.filter((h) => h.rating === "good" || h.rating === "easy").length,
    [state.history]
  );

  return {
    state,
    currentEntry,
    isFinished,
    progress,
    score,
    recordRating,
    attachSnapshot,
    reset,
  };
}
