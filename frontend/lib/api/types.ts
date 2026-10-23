/**
 * Hand-written API types mirroring the FastAPI Pydantic schemas.
 *
 * These are duplicated from the backend on purpose so the frontend can be
 * developed against a stable contract even before running the codegen step.
 *
 * To regenerate from the live backend's OpenAPI spec:
 *   1. Start the backend: `uvicorn app.main:app --port 8000` (from backend/)
 *   2. Run `npm run gen:api` (writes ./generated.ts)
 *   3. Replace this file's contents with the generated types
 */

export type UserPublic = {
  id: number;
  email: string;
  locale: string;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  user: UserPublic;
};

export type RegisterRequest = {
  email: string;
  password: string;
  locale?: "fr" | "en";
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type HskVersion = "2.0" | "3.0";

export type QuizPublic = {
  id: number;
  key: string;
  title: string;
  description: string | null;
  level: number | null;
  version: HskVersion;
};

export type AccountSettings = {
  hsk_version: HskVersion;
  /** Vocabulary quiz (self-assessment): pinyin shown from the start of every card. */
  pinyin_locked: boolean;
};

export type EntryPublic = {
  id: number;
  quiz_id: number;
  hanzi: string;
  pinyin: string;
  translation: string;
  alt_translations: string | null;
  tags: string | null;
};

export type RatingEnum = "again" | "hard" | "good" | "easy";

export type RateRequest = {
  entry_id: number;
  rating: RatingEnum;
  /** Optional context stored in the review history. */
  mode?: "auto-assess" | "pinyin-input";
  elapsed_ms?: number;
};

export type MasterySnapshotResponse = {
  entry_id: number;
  rating: RatingEnum;
  rating_value: number;
  confidence_score: number;
  review_count: number;
  last_seen_at: string;
  next_review_at: string | null;
  stability_days: number | null;
  difficulty: number | null;
  state: number | null;
};

export type DueEntry = EntryPublic;

export type StatsResponse = {
  due: number;
  new: number;
  upcoming: number;
};

export type MasteryItem = {
  quiz_key: string;
  quiz_title: string;
  entry_id: number;
  hanzi: string;
  pinyin: string;
  translation: string;
  status: string;
  confidence_score: number;
  review_count: number;
  last_seen_at: string;
  next_review_at: string | null;
  stability_days: number | null;
  last_rating: number | null;
};

export type SubjectItem = {
  subject: string;
  keywords: string[];
};

export type SubjectGenerateResponse = {
  subject: string;
  keywords: string[];
  quota_remaining: number;
};

export type ExpressionErrorItem = {
  type: string;
  segment: string;
  correction: string;
  explanation: string;
};

export type CorrectionPayload = {
  score: number | null;
  corrected_version: string;
  pinyin: string;
  french_translation: string;
  errors: ExpressionErrorItem[];
  vocabulary_mistakes: string[];
  strengths: string[];
  next_step_advice: string;
};

export type ExpressionAttemptItem = {
  id: number;
  hsk_level: number;
  subject: string;
  user_text: string;
  correction: CorrectionPayload;
  score: number | null;
  tokens_input: number;
  tokens_output: number;
  model_id: string;
  created_at: string;
};

export type QuotaStatus = {
  kind: string;
  count: number;
  limit: number;
  remaining: number;
};

export type QuotaResponse = {
  correction: QuotaStatus;
  subject_generation: QuotaStatus;
};

// Account dashboard

export type MasteryDistribution = {
  mastered: number;
  learning: number;
  new: number;
  total_entries: number;
};

export type ActivityCell = {
  date: string; // YYYY-MM-DD
  count: number;
};

export type QuizDailyPoint = {
  date: string;
  avg_rating: number;
  count: number;
};

export type ExpressionScorePoint = {
  date: string; // ISO datetime
  score: number;
};

export type ProfileSummary = {
  email: string;
  locale: string;
  joined_at: string;
  total_reviews: number;
  total_expressions: number;
};

export type LevelProgress = {
  quiz_key: string;
  title: string;
  level: number | null;
  total: number;
  mastered: number;
  learning: number;
  new: number;
};

export type StreakSummary = {
  current: number;
  best: number;
  studied_today: boolean;
};

export type SuccessRate = {
  /** 0..1, null without reviews in the window. */
  last_7_days: number | null;
  last_30_days: number | null;
  reviews_7_days: number;
  reviews_30_days: number;
  daily: { date: string; rate: number | null; count: number }[];
  /** First day recorded in the review history. */
  tracking_since: string | null;
};

export type UpcomingReviews = {
  due_now: number;
  /** Includes overdue. */
  due_today: number;
  due_tomorrow: number;
  /** Cumulative over 7 days, includes overdue. */
  due_next_7_days: number;
  /** Day 0 includes overdue. */
  forecast: { date: string; count: number }[];
};

export type AccountOverview = {
  profile: ProfileSummary;
  mastery: MasteryDistribution;
  activity_heatmap: ActivityCell[];
  quiz_progression: QuizDailyPoint[];
  expression_progression: ExpressionScorePoint[];
  level_progress: LevelProgress[];
  streak: StreakSummary;
  success_rate: SuccessRate;
  upcoming: UpcomingReviews;
  /** HSK version the word-level numbers are computed for. */
  hsk_version: HskVersion;
};

export type WordExampleItem = {
  id: number;
  entry_id: number;
  hsk_level: number | null;
  sentence: string;
  pinyin: string;
  translation: string;
  meaning_in_sentence: string;
  general_meaning: string;
  /** Empty for examples generated before this field existed. */
  decomposition: string;
  created_at: string;
};

export type DrawingItem = {
  id: number;
  entry_id: number;
  /** PNG data URL, usable directly as <img src>. */
  image: string;
  width: number;
  height: number;
  created_at: string;
};

export type DrawingWordGroup = {
  entry_id: number;
  hanzi: string;
  pinyin: string;
  translation: string;
  hsk_level: number | null;
  count: number;
  latest_at: string;
  /** The latest few drawings only (see `count` for the total). */
  drawings: DrawingItem[];
};

export type DrawingGallery = {
  total_drawings: number;
  total_words: number;
  words: DrawingWordGroup[];
  has_more: boolean;
};

export type ExampleGenerateResponse = {
  example: WordExampleItem;
  quota_remaining: number;
};
