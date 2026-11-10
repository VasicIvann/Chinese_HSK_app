/** Types and calls for the HSK-format practice (listening, writing, grammar). */

import { apiRequest } from "@/lib/api/client";
import type { HskVersion } from "@/lib/api/types";

export type Section = "listening" | "writing";
export type ExerciseLevel = 1 | 2 | 3;

/** One spoken turn: m = man, f = woman, n = narrator / single speaker. */
export type AudioLine = { s: "m" | "f" | "n"; t: string };

type Base = { id: string; level: number; versions?: HskVersion[]; generated?: boolean };

export type PicChoiceItem = Base & {
  type: "pic_choice" | "pic_answer";
  audio: AudioLine[];
  fr: string;
  options: string[];
  answer: number;
};
export type PicJudgeItem = Base & { type: "pic_judge"; audio: AudioLine[]; fr: string; picture: string; answer: boolean };
export type MatchQuestion = { audio: AudioLine[]; fr: string; answer: number };
export type MatchItem = Base & { type: "pic_match" | "word_match"; options: string[]; items: MatchQuestion[] };
export type McqItem = Base & {
  type: "short_mcq" | "long_mcq" | "passage_mcq";
  audio: AudioLine[];
  question: string;
  fr: string;
  question_fr: string;
  options: string[];
  options_fr: string[];
  answer: number;
};
export type PassageJudgeItem = Base & {
  type: "passage_judge";
  audio: AudioLine[];
  fr: string;
  statement: string;
  statement_fr: string;
  answer: boolean;
};
export type CharPinyinItem = Base & {
  type: "char_pinyin";
  before: string;
  pinyin: string;
  after: string;
  answer: string;
  fr: string;
};
export type ReorderItem = Base & { type: "reorder"; words: string[]; answers: string[]; fr: string };
/**
 * Imposed word. Words now come from the learner's vocabulary (pinyin + translation, no model
 * sentence: Claude writes one when the sentence is wrong); bank items had reference + fr.
 */
export type MakeSentenceItem = Base & {
  type: "make_sentence";
  word: string;
  pinyin?: string;
  translation?: string;
  source?: SentenceWords;
  reference?: string;
  fr?: string;
  /** Grammar-structure items: `word` is the structure (虽然……，但是……). */
  kind?: "structure";
  /** The hint: what the structure expresses (no pattern). */
  meaning?: string;
  /** Shown in the correction only when the sentence is wrong. */
  pattern?: string;
  example?: { zh: string; fr: string };
  grammar_point?: string;
  history?: "new" | "failed" | "passed";
};

/**
 * What is imposed: any already-seen word, one of the 50 weakest "À revoir" words,
 * or a grammar structure of HSK 2-3.
 */
export type SentenceWords = "seen" | "weak" | "structures";

export type ExerciseItem =
  | PicChoiceItem
  | PicJudgeItem
  | MatchItem
  | McqItem
  | PassageJudgeItem
  | CharPinyinItem
  | ReorderItem
  | MakeSentenceItem;

export type PartInfo = {
  part: string;
  numbers: string;
  type: string;
  count: number;
  pinyin: boolean;
  title: string;
  how: string;
  mix?: { type: string; count: number }[];
};

export type CatalogPart = PartInfo & {
  available: number;
  /** Imposed-word part only: words offered by each source. */
  word_counts?: (Record<SentenceWords, number> & { structures_new?: number }) | null;
  attempts: number;
  last: { score: number; total: number; at: string } | null;
  best: { score: number; total: number } | null;
};

export type Catalog = { version: HskVersion; level: number; section: Section; parts: CatalogPart[] };

export type ExerciseSet = {
  version: HskVersion;
  level: number;
  section: Section;
  part: string;
  parts: (PartInfo & { items: ExerciseItem[]; word_source?: SentenceWords; word_pool?: number })[];
  quota_remaining?: number;
};

export type SentenceCheck = {
  correct: boolean;
  uses_word: boolean;
  corrected: string;
  pinyin: string;
  translation: string;
  explanation: string;
  /** Only when the sentence is wrong: a model sentence written by Claude. */
  model?: string;
  model_pinyin?: string;
  model_translation?: string;
};

export type GrammarExample = { zh: string; fr: string };
export type GrammarQuiz = { q: string; options: string[]; answer: number; why: string };
export type GrammarPoint = {
  id: string;
  /** Official code, e.g. "二60". */
  code: string;
  level: number;
  no: number;
  item: string;
  category: string;
  detail: string;
  content: string;
  title: string;
  explanation: string;
  pattern: string;
  examples: GrammarExample[];
  quiz: GrammarQuiz[];
  last: { score: number; total: number } | null;
};

// The page sends the HSK version it shows, so a switch in progress never mixes formats.

export function getCatalog(section: Section, level: ExerciseLevel, version: HskVersion) {
  return apiRequest<Catalog>(`/v1/exercises/catalog?section=${section}&level=${level}&version=${version}`);
}

export function getExerciseSet(
  section: Section,
  level: ExerciseLevel,
  part: string,
  version: HskVersion,
  words: SentenceWords = "seen"
) {
  return apiRequest<ExerciseSet>(
    `/v1/exercises/set?section=${section}&level=${level}&part=${encodeURIComponent(part)}&version=${version}&words=${words}`
  );
}

export function generateExerciseSet(section: Section, level: ExerciseLevel, part: string, version: HskVersion) {
  return apiRequest<ExerciseSet>("/v1/exercises/generate", {
    method: "POST",
    body: { section, level, part, version },
  });
}

export function postExerciseResult(body: {
  section: Section | "grammar" | "classifiers" | "tones";
  version?: HskVersion;
  level: ExerciseLevel;
  part: string;
  answers: { id: string; correct: boolean }[];
}) {
  return apiRequest<{ id: number; score: number; total: number }>("/v1/exercises/results", {
    method: "POST",
    body,
  });
}

export function checkSentence(level: ExerciseLevel, word: string, sentence: string, meaning?: string) {
  return apiRequest<SentenceCheck>("/v1/exercises/check-sentence", {
    method: "POST",
    body: { level, word, sentence, ...(meaning ? { meaning } : {}) },
  });
}

export function checkStructure(level: ExerciseLevel, structure: string, sentence: string, meaning?: string) {
  return apiRequest<SentenceCheck>("/v1/exercises/check-structure", {
    method: "POST",
    body: { level, structure, sentence, ...(meaning ? { meaning } : {}) },
  });
}

export function getGrammar(level: ExerciseLevel, version: HskVersion) {
  return apiRequest<{ level: number; version: HskVersion; points: GrammarPoint[] }>(
    `/v1/grammar?level=${level}&version=${version}`
  );
}
