import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ClassifierQuiz } from "@/components/classifiers/classifier-quiz";
import { ClassifiersPage } from "@/components/classifiers/classifiers-page";
import type { ClassifierQuestion } from "@/lib/api/classifiers";

const getClassifierQuiz = vi.fn();
const generateClassifierSentences = vi.fn();

vi.mock("@/lib/api/classifiers", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/classifiers")>()),
  getClassifiers: async () => ({
    version: "3.0",
    level: 1,
    sentences: 38,
    classifiers: [
      {
        hanzi: "本",
        pinyin: "běn",
        kind: "nominal",
        level: 1,
        usage: "Les livres, cahiers, dictionnaires.",
        explanation: "本 compte ce qui est relié.",
        traps: "Une feuille : 张.",
        nouns: [{ zh: "书", fr: "livre", in_level: true }],
        examples: [{ zh: "这本书很好。", fr: "Ce livre est bien." }],
        sentence_count: 6,
      },
      {
        hanzi: "下",
        pinyin: "xià",
        kind: "verbal",
        level: 1,
        usage: "Une action brève.",
        explanation: "…",
        traps: "",
        nouns: [],
        examples: [{ zh: "请等一下。", fr: "Attendez." }],
        sentence_count: 5,
      },
    ],
  }),
  getClassifierQuiz: (...args: unknown[]) => getClassifierQuiz(...args),
  generateClassifierSentences: (...args: unknown[]) => generateClassifierSentences(...args),
}));
vi.mock("@/lib/api/endpoints", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/endpoints")>()),
  getAccountSettings: async () => ({ hsk_version: "3.0", pinyin_locked: false }),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const fill: ClassifierQuestion = {
  id: "本-01",
  mode: "fill",
  before: "我买了三",
  after: "书。",
  sentence: "我买了三本书。",
  options: ["张", "本", "件", "杯"],
  answer: 1,
  fr: "J'ai acheté trois livres.",
  classifier: "本",
  explain: "Les livres, cahiers, dictionnaires.",
  hint: "Les livres, cahiers, dictionnaires.",
  generated: false,
};
const usage: ClassifierQuestion = {
  id: "usage-辆-cl_to_usage",
  mode: "usage",
  kind: "cl_to_usage",
  classifier: "辆",
  prompt: "辆",
  pinyin: "liàng",
  options: ["Les livres", "Les véhicules à roues", "Les vêtements", "Les animaux"],
  option_hanzi: ["本", "辆", "件", "只"],
  answer: 1,
  explain: "辆 (liàng) : Les véhicules à roues.",
};

function wrap(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("ClassifierQuiz", () => {
  it("checks the answer, fills the blank, shows the translation and the score", () => {
    const onRestart = vi.fn();
    wrap(<ClassifierQuiz title="Test" questions={[fill, usage]} defaultPinyin={false} onExit={vi.fn()} onRestart={onRestart} />);

    expect(screen.getByLabelText("trou à compléter")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /张/ }));
    expect(screen.getByRole("status")).toHaveTextContent("Mauvaise réponse : c'était 本.");
    expect(screen.getByText("J'ai acheté trois livres.")).toBeInTheDocument();
    expect(screen.getByLabelText("本")).toBeInTheDocument(); // blank filled with the right answer
    fireEvent.click(screen.getByRole("button", { name: /question suivante/i }));

    // Usage question, answered with the keyboard (2 = B).
    expect(screen.getByText("À quoi sert ce classificateur ?")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "2" });
    expect(screen.getByRole("status")).toHaveTextContent("Bonne réponse !");
    fireEvent.keyDown(window, { key: "Enter" });

    expect(screen.getByText("Ton score")).toBeInTheDocument();
    expect(screen.getByText(/^1$/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /nouvelle série/i }));
    expect(onRestart).toHaveBeenCalled();
  });
});

describe("ClassifierQuiz, typed mode", () => {
  const second: ClassifierQuestion = {
    ...(fill as Extract<ClassifierQuestion, { mode: "fill" }>),
    id: "张-01",
    before: "请给我一",
    after: "纸。",
    sentence: "请给我一张纸。",
    options: ["本", "张", "条", "件"],
    answer: 1,
    classifier: "张",
    hint: "Les objets plats : papier, photo.",
  };

  it("checks the written character strictly, with an optional hint", () => {
    const onFinish = vi.fn();
    wrap(
      <ClassifierQuiz title="Écrire" questions={[fill, second]} typed defaultPinyin={false} onExit={vi.fn()} onRestart={vi.fn()} onFinish={onFinish} />
    );
    expect(screen.getByText(/Écris le classificateur manquant/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^A/ })).not.toBeInTheDocument(); // no options

    const input = screen.getByLabelText("Classificateur manquant");
    // Latin letters are refused without counting the question.
    fireEvent.change(input, { target: { value: "ben" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(screen.getByRole("alert")).toHaveTextContent("caractère chinois");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    fireEvent.change(input, { target: { value: "张" } });
    fireEvent.click(screen.getByRole("button", { name: "Valider" }));
    expect(screen.getByRole("status")).toHaveTextContent("tu as écrit « 张 », c'était 本.");
    fireEvent.click(screen.getByRole("button", { name: /question suivante/i }));

    fireEvent.click(screen.getByRole("button", { name: /Indice/ }));
    expect(screen.getByText("Les objets plats : papier, photo.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Classificateur manquant"), { target: { value: " 张 " } });
    fireEvent.keyDown(screen.getByLabelText("Classificateur manquant"), { key: "Enter" });
    expect(screen.getByRole("status")).toHaveTextContent("Bonne réponse !");
    fireEvent.click(screen.getByRole("button", { name: /voir mon score/i }));

    expect(screen.getByText(/tu as écrit/)).toHaveTextContent("(tu as écrit 张)");
    expect(screen.getByText(/avec indice/)).toBeInTheDocument();
    expect(onFinish).toHaveBeenCalledWith([
      { id: "本-01", correct: false },
      { id: "张-01", correct: true },
    ]);
  });
});

describe("ClassifiersPage", () => {
  beforeEach(() => {
    getClassifierQuiz.mockReset().mockResolvedValue({ mode: "fill", version: "3.0", level: 1, hanzi: "本", questions: [fill] });
    generateClassifierSentences.mockReset();
    localStorage.setItem("hsk.exercise-level", "1");
  });

  it("opens a fiche and practises that classifier", async () => {
    wrap(<ClassifiersPage />);
    fireEvent.click(await screen.findByRole("button", { name: /Les livres, cahiers/ }));
    expect(screen.getByText("一本书")).toBeInTheDocument();
    expect(screen.getByText(/yì běn shū · livre/)).toBeInTheDocument();
    expect(screen.getByText("Une feuille : 张.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /S'entraîner sur 本/ }));
    await waitFor(() => expect(getClassifierQuiz).toHaveBeenCalledWith("fill", 1, "3.0", "本"));
    expect(await screen.findByText(/Phrases à compléter · 本 · HSK 1/)).toBeInTheDocument();
  });

  it("filters verbal classifiers and starts the usage quiz", async () => {
    wrap(<ClassifiersPage />);
    await screen.findByText("Une action brève.");
    fireEvent.click(screen.getByRole("button", { name: "Verbaux" }));
    expect(screen.queryByText(/Les livres, cahiers/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Écrire le classificateur/ }));
    fireEvent.click(screen.getByRole("button", { name: /Commencer \(10 phrases\)/ }));
    await waitFor(() => expect(getClassifierQuiz).toHaveBeenCalledWith("fill", 1, "3.0", undefined));
    expect(await screen.findByLabelText("Classificateur manquant")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Quitter" }));

    fireEvent.click(await screen.findByRole("tab", { name: /Phrases à compléter/ }));
    fireEvent.click(screen.getByRole("button", { name: /Plus de phrases/ }));
    await waitFor(() => expect(generateClassifierSentences).toHaveBeenCalledWith(1, "3.0", undefined));
  });
});
