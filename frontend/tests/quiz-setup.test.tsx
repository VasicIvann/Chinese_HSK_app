import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { QuizSetup } from "@/components/quiz/quiz-setup";

const getQuizzes = vi.fn();
const getStats = vi.fn();

vi.mock("@/lib/api/endpoints", () => ({
  MAX_SESSION_SIZE: 2000,
  getQuizzes: () => getQuizzes(),
  getStats: (q: string[]) => getStats(q),
}));

// Stats per level: HSK1 = 150 words (20 seen), HSK2 = 150 (all new), HSK3 = 300 (all new).
const STATS: Record<string, { due: number; new: number; upcoming: number }> = {
  HSK1: { due: 5, new: 130, upcoming: 15 },
  HSK2: { due: 0, new: 150, upcoming: 0 },
  HSK3: { due: 0, new: 300, upcoming: 0 },
};

function renderSetup(onStart = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <QuizSetup onStart={onStart} />
    </QueryClientProvider>
  );
  return onStart;
}

const startButton = () => screen.getByRole("button", { name: /lancer la session/i });

describe("QuizSetup", () => {
  beforeEach(() => {
    getQuizzes.mockResolvedValue([
      { id: 1, key: "HSK1", title: "HSK 1", description: null, level: 1 },
      { id: 2, key: "HSK2", title: "HSK 2", description: null, level: 2 },
      { id: 3, key: "HSK3", title: "HSK 3", description: null, level: 3 },
    ]);
    getStats.mockImplementation(async (keys: string[]) =>
      (keys.length ? keys : Object.keys(STATS)).reduce(
        (acc, k) => ({
          due: acc.due + STATS[k].due,
          new: acc.new + STATS[k].new,
          upcoming: acc.upcoming + STATS[k].upcoming,
        }),
        { due: 0, new: 0, upcoming: 0 }
      )
    );
  });

  it("selects several levels and starts with all of them", async () => {
    const onStart = renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 3" }));
    fireEvent.click(screen.getByRole("button", { name: "HSK 2" }));

    await waitFor(() => expect(getStats).toHaveBeenLastCalledWith(["HSK2", "HSK3"]));
    expect(screen.getByRole("button", { name: /HSK 2/ })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(startButton());
    expect(onStart).toHaveBeenCalledWith({
      quizzes: ["HSK2", "HSK3"],
      count: 10,
      mode: "auto-assess",
      onlyNew: false,
    });
  });

  it("MAX uses every word of the selected levels", async () => {
    const onStart = renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 2" }));
    fireEvent.click(screen.getByRole("button", { name: "HSK 3" }));

    const max = await screen.findByRole("button", { name: "MAX (450)" });
    fireEvent.click(max);
    fireEvent.click(startButton());
    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ count: 450 }));
  });

  it("accepts a custom number of questions", async () => {
    const onStart = renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 1" }));
    const input = screen.getByRole("textbox", { name: /nombre de questions personnalisé/i });
    fireEvent.change(input, { target: { value: "27" } });

    await waitFor(() => expect(startButton()).toHaveTextContent("(27)"));
    fireEvent.click(startButton());
    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ quizzes: ["HSK1"], count: 27 }));
  });

  it("caps a custom number at the words available", async () => {
    const onStart = renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 1" }));
    fireEvent.change(screen.getByRole("textbox", { name: /personnalisé/i }), {
      target: { value: "999" },
    });
    expect(await screen.findByText(/Seulement 150 mots disponibles/)).toBeInTheDocument();
    fireEvent.click(startButton());
    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ count: 150 }));
  });

  it("only-new mode counts never-seen words and passes the flag", async () => {
    const onStart = renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 1" }));
    fireEvent.click(screen.getByRole("switch", { name: /nouveaux mots uniquement/i }));

    fireEvent.click(await screen.findByRole("button", { name: "MAX (130)" }));
    fireEvent.click(startButton());
    expect(onStart).toHaveBeenCalledWith(
      expect.objectContaining({ quizzes: ["HSK1"], count: 130, onlyNew: true })
    );
  });

  it("blocks the start when every word was already seen in only-new mode", async () => {
    STATS.HSK1 = { due: 10, new: 0, upcoming: 140 };
    renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 1" }));
    fireEvent.click(screen.getByRole("switch", { name: /nouveaux mots uniquement/i }));

    expect(await screen.findByText(/déjà vu tous les mots/)).toBeInTheDocument();
    expect(startButton()).toBeDisabled();
    STATS.HSK1 = { due: 5, new: 130, upcoming: 15 };
  });

  it("cannot start without a level", async () => {
    renderSetup();
    await screen.findByRole("button", { name: "HSK 1" });
    expect(startButton()).toBeDisabled();
  });
});
