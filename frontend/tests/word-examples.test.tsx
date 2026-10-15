import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WordExamples } from "@/components/quiz/word-examples";
import type { DueEntry, WordExampleItem } from "@/lib/api/types";

const getWordExamples = vi.fn();
const postGenerateExample = vi.fn();

vi.mock("@/lib/api/endpoints", () => ({
  getWordExamples: (id: number) => getWordExamples(id),
  postGenerateExample: (id: number) => postGenerateExample(id),
}));

const entry: DueEntry = {
  id: 7,
  quiz_id: 1,
  hanzi: "本",
  pinyin: "běn",
  translation: "classificateur (livres)",
  alt_translations: null,
  tags: null,
};

function example(id: number, sentence: string): WordExampleItem {
  return {
    id,
    entry_id: 7,
    hsk_level: 1,
    sentence,
    pinyin: "pinyin",
    translation: "traduction",
    meaning_in_sentence: "sens ici",
    general_meaning: "sens général",
    created_at: "2026-10-15T00:00:00Z",
  };
}

function renderWidget() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <WordExamples entry={entry} />
    </QueryClientProvider>
  );
}

describe("WordExamples", () => {
  beforeEach(() => {
    getWordExamples.mockReset();
    postGenerateExample.mockReset();
  });

  it("shows only the generate button when the word has no saved example", async () => {
    getWordExamples.mockResolvedValue([]);
    renderWidget();
    expect(await screen.findByRole("button", { name: /générer un exemple/i })).toBeEnabled();
    await waitFor(() => expect(getWordExamples).toHaveBeenCalledWith(7));
    expect(screen.queryByRole("button", { name: /exemples précédents/i })).toBeNull();
  });

  it("generates an example, displays it, and keeps older ones behind the history button", async () => {
    getWordExamples.mockResolvedValue([example(1, "我有一本书。")]);
    postGenerateExample.mockResolvedValue({
      example: example(2, "这本书很好。"),
      quota_remaining: 98,
    });
    renderWidget();

    const history = await screen.findByRole("button", { name: /voir les exemples précédents \(1\)/i });
    fireEvent.click(screen.getByRole("button", { name: /générer un exemple/i }));

    expect(await screen.findByText("sens général")).toBeInTheDocument();
    expect(postGenerateExample).toHaveBeenCalledWith(7);
    expect(screen.getByText("书很好。", { exact: false })).toBeInTheDocument();
    // The older example stays hidden until the history is opened.
    expect(screen.queryByText("我有一", { exact: false })).toBeNull();

    fireEvent.click(history);
    expect(screen.getByText("我有一", { exact: false })).toBeInTheDocument();
  });

  it("shows the API error message when generation fails", async () => {
    const { ApiError } = await import("@/lib/api/client");
    getWordExamples.mockResolvedValue([]);
    postGenerateExample.mockRejectedValue(new ApiError(429, "Quota quotidien atteint."));
    renderWidget();

    fireEvent.click(await screen.findByRole("button", { name: /générer un exemple/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Quota quotidien atteint.");
  });
});
