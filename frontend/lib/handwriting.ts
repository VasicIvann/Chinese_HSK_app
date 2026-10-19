/**
 * Handwriting practice: stroke model and canvas rendering.
 *
 * Strokes are kept as vectors in coordinates normalised to their cell (0..1),
 * so the pad can be resized without losing anything and the saved image is
 * re-rendered cleanly at a fixed resolution.
 */

export type Point = [number, number];
export type Tool = "pen" | "eraser";
export type Stroke = { cell: number; tool: Tool; points: Point[] };

/** Line widths, as a fraction of the cell size. */
export const PEN_WIDTH = 0.034;
export const ERASER_WIDTH = 0.11;
export const MAX_CELLS = 8;
/** Pixel size of one cell in the saved PNG. */
export const EXPORT_CELL_PX = 256;

export const GRID_COLOR = "rgba(220, 38, 38, 0.38)";
export const INK_EXPORT = "#111111";
export const PAPER_EXPORT = "#ffffff";

const HAN = /\p{Script=Han}/u;

/** The characters to practise, one cell each (punctuation like "…" is dropped). */
export function practiceCharacters(hanzi: string): string[] {
  const chars = Array.from(hanzi).filter((c) => HAN.test(c));
  if (chars.length === 0) return [hanzi.trim() || "?"];
  return chars.slice(0, MAX_CELLS);
}

export function strokeWidth(tool: Tool, size: number): number {
  return (tool === "pen" ? PEN_WIDTH : ERASER_WIDTH) * size;
}

/**
 * Draw `stroke` on a context whose units are CSS pixels of a `size`-wide cell.
 * With `from > 0`, only the segments added since point `from` are drawn
 * (used while the pointer moves, so long strokes stay cheap).
 */
export function drawStroke(
  ctx: CanvasRenderingContext2D,
  stroke: Stroke,
  size: number,
  color: string,
  from = 0
): void {
  const { points } = stroke;
  if (points.length === 0) return;
  const width = strokeWidth(stroke.tool, size);
  ctx.save();
  ctx.globalCompositeOperation = stroke.tool === "eraser" ? "destination-out" : "source-over";
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  if (points.length === 1) {
    ctx.beginPath();
    ctx.arc(points[0][0] * size, points[0][1] * size, width / 2, 0, Math.PI * 2);
    ctx.fill();
  } else {
    const start = Math.max(0, from - 1);
    ctx.beginPath();
    ctx.moveTo(points[start][0] * size, points[start][1] * size);
    for (let i = start + 1; i < points.length; i++) {
      ctx.lineTo(points[i][0] * size, points[i][1] * size);
    }
    ctx.stroke();
  }
  ctx.restore();
}

/** Clear the cell and replay every stroke that belongs to it, in order. */
export function renderCell(
  ctx: CanvasRenderingContext2D,
  strokes: Stroke[],
  cell: number,
  size: number,
  color: string
): void {
  ctx.clearRect(0, 0, size, size);
  for (const stroke of strokes) {
    if (stroke.cell === cell) drawStroke(ctx, stroke, size, color);
  }
}

/** The 米字格 practice grid: frame, centre cross and diagonals (dashed). */
export function drawGuideGrid(ctx: CanvasRenderingContext2D, x: number, y: number, size: number): void {
  ctx.save();
  ctx.strokeStyle = GRID_COLOR;
  ctx.lineWidth = Math.max(1, size / 128);
  ctx.strokeRect(x + ctx.lineWidth / 2, y + ctx.lineWidth / 2, size - ctx.lineWidth, size - ctx.lineWidth);
  ctx.setLineDash([size / 32, size / 40]);
  ctx.beginPath();
  ctx.moveTo(x + size / 2, y);
  ctx.lineTo(x + size / 2, y + size);
  ctx.moveTo(x, y + size / 2);
  ctx.lineTo(x + size, y + size / 2);
  ctx.moveTo(x, y);
  ctx.lineTo(x + size, y + size);
  ctx.moveTo(x + size, y);
  ctx.lineTo(x, y + size);
  ctx.stroke();
  ctx.restore();
}

/** True when there is at least one pen stroke (an eraser-only pad is empty). */
export function hasInk(strokes: Stroke[]): boolean {
  return strokes.some((s) => s.tool === "pen");
}

/**
 * Render the pad as one PNG: the cells side by side, dark ink on white paper
 * with the practice grid. Each cell is drawn on its own layer first so the
 * eraser only removes ink, never the paper or the grid.
 */
export function exportDrawing(
  strokes: Stroke[],
  cellCount: number,
  cellPx = EXPORT_CELL_PX,
  createCanvas: () => HTMLCanvasElement = () => document.createElement("canvas")
): string {
  const sheet = createCanvas();
  sheet.width = cellPx * cellCount;
  sheet.height = cellPx;
  const ctx = sheet.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D indisponible.");
  ctx.fillStyle = PAPER_EXPORT;
  ctx.fillRect(0, 0, sheet.width, sheet.height);

  const layer = createCanvas();
  layer.width = cellPx;
  layer.height = cellPx;
  const layerCtx = layer.getContext("2d");
  if (!layerCtx) throw new Error("Canvas 2D indisponible.");

  for (let cell = 0; cell < cellCount; cell++) {
    drawGuideGrid(ctx, cell * cellPx, 0, cellPx);
    renderCell(layerCtx, strokes, cell, cellPx, INK_EXPORT);
    ctx.drawImage(layer, cell * cellPx, 0);
  }
  return sheet.toDataURL("image/png");
}
