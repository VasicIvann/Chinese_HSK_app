"use client";

import { Eraser, Loader2, PenLine, Save, Trash2, Undo2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  drawStroke,
  exportDrawing,
  GRID_COLOR,
  hasInk,
  practiceCharacters,
  renderCell,
  type Point,
  type Stroke,
  type Tool,
} from "@/lib/handwriting";
import { cn } from "@/lib/utils";

type Props = {
  hanzi: string;
  saving?: boolean;
  /** Receives the PNG data URL; resolve to clear the pad, reject to keep it. */
  onSave: (image: string) => Promise<unknown>;
  onClose?: () => void;
};

/** 米字格 drawn in SVG behind the canvas (the canvas only holds ink). */
function GuideGrid() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-0 h-full w-full"
    >
      <rect x="0.5" y="0.5" width="99" height="99" fill="none" stroke={GRID_COLOR} strokeWidth="1" />
      <g stroke={GRID_COLOR} strokeWidth="0.6" strokeDasharray="3 2.5" vectorEffect="non-scaling-stroke">
        <line x1="50" y1="0" x2="50" y2="100" />
        <line x1="0" y1="50" x2="100" y2="50" />
        <line x1="0" y1="0" x2="100" y2="100" />
        <line x1="100" y1="0" x2="0" y2="100" />
      </g>
    </svg>
  );
}

/**
 * Square practice cells (one per character) where the user writes with a
 * stylus, finger or mouse. Pen, eraser, undo, clear, then save as one PNG.
 */
export function DrawingPad({ hanzi, saving = false, onSave, onClose }: Props) {
  const chars = practiceCharacters(hanzi);
  const cellCount = chars.length;

  const strokes = useRef<Stroke[]>([]);
  const canvases = useRef<(HTMLCanvasElement | null)[]>([]);
  const sizes = useRef<number[]>([]);
  const active = useRef<{ pointerId: number; stroke: Stroke; rect: DOMRect } | null>(null);
  // Once a stylus has been used, touches are treated as a resting palm.
  const penSeen = useRef(false);
  const [tool, setTool] = useState<Tool>("pen");
  // Mirror of what the buttons need, refreshed after each change to the strokes.
  const [summary, setSummary] = useState({ count: 0, ink: false });
  const bump = () => setSummary({ count: strokes.current.length, ink: hasInk(strokes.current) });

  const inkColor = (canvas: HTMLCanvasElement) => getComputedStyle(canvas).color || "#111";

  const redraw = useCallback((cell: number) => {
    const canvas = canvases.current[cell];
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const size = sizes.current[cell] ?? canvas.clientWidth;
    renderCell(ctx, strokes.current, cell, size, inkColor(canvas));
  }, []);

  // Keep each canvas backing store at device resolution and replay the ink.
  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((items) => {
      for (const item of items) {
        const canvas = item.target as HTMLCanvasElement;
        const cell = canvases.current.indexOf(canvas);
        if (cell < 0) continue;
        const size = canvas.clientWidth;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.round(size * dpr);
        canvas.height = Math.round(size * dpr);
        canvas.getContext("2d")?.setTransform(dpr, 0, 0, dpr, 0, 0);
        sizes.current[cell] = size;
        redraw(cell);
      }
    });
    canvases.current.forEach((c) => c && observer.observe(c));
    return () => observer.disconnect();
  }, [cellCount, redraw]);

  // Ink follows the theme (light/dark) on screen.
  useEffect(() => {
    const observer = new MutationObserver(() => canvases.current.forEach((_, i) => redraw(i)));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class", "data-theme"] });
    return () => observer.disconnect();
  }, [redraw]);

  const pointFrom = (e: { clientX: number; clientY: number }, rect: DOMRect): Point => [
    (e.clientX - rect.left) / rect.width,
    (e.clientY - rect.top) / rect.height,
  ];

  const onPointerDown = (cell: number) => (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (e.pointerType === "pen") penSeen.current = true;
    else if (e.pointerType === "touch" && penSeen.current) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    if (active.current) return; // one stroke at a time
    e.preventDefault();
    const canvas = e.currentTarget;
    canvas.setPointerCapture?.(e.pointerId);
    const rect = canvas.getBoundingClientRect();
    const stroke: Stroke = { cell, tool, points: [pointFrom(e, rect)] };
    strokes.current.push(stroke);
    active.current = { pointerId: e.pointerId, stroke, rect };
    const ctx = canvas.getContext("2d");
    if (ctx) drawStroke(ctx, stroke, sizes.current[cell] ?? rect.width, inkColor(canvas));
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const current = active.current;
    if (!current || current.pointerId !== e.pointerId) return;
    e.preventDefault();
    const native = e.nativeEvent;
    const events = typeof native.getCoalescedEvents === "function" ? native.getCoalescedEvents() : [];
    const from = current.stroke.points.length;
    for (const ev of events.length ? events : [native]) {
      current.stroke.points.push(pointFrom(ev, current.rect));
    }
    const canvas = e.currentTarget;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      drawStroke(ctx, current.stroke, sizes.current[current.stroke.cell] ?? current.rect.width, inkColor(canvas), from);
    }
  };

  const endStroke = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (active.current?.pointerId !== e.pointerId) return;
    active.current = null;
    bump();
  };

  const undo = () => {
    const last = strokes.current.pop();
    if (last) redraw(last.cell);
    bump();
  };

  const clear = () => {
    strokes.current = [];
    canvases.current.forEach((_, i) => redraw(i));
    bump();
  };

  const save = async () => {
    const image = exportDrawing(strokes.current, cellCount);
    try {
      await onSave(image);
      clear();
    } catch {
      // The caller shows the error; keep the drawing so it can be saved again.
    }
  };

  const canUndo = summary.count > 0;
  const canSave = summary.ink && !saving;

  return (
    <div className="flex w-full flex-col gap-3 rounded-lg border border-border bg-card p-3 sm:p-4">
      <div
        className="flex flex-wrap justify-center gap-2"
        style={{ WebkitUserSelect: "none", userSelect: "none", WebkitTouchCallout: "none" } as React.CSSProperties}
      >
        {chars.map((char, i) => (
          <div
            key={`${char}-${i}`}
            className="relative aspect-square overflow-hidden rounded-md bg-background"
            style={{ width: `min(240px, calc((100% - ${(cellCount - 1) * 0.5}rem) / ${cellCount}))`, minWidth: 120 }}
          >
            <GuideGrid />
            <canvas
              ref={(el) => {
                canvases.current[i] = el;
              }}
              aria-label={`Case d'écriture ${i + 1} sur ${cellCount}`}
              className={cn(
                "absolute inset-0 h-full w-full touch-none text-foreground",
                tool === "eraser" ? "cursor-cell" : "cursor-crosshair"
              )}
              onPointerDown={onPointerDown(i)}
              onPointerMove={onPointerMove}
              onPointerUp={endStroke}
              onPointerCancel={endStroke}
              onContextMenu={(e) => e.preventDefault()}
            />
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        <div className="inline-flex rounded-md border border-input p-0.5" role="group" aria-label="Outil">
          <Button
            type="button"
            size="sm"
            variant={tool === "pen" ? "secondary" : "ghost"}
            aria-pressed={tool === "pen"}
            onClick={() => setTool("pen")}
          >
            <PenLine className="h-4 w-4" />
            Stylo
          </Button>
          <Button
            type="button"
            size="sm"
            variant={tool === "eraser" ? "secondary" : "ghost"}
            aria-pressed={tool === "eraser"}
            onClick={() => setTool("eraser")}
          >
            <Eraser className="h-4 w-4" />
            Gomme
          </Button>
        </div>
        <Button type="button" size="sm" variant="ghost" onClick={undo} disabled={!canUndo}>
          <Undo2 className="h-4 w-4" />
          Annuler
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={clear} disabled={!canUndo}>
          <Trash2 className="h-4 w-4" />
          Effacer tout
        </Button>
        <Button type="button" size="sm" onClick={save} disabled={!canSave}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {saving ? "Enregistrement…" : "Enregistrer"}
        </Button>
        {onClose && (
          <Button type="button" size="sm" variant="ghost" onClick={onClose} aria-label="Fermer la zone de dessin">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
