import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { QuizQuestion } from "@/components/quiz/quiz-question";
import type { DueEntry } from "@/lib/api/types";
import type { QuizMode } from "@/lib/hooks/use-quiz-session";

const settings = { hsk_version: "3.0" as const, pinyin_locked: true };
const putAccountSettings = vi.fn(async (next: Partial<typeof settings>) => ({ ...settings, ...next }));

vi.mock("@/lib/api/endpoints", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/endpoints")>()),
  getAccountSettings: async () => ({ ...settings }),
  putAccountSettings: (s: Partial<typeof settings>) => putAccountSettings(s),
}));
vi.mock("@/components/quiz/word-study-tools", () => ({ WordStudyTools: () => null }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const entry = {
  id: 7,
  quiz_id: 1,
  hanzi: "觉得",
  pinyin: "juéde",
  translation: "trouver, penser",
  alt_translations: null,
  tags: null,
} as unknown as DueEntry;

function renderQuestion(mode: QuizMode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <QuizQuestion entry={entry} mode={mode} onRate={vi.fn()} />
    </QueryClientProvider>
  );
}

describe("pinyin lock in the vocabulary quiz", () => {
  beforeEach(() => {
    settings.pinyin_locked = true;
    putAccountSettings.mockClear();
  });

  it("shows the pinyin from the start, once, and can be unlocked from the card", async () => {
    renderQuestion("auto-assess");
    expect(await screen.findByTestId("locked-pinyin")).toHaveTextContent("juéde");
    expect(screen.queryByRole("button", { name: /indice pinyin/i })).not.toBeInTheDocument();

    // Revealing the solution does not print the pinyin a second time.
    fireEvent.click(screen.getByRole("button", { name: /afficher la solution/i }));
    expect(screen.getByText("trouver, penser")).toBeInTheDocument();
    expect(screen.getAllByText("juéde")).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: /pinyin verrouillé/i }));
    await waitFor(() => expect(putAccountSettings).toHaveBeenCalledWith({ pinyin_locked: false }));
    await waitFor(() => expect(screen.queryByTestId("locked-pinyin")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: /toujours afficher le pinyin/i })).toBeInTheDocument();
  });

  it("is ignored when the pinyin has to be typed", async () => {
    renderQuestion("pinyin-input");
    // Let the settings query resolve (lock is on), then check nothing leaks.
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByTestId("locked-pinyin")).not.toBeInTheDocument();
    expect(screen.queryByText("juéde")).not.toBeInTheDocument();
  });
});
