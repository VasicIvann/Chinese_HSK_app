import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ToneSession } from "@/components/tones/tone-session";
import { toToneWord, type ToneWord } from "@/lib/tones";

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const word = (id: number, hanzi: string, pinyin: string, translation: string) => toToneWord({ id, hanzi, pinyin, translation }) as ToneWord;
const xuexi = word(1, "学习", "xuéxí", "étudier");
const hao = word(2, "好", "hǎo", "bien");
const nihao = word(3, "你好", "nǐhǎo", "bonjour");

describe("Trouve le ton", () => {
  it("picks a tone per syllable, shows the toneless pinyin, re-asks a missed word and reports first tries", () => {
    const onFinish = vi.fn();
    render(<ToneSession mode="read" words={[xuexi, hao]} title="Trouve le ton" onExit={vi.fn()} onRestart={vi.fn()} onFinish={onFinish} />);

    expect(screen.getByText("学")).toBeInTheDocument();
    expect(screen.queryByText("xue")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Afficher le pinyin/ }));
    expect(screen.getByRole("button", { name: "Syllabe 1" })).toHaveTextContent("xue");
    expect(screen.getByRole("button", { name: "Syllabe 2" })).toHaveTextContent("xi");
    // The tone buttons show the active syllable with each tone.
    expect(screen.getByRole("button", { name: "3e ton" })).toHaveTextContent("xuě");

    // 学 = 2 (right), 习 = 4 (wrong): checked automatically once both are filled.
    fireEvent.click(screen.getByRole("button", { name: "2e ton" }));
    fireEvent.keyDown(window, { key: "4" });
    expect(screen.getByRole("status")).toHaveTextContent("Pas tout à fait.");
    expect(screen.getByRole("status")).toHaveTextContent("xué xí");
    expect(screen.getByText("tu as dit : 4e ton")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mot suivant" }));

    // 好: 3rd tone, with the keyboard; then 学习 comes back.
    fireEvent.keyDown(window, { key: "3" });
    expect(screen.getByRole("status")).toHaveTextContent("Bonne réponse !");
    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByText(/à revoir/)).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "2" });
    fireEvent.keyDown(window, { key: "2" });
    fireEvent.click(screen.getByRole("button", { name: "Voir mon score" }));

    expect(screen.getByText("Ton score (premier essai)")).toBeInTheDocument();
    expect(screen.getByText(/réussi au 2e essai/)).toBeInTheDocument();
    expect(onFinish).toHaveBeenCalledWith([
      { id: "1", correct: false },
      { id: "2", correct: true },
    ]);
  });

  it("explains a 3rd + 3rd tone change", () => {
    render(<ToneSession mode="read" words={[nihao]} title="t" onExit={vi.fn()} onRestart={vi.fn()} />);
    fireEvent.keyDown(window, { key: "3" });
    fireEvent.keyDown(window, { key: "3" });
    expect(screen.getByRole("status")).toHaveTextContent("Bonne réponse !");
    expect(screen.getByRole("status")).toHaveTextContent("on entend « ní hǎo »");
  });
});

describe("Dictée", () => {
  it("checks letters and tone of each syllable", () => {
    const onFinish = vi.fn();
    render(<ToneSession mode="listen" words={[xuexi]} title="Dictée" onExit={vi.fn()} onRestart={vi.fn()} onFinish={onFinish} />);
    expect(screen.queryByText("学")).not.toBeInTheDocument(); // the word is hidden

    const validate = screen.getByRole("button", { name: "Valider" });
    expect(validate).toBeDisabled();
    // "xue2" gives the tone; second syllable typed with the wrong letters.
    fireEvent.change(screen.getByLabelText("Pinyin de la syllabe 1"), { target: { value: "xue2" } });
    expect(screen.getByRole("button", { name: "2e ton pour la syllabe 1" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.change(screen.getByLabelText("Pinyin de la syllabe 2"), { target: { value: "shi" } });
    fireEvent.click(screen.getByRole("button", { name: "2e ton pour la syllabe 2" }));
    fireEvent.click(validate);

    expect(screen.getByRole("status")).toHaveTextContent("Pas tout à fait.");
    expect(screen.getByText(/lettres : « shi » au lieu de « xi »/)).toBeInTheDocument();
    expect(screen.getAllByText("学").length).toBeGreaterThan(0); // revealed after checking
  });
});
