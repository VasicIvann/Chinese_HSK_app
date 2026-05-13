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

export type QuizPublic = {
  id: number;
  key: string;
  title: string;
  description: string | null;
  level: number | null;
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

export type AccountOverview = {
  profile: ProfileSummary;
  mastery: MasteryDistribution;
  activity_heatmap: ActivityCell[];
  quiz_progression: QuizDailyPoint[];
  expression_progression: ExpressionScorePoint[];
};
