"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { deleteWordDrawing } from "@/lib/api/endpoints";
import type { DrawingItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export const wordDrawingsKey = (entryId: number) => ["word-drawings", entryId] as const;
export const drawingGalleryKey = ["drawings-gallery"] as const;

/** Delete a drawing and drop it from every cached list. */
export function useDeleteDrawing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (drawing: DrawingItem) => deleteWordDrawing(drawing.id),
    onSuccess: (_, drawing) => {
      queryClient.setQueryData<DrawingItem[]>(wordDrawingsKey(drawing.entry_id), (old) =>
        old?.filter((d) => d.id !== drawing.id)
      );
      queryClient.invalidateQueries({ queryKey: drawingGalleryKey });
      toast.success("Dessin supprimé");
    },
    onError: (error) => {
      toast.error(error instanceof ApiError && error.detail ? error.detail : "Suppression impossible.");
    },
  });
}

function formatDate(iso: string) {
  // The API sends naive UTC timestamps.
  const date = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** A row of saved drawings (white "paper" thumbnails) with a delete button each. */
export function DrawingThumbs({
  drawings,
  hanzi,
  className,
}: {
  drawings: DrawingItem[];
  hanzi: string;
  className?: string;
}) {
  const remove = useDeleteDrawing();
  const [enlarged, setEnlarged] = useState<number | null>(null);

  return (
    <ul className={cn("flex flex-wrap justify-center gap-3", className)}>
      {drawings.map((drawing) => (
        <li key={drawing.id} className="flex max-w-full flex-col items-center gap-1">
          <button
            type="button"
            className="block max-w-full"
            aria-label={enlarged === drawing.id ? "Réduire le dessin" : "Agrandir le dessin"}
            aria-expanded={enlarged === drawing.id}
            onClick={() => setEnlarged((id) => (id === drawing.id ? null : drawing.id))}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- inline data URL */}
            <img
              src={drawing.image}
              alt={`Ton dessin de ${hanzi}`}
              width={drawing.width}
              height={drawing.height}
              className={cn(
                "w-auto max-w-full rounded-md border border-border bg-white",
                enlarged === drawing.id ? "h-auto max-h-72" : "h-24"
              )}
            />
          </button>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <span>{formatDate(drawing.created_at)}</span>
            <button
              type="button"
              className="rounded p-1 hover:bg-accent hover:text-destructive disabled:opacity-50"
              aria-label="Supprimer ce dessin"
              disabled={remove.isPending}
              onClick={() => {
                if (window.confirm("Supprimer ce dessin ?")) remove.mutate(drawing);
              }}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
