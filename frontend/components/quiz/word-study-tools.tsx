"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Images, PenLine } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { WordExamples } from "@/components/quiz/word-examples";
import { Button } from "@/components/ui/button";
import { DrawingPad } from "@/components/writing/drawing-pad";
import { DrawingThumbs, drawingGalleryKey, wordDrawingsKey } from "@/components/writing/drawing-thumbs";
import { ApiError } from "@/lib/api/client";
import { getWordDrawings, postWordDrawing } from "@/lib/api/endpoints";
import type { DrawingItem, DueEntry } from "@/lib/api/types";

/**
 * Everything under a quiz card: example sentences plus handwriting practice
 * ("S'entraîner à écrire" / "Voir mes dessins"). Mount with `key={entry.id}`.
 */
export function WordStudyTools({ entry }: { entry: DueEntry }) {
  const queryClient = useQueryClient();
  const [padOpen, setPadOpen] = useState(false);
  const [showDrawings, setShowDrawings] = useState(false);

  const drawingsQuery = useQuery({
    queryKey: wordDrawingsKey(entry.id),
    queryFn: () => getWordDrawings(entry.id),
  });
  const drawings = drawingsQuery.data ?? [];

  const save = useMutation({
    mutationFn: (image: string) => postWordDrawing(entry.id, image),
    retry: 1,
    onSuccess: (drawing) => {
      queryClient.setQueryData<DrawingItem[]>(wordDrawingsKey(entry.id), (old) => [drawing, ...(old ?? [])]);
      queryClient.invalidateQueries({ queryKey: drawingGalleryKey });
      toast.success("Dessin enregistré");
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError && error.detail ? error.detail : "Enregistrement impossible. Vérifie ta connexion."
      );
    },
  });

  return (
    <WordExamples
      entry={entry}
      actions={
        <Button
          type="button"
          variant={padOpen ? "secondary" : "outline"}
          onClick={() => setPadOpen((v) => !v)}
          aria-expanded={padOpen}
        >
          <PenLine className="h-4 w-4" />
          S&apos;entraîner à écrire
        </Button>
      }
      secondaryActions={
        drawings.length > 0 && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => setShowDrawings((v) => !v)}
            aria-expanded={showDrawings}
            className="text-muted-foreground"
          >
            <Images className="h-4 w-4" />
            {showDrawings ? "Masquer mes dessins" : `Voir mes dessins (${drawings.length})`}
          </Button>
        )
      }
    >
      {padOpen && (
        <DrawingPad
          hanzi={entry.hanzi}
          saving={save.isPending}
          onSave={(image) => save.mutateAsync(image)}
          onClose={() => setPadOpen(false)}
        />
      )}
      {showDrawings && drawings.length > 0 && <DrawingThumbs drawings={drawings} hanzi={entry.hanzi} />}
    </WordExamples>
  );
}
