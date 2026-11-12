import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { QuizSetup } from "@/components/quiz/quiz-setup";

const getQuizzes = vi.fn();
const getStats = vi.fn();
const settings = { hsk_version: "3.0" as "2.0" | "3.0", pinyin_locked: false };
const putAccountSettings = vi.fn(async (next: Partial<typeof settings>) => {
  Object.assign(settings, next);
  return { ...settings };
});

vi.mock("@/lib/api/endpoints", () => ({
  MAX_SESSION_SIZE: 2000,
  getQuizzes: (version?: string) => getQuizzes(version),
  getStats: (q: string[]) => getStats(q),
  getAccountSettings: async () => ({ ...settings }),
  putAccountSettings: (s: Partial<typeof settings>) => putAccountSettings(s),
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
    settings.hsk_version = "3.0";
    settings.pinyin_locked = false;
    putAccountSettings.mockClear();
    getQuizzes.mockImplementation(async (version?: string) =>
      version === "2.0"
        ? [
            { id: 11, key: "HSK1-2.0", title: "HSK 1", description: null, level: 1, version: "2.0" },
            { id: 12, key: "HSK2-2.0", title: "HSK 2", description: null, level: 2, version: "2.0" },
          ]
        : [
            { id: 1, key: "HSK1", title: "HSK 1", description: null, level: 1, version: "3.0" },
            { id: 2, key: "HSK2", title: "HSK 2", description: null, level: 2, version: "3.0" },
            { id: 3, key: "HSK3", title: "HSK 3", description: null, level: 3, version: "3.0" },
          ]
    );
    getStats.mockImplementation(async (keys: string[]) =>
      (keys.length ? keys : Object.keys(STATS)).map((k) => k.replace("-2.0", "")).reduce(
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
      words: "all",
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

  it("only-new mode counts never-seen words and passes the choice", async () => {
    const onStart = renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 1" }));
    fireEvent.click(screen.getByRole("radio", { name: /nouveaux uniquement/i }));

    fireEvent.click(await screen.findByRole("button", { name: "MAX (130)" }));
    fireEvent.click(startButton());
    expect(onStart).toHaveBeenCalledWith(
      expect.objectContaining({ quizzes: ["HSK1"], count: 130, words: "new" })
    );
  });

  it("revision-only mode counts already-seen words (due + upcoming) and never new ones", async () => {
    const onStart = renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 1" }));
    const seen = screen.getByRole("radio", { name: /révision uniquement/i });
    expect(await screen.findByText("20 mots · 5 à réviser maintenant")).toBeInTheDocument();
    fireEvent.click(seen);
    expect(seen).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: /nouveaux uniquement/i })).toHaveAttribute("aria-checked", "false");

    fireEvent.click(await screen.findByRole("button", { name: "MAX (20)" }));
    fireEvent.click(startButton());
    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ count: 20, words: "seen" }));
  });

  it("blocks revision-only when nothing was seen yet", async () => {
    renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 2" }));
    fireEvent.click(screen.getByRole("radio", { name: /révision uniquement/i }));
    expect(await screen.findByText(/Tu n'as encore vu aucun mot de ces niveaux/)).toBeInTheDocument();
    expect(startButton()).toBeDisabled();
  });

  it("blocks the start when every word was already seen in only-new mode", async () => {
    STATS.HSK1 = { due: 10, new: 0, upcoming: 140 };
    renderSetup();
    fireEvent.click(await screen.findByRole("button", { name: "HSK 1" }));
    fireEvent.click(screen.getByRole("radio", { name: /nouveaux uniquement/i }));

    expect(await screen.findByText(/déjà vu tous les mots/)).toBeInTheDocument();
    expect(startButton()).toBeDisabled();
    STATS.HSK1 = { due: 5, new: 130, upcoming: 15 };
  });

  it("cannot start without a level", async () => {
    renderSetup();
    await screen.findByRole("button", { name: "HSK 1" });
    expect(startButton()).toBeDisabled();
  });

  it("switches between HSK 3.0 and HSK 2.0 and saves the choice", async () => {
    const onStart = renderSetup();
    const v2 = await screen.findByRole("radio", { name: "HSK 2.0" });
    expect(screen.getByRole("radio", { name: "HSK 3.0" })).toHaveAttribute("aria-checked", "true");
    await screen.findByRole("button", { name: "HSK 3" });
    fireEvent.click(screen.getByRole("button", { name: "HSK 1" }));

    fireEvent.click(v2);
    await waitFor(() => expect(putAccountSettings).toHaveBeenCalledWith({ hsk_version: "2.0" }));
    expect(await screen.findByRole("radio", { name: "HSK 2.0" })).toHaveAttribute("aria-checked", "true");
    await waitFor(() => expect(getQuizzes).toHaveBeenCalledWith("2.0"));
    await waitFor(() => expect(screen.queryByRole("button", { name: "HSK 3" })).toBeNull());
    expect(screen.getByText(/examens jusqu'au 7 novembre 2026/)).toBeInTheDocument();

    // The 3.0 selection does not leak into 2.0.
    expect(screen.getByRole("button", { name: "HSK 1" })).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(screen.getByRole("button", { name: "HSK 2" }));
    await waitFor(() => expect(getStats).toHaveBeenLastCalledWith(["HSK2-2.0"]));
    await waitFor(() => expect(startButton()).toBeEnabled());
    fireEvent.click(startButton());
    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ quizzes: ["HSK2-2.0"] }));
  });

  it("saves the pinyin lock on the account and greys it out in pinyin-typing mode", async () => {
    renderSetup();
    const lock = await screen.findByRole("switch", { name: /pinyin toujours affiché/i });
    expect(lock).toHaveAttribute("aria-checked", "false");
    fireEvent.click(lock);
    await waitFor(() => expect(putAccountSettings).toHaveBeenCalledWith({ pinyin_locked: true }));
    await waitFor(() => expect(lock).toHaveAttribute("aria-checked", "true"));

    fireEvent.click(screen.getByRole("button", { name: /saisie pinyin/i }));
    expect(lock).toBeDisabled();
    expect(lock).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText(/donnerait la réponse/)).toBeInTheDocument();
  });
});
