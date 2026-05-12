/**
 * One typed function per backend endpoint. Each one returns the data directly
 * (no wrapping), so they compose well with TanStack Query.
 */

import { apiRequest, apiUrl } from "@/lib/api/client";
import type {
  DueEntry,
  EntryPublic,
  ExpressionAttemptItem,
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

export function getQuizzes() {
  return apiRequest<QuizPublic[]>("/v1/quizzes");
}

export function getQuizEntries(quizKey: string) {
  return apiRequest<EntryPublic[]>(
    `/v1/quizzes/${encodeURIComponent(quizKey)}/entries`
  );
}

// SRS

export function getDueEntries(
  quiz: string,
  count: number = 10,
  newRatio: number = 0.3
) {
  const params = new URLSearchParams({
    quiz,
    count: String(count),
    new_ratio: String(newRatio),
  });
  return apiRequest<DueEntry[]>(`/v1/srs/due?${params.toString()}`);
}

export function postRate(body: RateRequest) {
  return apiRequest<MasterySnapshotResponse>("/v1/srs/rate", {
    method: "POST",
    body,
  });
}

export function getStats(quiz?: string) {
  const qs = quiz ? `?quiz=${encodeURIComponent(quiz)}` : "";
  return apiRequest<StatsResponse>(`/v1/srs/stats${qs}`);
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
