import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ExerciseRunner, flattenSet } from "@/components/exercises/runner";
import type { ExerciseSet } from "@/lib/api/exercises";

const postExerciseResult = vi.fn();
const checkSentence = vi.fn();

vi.mock("@/lib/api/exercises", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/exercises")>()),
  postExerciseResult: (body: unknown) => postExerciseResult(body),
  checkSentence: (...args: unknown[]) => checkSentence(...args),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const part = (p: string, numbers: string, type: string, count: number) => ({
  part: p,
  numbers,
  type,
  count,
  pinyin: false,
  title: `Titre ${p}`,
  how: "",
});

const set: ExerciseSet = {
  version: "3.0",
  level: 2,
  section: "listening",
  part: "all",
  parts: [
    {
      ...part("L1", "1-5", "pic_choice", 1),
      items: [
        {
          id: "2-pic_choice-001",
          type: "pic_choice",
          level: 2,
          audio: [{ s: "n", t: "外面下雪了。" }],
          fr: "Il neige dehors.",
          options: ["Une rue sous la pluie", "Une rue couverte de neige", "Un jardin ensoleillé"],
          answer: 1,
        },
      ],
    },
    {
      ...part("L2", "6-15", "pic_match", 2),
      items: [
        {
          id: "2-pic_match-001",
          type: "pic_match",
          level: 2,
          options: ["Image A", "Image B", "Image C", "Image D", "Image E", "Image F"],
          items: [
            { audio: [{ s: "m", t: "你好！" }], fr: "Bonjour !", answer: 3 },
            { audio: [{ s: "f", t: "再见！" }], fr: "Au revoir !", answer: 0 },
          ],
        },
      ],
    },
  ],
};

function renderRunner() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ExerciseRunner set={set} onExit={vi.fn()} />
    </QueryClientProvider>
  );
}

describe("flattenSet", () => {
  it("numbers the questions like the paper and splits the matching series", () => {
    const qs = flattenSet(set);
    expect(qs.map((q) => [q.key, q.number])).toEqual([
      ["2-pic_choice-001", 1],
      ["2-pic_match-001#0", 6],
      ["2-pic_match-001#1", 7],
    ]);
  });
});

describe("ExerciseRunner", () => {
  beforeEach(() => {
    postExerciseResult.mockReset().mockResolvedValue({ id: 1, score: 1, total: 1 });
  });

  it("checks each answer, shows the transcript, then saves one result per part", async () => {
    renderRunner();

    // Q1: picture options; pick the wrong one.
    fireEvent.click(screen.getByRole("button", { name: /Une rue sous la pluie/ }));
    expect(screen.getByRole("status")).toHaveTextContent("Mauvaise réponse");
    expect(screen.getByText("Il neige dehors.")).toBeInTheDocument(); // transcript
    fireEvent.click(screen.getByRole("button", { name: /question suivante/i }));

    // Q6 and Q7: same six pictures.
    fireEvent.click(screen.getByRole("button", { name: /Image D/ }));
    expect(screen.getByRole("status")).toHaveTextContent("Bonne réponse");
    fireEvent.click(screen.getByRole("button", { name: /question suivante/i }));
    fireEvent.click(screen.getByRole("button", { name: /Image A/ }));
    fireEvent.click(screen.getByRole("button", { name: /voir mon score/i }));

    expect(await screen.findByText("Ton score")).toBeInTheDocument();
    await waitFor(() => expect(postExerciseResult).toHaveBeenCalledTimes(2));
    expect(postExerciseResult).toHaveBeenCalledWith({
      section: "listening",
      version: "3.0",
      level: 2,
      part: "L1",
      answers: [{ id: "2-pic_choice-001", correct: false }],
    });
    expect(postExerciseResult).toHaveBeenCalledWith({
      section: "listening",
      version: "3.0",
      level: 2,
      part: "L2",
      answers: [
        { id: "2-pic_match-001#0", correct: true },
        { id: "2-pic_match-001#1", correct: true },
      ],
    });
  });
});

describe("writing questions", () => {
  const writingSet = (item: ExerciseSet["parts"][number]["items"][number], type: string): ExerciseSet => ({
    version: "2.0",
    level: 3,
    section: "writing",
    part: "W1",
    parts: [{ ...part("W1", "71-75", type, 1), items: [item] }],
  });

  function renderWriting(s: ExerciseSet) {
    const client = new QueryClient();
    return render(
      <QueryClientProvider client={client}>
        <ExerciseRunner set={s} onExit={vi.fn()} />
      </QueryClientProvider>
    );
  }

  it("char from pinyin: typed character is compared to the answer", () => {
    renderWriting(
      writingSet(
        { id: "3-char_pinyin-001", type: "char_pinyin", level: 3, before: "我（", pinyin: "jué", after: "得很好。", answer: "觉", fr: "x" },
        "char_pinyin"
      )
    );
    fireEvent.change(screen.getByLabelText("Caractère manquant"), { target: { value: "觉" } });
    fireEvent.click(screen.getByRole("button", { name: "Valider" }));
    expect(screen.getByRole("status")).toHaveTextContent("Bonne réponse");
  });

  it("reorder: tapping the words builds the sentence", () => {
    renderWriting(
      writingSet(
        { id: "3-reorder-002", type: "reorder", level: 3, words: ["把", "关上", "门", "请"], answers: ["请把门关上。"], fr: "x" },
        "reorder"
      )
    );
    for (const w of ["请", "把", "门", "关上"]) fireEvent.click(screen.getByRole("button", { name: w }));
    fireEvent.click(screen.getByRole("button", { name: "Valider" }));
    expect(screen.getByRole("status")).toHaveTextContent("Bonne réponse");
  });
});

describe("toPinyin", () => {
  it("reads 儿 as erhua except in 儿子 / 女儿", async () => {
    const { toPinyin } = await import("@/components/exercises/zh-text");
    expect(toPinyin("这儿")).toBe("zhèr");
    expect(toPinyin("一点儿")).toBe("yì diǎnr");
    expect(toPinyin("我女儿")).toBe("wǒ nǚ ér");
    expect(toPinyin("不对")).toBe("bú duì");
  });
});
