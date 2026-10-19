import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WordStudyTools } from "@/components/quiz/word-study-tools";
import type { DrawingItem, DueEntry } from "@/lib/api/types";
import { drawStroke, hasInk, practiceCharacters, type Stroke } from "@/lib/handwriting";

const getWordDrawings = vi.fn();
const postWordDrawing = vi.fn();

vi.mock("@/lib/api/endpoints", () => ({
  getWordExamples: () => Promise.resolve([]),
  postGenerateExample: vi.fn(),
  getWordDrawings: (id: number) => getWordDrawings(id),
  postWordDrawing: (id: number, image: string) => postWordDrawing(id, image),
  deleteWordDrawing: vi.fn(),
}));

// jsdom has no canvas: the export is checked on its own below.
vi.mock("@/lib/handwriting", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/handwriting")>()),
  exportDrawing: (_strokes: Stroke[], cells: number) => `data:image/png;base64,cells-${cells}`,
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const entry: DueEntry = {
  id: 9,
  quiz_id: 1,
  hanzi: "认真",
  pinyin: "rènzhēn",
  translation: "sérieux",
  alt_translations: null,
  tags: null,
};

function drawing(id: number): DrawingItem {
  return { id, entry_id: 9, image: "data:image/png;base64,AAAA", width: 512, height: 256, created_at: "2026-10-19T10:00:00" };
}

function renderTools() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <WordStudyTools entry={entry} />
    </QueryClientProvider>
  );
}

describe("practiceCharacters", () => {
  it("gives one cell per Chinese character and drops punctuation", () => {
    expect(practiceCharacters("认真")).toEqual(["认", "真"]);
    expect(practiceCharacters("虽然…但是…")).toEqual(["虽", "然", "但", "是"]);
    expect(practiceCharacters("面条儿")).toHaveLength(3);
    expect(practiceCharacters("…")).toEqual(["…"]);
  });
});

describe("strokes", () => {
  it("counts only pen strokes as ink", () => {
    expect(hasInk([])).toBe(false);
    expect(hasInk([{ cell: 0, tool: "eraser", points: [[0.5, 0.5]] }])).toBe(false);
    expect(hasInk([{ cell: 0, tool: "pen", points: [[0.5, 0.5]] }])).toBe(true);
  });

  it("draws a dot for a tap and erases with destination-out", () => {
    const calls: string[] = [];
    const ctx = {
      save: () => {},
      restore: () => {},
      beginPath: () => {},
      arc: (x: number, y: number) => calls.push(`arc ${x},${y}`),
      fill: () => calls.push("fill"),
      moveTo: (x: number, y: number) => calls.push(`move ${x},${y}`),
      lineTo: (x: number, y: number) => calls.push(`line ${x},${y}`),
      stroke: () => calls.push(`stroke ${ctx.globalCompositeOperation}`),
      globalCompositeOperation: "",
    } as unknown as CanvasRenderingContext2D & { globalCompositeOperation: string };

    drawStroke(ctx, { cell: 0, tool: "pen", points: [[0.5, 0.25]] }, 200, "#000");
    expect(calls).toEqual(["arc 100,50", "fill"]);

    calls.length = 0;
    const eraser: Stroke = { cell: 0, tool: "eraser", points: [[0, 0], [0.5, 0.5], [1, 1]] };
    drawStroke(ctx, eraser, 100, "#000", 2); // only the segments since point 2
    expect(calls).toEqual(["move 50,50", "line 100,100", "stroke destination-out"]);
  });
});

describe("WordStudyTools — writing practice", () => {
  beforeEach(() => {
    // jsdom logs "not implemented" for canvas; the pad copes with a null context.
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    getWordDrawings.mockReset();
    postWordDrawing.mockReset();
  });

  it("opens a pad with one square per character and saves the drawing", async () => {
    getWordDrawings.mockResolvedValue([]);
    postWordDrawing.mockResolvedValue(drawing(1));
    renderTools();

    fireEvent.click(await screen.findByRole("button", { name: /s'entraîner à écrire/i }));
    const cells = screen.getAllByLabelText(/case d'écriture/i);
    expect(cells).toHaveLength(2);

    const save = screen.getByRole("button", { name: /enregistrer/i });
    expect(save).toBeDisabled(); // nothing drawn yet

    fireEvent.pointerDown(cells[0], { pointerId: 1, clientX: 10, clientY: 10, button: 0 });
    fireEvent.pointerMove(cells[0], { pointerId: 1, clientX: 20, clientY: 30 });
    fireEvent.pointerUp(cells[0], { pointerId: 1 });
    expect(save).toBeEnabled();
    expect(screen.getByRole("button", { name: /annuler/i })).toBeEnabled();

    fireEvent.click(save);
    await waitFor(() => expect(postWordDrawing).toHaveBeenCalledWith(9, "data:image/png;base64,cells-2"));
    // The pad is cleared after a successful save, and the drawing is listed.
    await waitFor(() => expect(screen.getByRole("button", { name: /enregistrer/i })).toBeDisabled());
    expect(await screen.findByRole("button", { name: /voir mes dessins \(1\)/i })).toBeInTheDocument();
  });

  it("undo removes the last stroke", async () => {
    getWordDrawings.mockResolvedValue([]);
    renderTools();
    fireEvent.click(await screen.findByRole("button", { name: /s'entraîner à écrire/i }));
    const cell = screen.getAllByLabelText(/case d'écriture/i)[1];
    fireEvent.pointerDown(cell, { pointerId: 2, clientX: 5, clientY: 5, button: 0 });
    fireEvent.pointerUp(cell, { pointerId: 2 });
    fireEvent.click(screen.getByRole("button", { name: /annuler/i }));
    expect(screen.getByRole("button", { name: /enregistrer/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /annuler/i })).toBeDisabled();
  });

  it("an eraser stroke alone is not something to save", async () => {
    getWordDrawings.mockResolvedValue([]);
    renderTools();
    fireEvent.click(await screen.findByRole("button", { name: /s'entraîner à écrire/i }));
    fireEvent.click(screen.getByRole("button", { name: /gomme/i }));
    const cell = screen.getAllByLabelText(/case d'écriture/i)[0];
    fireEvent.pointerDown(cell, { pointerId: 3, clientX: 5, clientY: 5, button: 0 });
    fireEvent.pointerUp(cell, { pointerId: 3 });
    expect(screen.getByRole("button", { name: /enregistrer/i })).toBeDisabled();
  });

  it("shows the previous drawings of the word on demand", async () => {
    getWordDrawings.mockResolvedValue([drawing(1), drawing(2)]);
    renderTools();
    const toggle = await screen.findByRole("button", { name: /voir mes dessins \(2\)/i });
    expect(screen.queryAllByAltText(/ton dessin de 认真/i)).toHaveLength(0);
    fireEvent.click(toggle);
    expect(screen.getAllByAltText(/ton dessin de 认真/i)).toHaveLength(2);
  });
});
