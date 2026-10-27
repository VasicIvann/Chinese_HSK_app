/**
 * One typed function per backend endpoint. Each one returns the data directly
 * (no wrapping), so they compose well with TanStack Query.
 */

import { apiRequest, apiUrl } from "@/lib/api/client";
import type {
  AccountOverview,
  AccountSettings,
  DueEntry,
  EntryPublic,
  DrawingGallery,
  DrawingItem,
  ExampleGenerateResponse,
  ExpressionAttemptItem,
  HskVersion,
  LoginRequest,
  MasteryItem,
  MasterySnapshotResponse,
  QuizPublic,
  QuotaResponse,
  RateRequest,
  RegisterRequest,
  StatsResponse,
  SubjectGenerateResponse,
  SubjectItem,
  TokenResponse,
  UserPublic,
  WordExampleItem,
} from "@/lib/api/types";

// Auth

export function postRegister(body: RegisterRequest) {
  return apiRequest<TokenResponse>("/v1/auth/register", {
    method: "POST",
    body,
    withAuth: false,
  });
}

export function postLogin(body: LoginRequest) {
  return apiRequest<TokenResponse>("/v1/auth/login", {
    method: "POST",
    body,
    withAuth: false,
  });
}

export function getMe(token?: string) {
  return apiRequest<UserPublic>("/v1/auth/me", { token });
}

// Quizzes

/** Quizzes (levels) of one HSK version; the user's saved version when omitted. */
export function getQuizzes(version?: HskVersion) {
  return apiRequest<QuizPublic[]>(version ? `/v1/quizzes?version=${version}` : "/v1/quizzes");
}

export function getQuizEntries(quizKey: string) {
  return apiRequest<EntryPublic[]>(
    `/v1/quizzes/${encodeURIComponent(quizKey)}/entries`
  );
}

// SRS

/** Max questions per session accepted by the backend. */
export const MAX_SESSION_SIZE = 4000;

export function getDueEntries(
  quizzes: string[],
  count: number = 10,
  options: { newRatio?: number; onlyNew?: boolean; onlySeen?: boolean } = {}
) {
  const { newRatio = 0.3, onlyNew = false, onlySeen = false } = options;
  const params = new URLSearchParams();
  quizzes.forEach((q) => params.append("quiz", q));
  params.set("count", String(count));
  params.set("new_ratio", String(newRatio));
  if (onlyNew) params.set("only_new", "true");
  if (onlySeen) params.set("only_seen", "true");
  return apiRequest<DueEntry[]>(`/v1/srs/due?${params.toString()}`);
}

export function postRate(body: RateRequest) {
  return apiRequest<MasterySnapshotResponse>("/v1/srs/rate", {
    method: "POST",
    body,
  });
}

export function getStats(quizzes: string[] = []) {
  const params = new URLSearchParams();
  quizzes.forEach((q) => params.append("quiz", q));
  const qs = params.toString();
  return apiRequest<StatsResponse>(`/v1/srs/stats${qs ? `?${qs}` : ""}`);
}

// Mastery

export function getMastery(quiz?: string) {
  const qs = quiz ? `?quiz=${encodeURIComponent(quiz)}` : "";
  return apiRequest<MasteryItem[]>(`/v1/mastery${qs}`);
}

// Expression

export function getSubjects(level?: number) {
  const qs = level !== undefined ? `?level=${level}` : "";
  return apiRequest<SubjectItem[]>(`/v1/expression/subjects${qs}`);
}

export function postGenerateSubject(level: number, theme?: string) {
  return apiRequest<SubjectGenerateResponse>(
    "/v1/expression/subjects/generate",
    { method: "POST", body: { level, theme } }
  );
}

export function getAttempts(limit: number = 50) {
  return apiRequest<ExpressionAttemptItem[]>(
    `/v1/expression/attempts?limit=${limit}`
  );
}

export function getQuota() {
  return apiRequest<QuotaResponse>("/v1/expression/quota");
}

export function expressionCorrectUrl() {
  return apiUrl("/v1/expression/correct");
}

// Vocabulary examples

export function getWordExamples(entryId: number) {
  return apiRequest<WordExampleItem[]>(`/v1/examples?entry_id=${entryId}`);
}

export function postGenerateExample(entryId: number) {
  return apiRequest<ExampleGenerateResponse>("/v1/examples", {
    method: "POST",
    body: { entry_id: entryId },
  });
}

// Handwriting practice

export function getWordDrawings(entryId: number) {
  return apiRequest<DrawingItem[]>(`/v1/drawings?entry_id=${entryId}`);
}

export function postWordDrawing(entryId: number, image: string) {
  return apiRequest<DrawingItem>("/v1/drawings", {
    method: "POST",
    body: { entry_id: entryId, image },
  });
}

export function deleteWordDrawing(drawingId: number) {
  return apiRequest<void>(`/v1/drawings/${drawingId}`, { method: "DELETE" });
}

export function getDrawingGallery(offset = 0, limit = 20) {
  return apiRequest<DrawingGallery>(`/v1/drawings/gallery?limit=${limit}&offset=${offset}`);
}

// Account

export function getAccountSettings() {
  return apiRequest<AccountSettings>("/v1/account/settings");
}

/** Partial update: only the fields sent are changed. */
export function putAccountSettings(settings: Partial<AccountSettings>) {
  return apiRequest<AccountSettings>("/v1/account/settings", { method: "PUT", body: settings });
}

export function getAccountOverview() {
  return apiRequest<AccountOverview>("/v1/account/overview");
}
