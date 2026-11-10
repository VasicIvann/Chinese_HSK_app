import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { QuizQuestion } from "@/components/quiz/quiz-question";
import type { DueEntry } from "@/lib/api/types";
import type { QuizMode } from "@/lib/hooks/use-quiz-session";
import { hanziMatches } from "@/lib/pinyin";

const settings = { hsk_version: "3.0" as const, pinyin_locked: false };

vi.mock("@/lib/api/endpoints", () => ({
  getAccountSettings: async () => ({ ...settings }),
  putAccountSettings: async (next: Partial<typeof settings>) => Object.assign(settings, next),
}));
vi.mock("@/components/quiz/word-study-tools", () => ({
  WordStudyTools: ({ entry }: { entry: DueEntry }) => <div data-testid="study-tools">{entry.hanzi}</div>,
}));
vi.mock("@/components/listen-button", () => ({
  ListenButton: () => <button type="button">Écouter</button>,
}));

const ENTRY: DueEntry = {
  id: 7,
  quiz_id: 1,
  hanzi: "帮助",
  pinyin: "bāngzhù",
  translation: "aider",
  alt_translations: "aider; aide",
  tags: null,
};

function renderQuestion(mode: QuizMode = "hanzi-input") {
  const onRate = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <QuizQuestion entry={ENTRY} mode={mode} onRate={onRate} />
    </QueryClientProvider>
  );
  return onRate;
}

const answerBox = () => screen.getByLabelText("Ta réponse en hanzi");

describe("hanziMatches", () => {
  it("ignores spaces and punctuation but not other characters", () => {
    expect(hanziMatches(" 帮 助。", "帮助")).toBe(true);
    expect(hanziMatches("帮忙", "帮助")).toBe(false);
    expect(hanziMatches("", "帮助")).toBe(false);
  });
});

describe("QuizQuestion — hanzi input mode", () => {
  beforeEach(() => {
    settings.pinyin_locked = false;
  });

  it("shows the translation and hides every trace of the characters before checking", () => {
    renderQuestion();
    expect(screen.getByTestId("prompt-translation")).toHaveTextContent("aider");
    expect(screen.getByText("Écris le mot en hanzi")).toBeInTheDocument();
    expect(screen.queryByText("帮助")).not.toBeInTheDocument();
    expect(screen.queryByTestId("study-tools")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Écouter" })).not.toBeInTheDocument();
    expect(screen.queryByText("bāngzhù")).not.toBeInTheDocument();
  });

  it("reveals the pinyin on demand without revealing the hanzi", () => {
    renderQuestion();
    fireEvent.click(screen.getByRole("button", { name: /indice pinyin/i }));
    expect(screen.getByText("bāngzhù")).toBeInTheDocument();
    expect(screen.queryByText("帮助")).not.toBeInTheDocument();
  });

  it("checks a correct answer, then passes the input along with the rating", () => {
    const onRate = renderQuestion();
    fireEvent.change(answerBox(), { target: { value: "帮助" } });
    fireEvent.click(screen.getByRole("button", { name: "Vérifier" }));
    expect(screen.getByText("Bonne réponse !")).toBeInTheDocument();
    expect(screen.getByTestId("solution-hanzi")).toHaveTextContent("帮助");
    expect(screen.getByTestId("study-tools")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Écouter" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /juste/i }));
    expect(onRate).toHaveBeenCalledWith("good", { userInput: "帮助", inputCorrect: true });
  });

  it("shows the expected word after a wrong answer", () => {
    const onRate = renderQuestion();
    fireEvent.change(answerBox(), { target: { value: "帮忙" } });
    fireEvent.keyDown(answerBox(), { key: "Enter" });
    expect(screen.getByText("Mot attendu : 帮助")).toBeInTheDocument();
    expect(answerBox()).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /faux/i }));
    expect(onRate).toHaveBeenCalledWith("again", { userInput: "帮忙", inputCorrect: false });
  });

  it("does not check while the IME is still composing", () => {
    renderQuestion();
    fireEvent.change(answerBox(), { target: { value: "bang" } });
    fireEvent.keyDown(answerBox(), { key: "Enter", isComposing: true });
    expect(screen.queryByText(/Mot attendu/)).not.toBeInTheDocument();
    expect(answerBox()).not.toBeDisabled();
  });

  it("'show the solution' reveals hanzi and pinyin without an answer", () => {
    renderQuestion();
    fireEvent.click(screen.getByRole("button", { name: /afficher la solution/i }));
    expect(screen.getByTestId("solution-hanzi")).toHaveTextContent("帮助");
    expect(screen.getByText("bāngzhù")).toBeInTheDocument();
  });

  it("the pinyin lock also applies to this mode", async () => {
    settings.pinyin_locked = true;
    renderQuestion();
    expect(await screen.findByTestId("locked-pinyin")).toHaveTextContent("bāngzhù");
    expect(screen.queryByText("帮助")).not.toBeInTheDocument();
  });

  it("other modes still show the hanzi up front", () => {
    renderQuestion("pinyin-input");
    expect(screen.getByText("帮助", { selector: "p.hanzi" })).toBeInTheDocument();
    expect(screen.getByTestId("study-tools")).toBeInTheDocument();
    expect(screen.getByLabelText("Ta réponse en pinyin")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /indice pinyin/i })).not.toBeInTheDocument();
  });
});
