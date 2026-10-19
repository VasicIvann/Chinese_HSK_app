"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Loader2, PenLine } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DrawingThumbs, drawingGalleryKey, wordDrawingsKey } from "@/components/writing/drawing-thumbs";
import { getDrawingGallery, getWordDrawings } from "@/lib/api/endpoints";
import type { DrawingWordGroup } from "@/lib/api/types";

const PAGE_SIZE = 12;

function WordRow({ word }: { word: DrawingWordGroup }) {
  const [expanded, setExpanded] = useState(false);
  const hasMore = word.count > word.drawings.length;
  const allQuery = useQuery({
    queryKey: wordDrawingsKey(word.entry_id),
    queryFn: () => getWordDrawings(word.entry_id),
    enabled: expanded,
  });
  const drawings = expanded && allQuery.data ? allQuery.data : word.drawings;

  return (
    <li className="flex flex-col gap-3 border-t border-border pt-4 first:border-t-0 first:pt-0 sm:flex-row sm:items-start">
      <div className="flex shrink-0 items-baseline gap-2 sm:w-40 sm:flex-col sm:gap-0.5">
        <span className="hanzi text-3xl font-semibold">{word.hanzi}</span>
        <span className="text-sm">{word.pinyin}</span>
        <span className="truncate text-xs text-muted-foreground">
          {word.translation}
          {word.hsk_level ? ` · HSK ${word.hsk_level}` : ""}
        </span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
        <DrawingThumbs drawings={drawings} hanzi={word.hanzi} className="justify-start" />
        {hasMore && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-muted-foreground"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
          >
            {expanded && allQuery.isFetching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
            {expanded ? "Afficher moins" : `Voir les ${word.count} dessins`}
          </Button>
        )}
      </div>
    </li>
  );
}

/** "Mes dessins" on the account page: handwriting practice grouped by word. */
export function DrawingsGallery() {
  const query = useInfiniteQuery({
    queryKey: drawingGalleryKey,
    queryFn: ({ pageParam }) => getDrawingGallery(pageParam, PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => (last.has_more ? pages.length * PAGE_SIZE : undefined),
  });

  const first = query.data?.pages[0];
  const words = query.data?.pages.flatMap((p) => p.words) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PenLine className="h-5 w-5 text-primary" />
          Mes dessins
        </CardTitle>
        <CardDescription>
          {first && first.total_drawings > 0
            ? `${first.total_drawings} dessin${first.total_drawings > 1 ? "s" : ""} sur ${first.total_words} mot${first.total_words > 1 ? "s" : ""}, du plus récent au plus ancien.`
            : "Tes entraînements d'écriture, regroupés par mot."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <Skeleton className="h-28 w-full" />
        ) : query.isError ? (
          <p className="text-sm text-muted-foreground">Impossible de charger tes dessins.</p>
        ) : words.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Aucun dessin pour l&apos;instant. Pendant un quiz, clique sur « S&apos;entraîner à écrire », écris le mot
            puis « Enregistrer ».
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            <ul className="flex flex-col gap-4">
              {words.map((word) => (
                <WordRow key={word.entry_id} word={word} />
              ))}
            </ul>
            {query.hasNextPage && (
              <Button
                type="button"
                variant="outline"
                className="self-center"
                onClick={() => query.fetchNextPage()}
                disabled={query.isFetchingNextPage}
              >
                {query.isFetchingNextPage && <Loader2 className="h-4 w-4 animate-spin" />}
                Charger plus de mots
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
