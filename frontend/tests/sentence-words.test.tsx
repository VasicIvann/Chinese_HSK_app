import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PracticePage } from "@/components/exercises/practice-page";
import { ExerciseRunner } from "@/components/exercises/runner";
import type { ExerciseSet } from "@/lib/api/exercises";

const checkSentence = vi.fn();
const getExerciseSet = vi.fn();
const getCatalog = vi.fn();
const postExerciseResult = vi.fn();

vi.mock("@/lib/api/exercises", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/exercises")>()),
  checkSentence: (...a: unknown[]) => checkSentence(...a),
  getExerciseSet: (...a: unknown[]) => getExerciseSet(...a),
  getCatalog: (...a: unknown[]) => getCatalog(...a),
  postExerciseResult: (...a: unknown[]) => postExerciseResult(...a),
}));
vi.mock("@/lib/api/endpoints", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/endpoints")>()),
  getAccountSettings: async () => ({ hsk_version: "3.0", pinyin_locked: false }),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }));

const W2 = {
  part: "W2",
  numbers: "66-70",
  type: "make_sentence",
  count: 5,
  pinyin: false,
  title: "Écris une phrase avec le mot donné",
  how: "Un mot imposé.",
};

function set(items: { id: string; word: string; pinyin: string; translation: string }[]): ExerciseSet {
  return {
    version: "3.0",
    level: 3,
    section: "writing",
    part: "W2",
    parts: [{ ...W2, word_source: "weak", word_pool: items.length, items: items.map((i) => ({ ...i, type: "make_sentence", level: 3, source: "weak" })) }],
  };
}

function wrap(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  checkSentence.mockReset();
  postExerciseResult.mockReset().mockResolvedValue({});
});

describe("imposed word from the learner's vocabulary", () => {
  it("shows pinyin and meaning on demand, sends the meaning, and shows Claude's model only when wrong", async () => {
    checkSentence
      .mockResolvedValueOnce({
        correct: false, uses_word: true, corrected: "他学习很认真。", pinyin: "tā xuéxí hěn rènzhēn.", translation: "Il étudie sérieusement.",
        explanation: "Il manque le verbe.", model: "我们要认真学习。", model_pinyin: "wǒmen yào rènzhēn xuéxí.", model_translation: "Nous devons étudier sérieusement.",
      })
      .mockResolvedValueOnce({
        correct: true, uses_word: true, corrected: "我很高兴。", pinyin: "", translation: "Je suis content.", explanation: "Parfait.",
        model: "", model_pinyin: "", model_translation: "",
      });
    wrap(
      <ExerciseRunner
        set={set([
          { id: "word-1", word: "认真", pinyin: "rènzhēn", translation: "sérieux, consciencieux" },
          { id: "word-2", word: "高兴", pinyin: "gāoxìng", translation: "content" },
        ])}
        onExit={vi.fn()}
      />
    );

    expect(screen.getByText("认真")).toBeInTheDocument();
    expect(screen.queryByText("rènzhēn")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Indice : pinyin et sens/ }));
    expect(screen.getByText("rènzhēn")).toBeInTheDocument();
    expect(screen.getByText("sérieux, consciencieux")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Ta phrase"), { target: { value: "他认真。" } });
    fireEvent.click(screen.getByRole("button", { name: /Faire corriger par Claude/ }));
    expect(await screen.findByText("Phrase modèle (Claude)")).toBeInTheDocument();
    expect(screen.getByText("我们要认真学习。")).toBeInTheDocument();
    expect(checkSentence).toHaveBeenCalledWith(3, "认真", "他认真。", "sérieux, consciencieux");
    fireEvent.click(screen.getByRole("button", { name: /question suivante/i }));

    fireEvent.change(screen.getByLabelText("Ta phrase"), { target: { value: "我很高兴。" } });
    fireEvent.click(screen.getByRole("button", { name: /Faire corriger par Claude/ }));
    expect(await screen.findByText("Parfait.")).toBeInTheDocument();
    expect(screen.queryByText(/Phrase modèle/)).not.toBeInTheDocument();
  });
});

describe("Écriture HSK page, part 2", () => {
  beforeEach(() => {
    localStorage.setItem("hsk.exercise-level", "3");
    localStorage.removeItem("hsk.sentence-words");
    getCatalog.mockReset().mockResolvedValue({
      version: "3.0",
      level: 3,
      section: "writing",
      parts: [{ ...W2, available: 40, word_counts: { seen: 40, weak: 0 }, attempts: 0, last: null, best: null }],
    });
    getExerciseSet.mockReset().mockResolvedValue(set([{ id: "word-1", word: "认真", pinyin: "rènzhēn", translation: "sérieux" }]));
  });

  it("picks the word source, explains an empty source and passes the choice", async () => {
    wrap(<PracticePage section="writing" />);
    const weak = await screen.findByRole("radio", { name: /Mots à revoir/ });
    expect(screen.getByRole("radio", { name: /Mots déjà vus/ })).toHaveAttribute("aria-checked", "true");
    expect(screen.queryByRole("button", { name: /Nouvelle série \(Claude\)/ })).not.toBeInTheDocument();

    fireEvent.click(weak);
    expect(screen.getByText(/Aucun mot « À revoir »/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /S'entraîner/ })).toBeDisabled();

    fireEvent.click(screen.getByRole("radio", { name: /Mots déjà vus/ }));
    fireEvent.click(screen.getByRole("button", { name: /S'entraîner/ }));
    await waitFor(() => expect(getExerciseSet).toHaveBeenCalledWith("writing", 3, "W2", "3.0", "seen"));
    expect(localStorage.getItem("hsk.sentence-words")).toBe("seen");
  });
});

describe("grammar structure items", () => {
  it("hint gives only the meaning; pattern and example appear in the correction when wrong", async () => {
    const checkStructure = vi.spyOn(await import("@/lib/api/exercises"), "checkStructure");
    checkStructure.mockResolvedValueOnce({
      correct: false, uses_word: true, corrected: "虽然下雨，但是我们去了公园。", pinyin: "", translation: "",
      explanation: "Il manque 但是 dans la deuxième partie.", model: "虽然很累，但是我很高兴。", model_pinyin: "", model_translation: "Bien que fatigué, je suis content.",
    });
    const structureSet: ExerciseSet = {
      version: "3.0",
      level: 3,
      section: "writing",
      part: "W2",
      parts: [
        {
          ...W2,
          word_source: "structures",
          word_pool: 61,
          items: [
            {
              id: "struct-suiran-danshi",
              type: "make_sentence",
              level: 2,
              kind: "structure",
              word: "虽然……，但是……",
              meaning: "bien que…, pourtant…",
              pattern: "虽然 + A，但是 / 可是 + B",
              example: { zh: "虽然今天很累，但是我很高兴。", fr: "Bien que fatigué, je suis content." },
              history: "new",
              source: "structures",
            },
          ],
        },
      ],
    };
    wrap(<ExerciseRunner set={structureSet} onExit={vi.fn()} />);

    expect(screen.getByText("Écris une phrase avec la structure :")).toBeInTheDocument();
    expect(screen.getByText("Jamais travaillée")).toBeInTheDocument();
    expect(screen.queryByText(/虽然 \+ A/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Indice : le sens" }));
    expect(screen.getByText("bien que…, pourtant…")).toBeInTheDocument();
    expect(screen.queryByText(/虽然 \+ A/)).not.toBeInTheDocument(); // the pattern stays hidden

    fireEvent.change(screen.getByLabelText("Ta phrase"), { target: { value: "虽然下雨，我们去了公园。" } });
    fireEvent.click(screen.getByRole("button", { name: /Faire corriger par Claude/ }));
    expect(await screen.findByText("La structure")).toBeInTheDocument();
    expect(screen.getByText("虽然 + A，但是 / 可是 + B")).toBeInTheDocument();
    expect(screen.getByText("Phrase modèle (Claude)")).toBeInTheDocument();
    expect(checkStructure).toHaveBeenCalledWith(3, "虽然……，但是……", "虽然下雨，我们去了公园。", "bien que…, pourtant…");
    expect(checkSentence).not.toHaveBeenCalled();
  });
});
