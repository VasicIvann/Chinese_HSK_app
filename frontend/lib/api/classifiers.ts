/** Types and calls for the Classificateurs (量词) tab. */

import { apiRequest } from "@/lib/api/client";
import type { ExerciseLevel } from "@/lib/api/exercises";
import type { HskVersion } from "@/lib/api/types";

export type ClassifierKind = "nominal" | "verbal" | "both";

export type Classifier = {
  hanzi: string;
  pinyin: string;
  kind: ClassifierKind;
  /** Level of the classifier in the selected version (≤ the level shown). */
  level: number;
  usage: string;
  explanation: string;
  traps: string;
  nouns: { zh: string; fr: string; in_level: boolean }[];
  examples: { zh: string; fr: string }[];
  sentence_count: number;
};

export type ClassifierList = { version: HskVersion; level: number; classifiers: Classifier[]; sentences: number };

export type FillQuestion = {
  id: string;
  mode: "fill";
  before: string;
  after: string;
  sentence: string;
  options: string[];
  answer: number;
  fr: string;
  classifier: string;
  explain: string;
  generated: boolean;
};

export type UsageQuestion = {
  id: string;
  mode: "usage";
  kind: "usage_to_cl" | "noun_to_cl" | "cl_to_usage";
  classifier: string;
  /** usage_to_cl: the usage (French) · noun_to_cl: the noun · cl_to_usage: the classifier. */
  prompt: string;
  prompt_fr?: string;
  pinyin?: string;
  /** Classifiers, or usages (French) for cl_to_usage. */
  options: string[];
  option_hanzi?: string[];
  answer: number;
  explain: string;
};

export type ClassifierQuestion = FillQuestion | UsageQuestion;
export type QuizMode = "fill" | "usage";

export type ClassifierQuiz = {
  mode: QuizMode;
  version: HskVersion;
  level: number;
  hanzi: string | null;
  questions: ClassifierQuestion[];
  quota_remaining?: number;
};

export function getClassifiers(level: ExerciseLevel, version: HskVersion) {
  return apiRequest<ClassifierList>(`/v1/classifiers?level=${level}&version=${version}`);
}

export function getClassifierQuiz(mode: QuizMode, level: ExerciseLevel, version: HskVersion, hanzi?: string) {
  const focus = hanzi ? `&hanzi=${encodeURIComponent(hanzi)}` : "";
  return apiRequest<ClassifierQuiz>(`/v1/classifiers/quiz?mode=${mode}&level=${level}&version=${version}${focus}`);
}

export function generateClassifierSentences(level: ExerciseLevel, version: HskVersion, hanzi?: string) {
  return apiRequest<ClassifierQuiz>("/v1/classifiers/generate", {
    method: "POST",
    body: { level, version, ...(hanzi ? { hanzi } : {}) },
  });
}
