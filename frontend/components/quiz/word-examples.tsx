"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { History, Loader2, Sparkles } from "lucide-react";
import { Fragment, useState, type ReactNode } from "react";

import { ListenButton } from "@/components/listen-button";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { getWordExamples, postGenerateExample } from "@/lib/api/endpoints";
import type { DueEntry, WordExampleItem } from "@/lib/api/types";

export const wordExamplesKey = (entryId: number) => ["word-examples", entryId] as const;

/** Wrap every occurrence of `word` in the sentence so it stands out. */
function HighlightedSentence({ sentence, word }: { sentence: string; word: string }) {
  if (!word || !sentence.includes(word)) return <>{sentence}</>;
  const parts = sentence.split(word);
  return (
    <>
      {parts.map((part, i) => (
        <Fragment key={i}>
          {part}
          {i < parts.length - 1 && <span className="text-primary">{word}</span>}
        </Fragment>
      ))}
    </>
  );
}

export function ExampleCard({ example, word }: { example: WordExampleItem; word: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 text-left">
      <div className="flex items-start justify-between gap-2">
        <p className="hanzi text-xl leading-relaxed">
          <HighlightedSentence sentence={example.sentence} word={word} />
        </p>
        <ListenButton text={example.sentence} rate={0.9} className="-mr-2 -mt-1 shrink-0" />
      </div>
      {example.pinyin && <p className="mt-1 text-sm text-muted-foreground">{example.pinyin}</p>}
      {example.translation && <p className="mt-1 text-sm italic">{example.translation}</p>}
      {(example.meaning_in_sentence || example.general_meaning || example.decomposition) && (
        <div className="mt-3 space-y-1.5 border-t border-border pt-3 text-sm">
          {example.meaning_in_sentence && (
            <p>
              <span className="font-medium">Dans cette phrase : </span>
              {example.meaning_in_sentence}
            </p>
          )}
          {example.general_meaning && (
            <p>
              <span className="font-medium">
                En général{example.hsk_level ? ` (HSK ${example.hsk_level})` : ""} :{" "}
              </span>
              {example.general_meaning}
            </p>
          )}
          {example.decomposition && (
            <p>
              <span className="font-medium">Décomposition : </span>
              {example.decomposition}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * "Générer un exemple" + "Voir les exemples précédents" for one quiz word.
 * Mount it with `key={entry.id}` so its local state resets on each new word.
 */
export function WordExamples({
  entry,
  actions,
  secondaryActions,
  children,
}: {
  entry: DueEntry;
  /** Extra buttons shown right after "Générer un exemple". */
  actions?: ReactNode;
  /** Extra buttons shown after "Voir les exemples précédents". */
  secondaryActions?: ReactNode;
  /** Extra panels shown under the buttons (e.g. the writing pad). */
  children?: ReactNode;
}) {
  const queryClient = useQueryClient();
  const [latestId, setLatestId] = useState<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const examplesQuery = useQuery({
    queryKey: wordExamplesKey(entry.id),
    queryFn: () => getWordExamples(entry.id),
  });

  const generate = useMutation({
    mutationFn: () => postGenerateExample(entry.id),
    // Each call costs an LLM request; never retry silently.
    retry: 0,
    onSuccess: ({ example }) => {
      queryClient.setQueryData<WordExampleItem[]>(wordExamplesKey(entry.id), (old) => [
        example,
        ...(old ?? []).filter((e) => e.id !== example.id),
      ]);
      setLatestId(example.id);
    },
  });

  const examples = examplesQuery.data ?? [];
  const latest = latestId !== null ? examples.find((e) => e.id === latestId) : undefined;
  const previous = examples.filter((e) => e.id !== latestId);

  const errorMessage =
    generate.error instanceof ApiError
      ? generate.error.detail || "La génération a échoué."
      : generate.error
        ? "La génération a échoué. Vérifie ta connexion."
        : null;

  return (
    <div className="flex w-full flex-col gap-3">
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
        >
          {generate.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {generate.isPending ? "Génération…" : "Générer un exemple"}
        </Button>
        {actions}
        {previous.length > 0 && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => setShowHistory((v) => !v)}
            aria-expanded={showHistory}
            className="text-muted-foreground"
          >
            <History className="h-4 w-4" />
            {showHistory
              ? "Masquer les exemples précédents"
              : `Voir les exemples précédents (${previous.length})`}
          </Button>
        )}
        {secondaryActions}
      </div>

      {errorMessage && (
        <p role="alert" className="text-center text-sm text-destructive">
          {errorMessage}
        </p>
      )}

      {children}

      {latest && <ExampleCard example={latest} word={entry.hanzi} />}

      {showHistory && previous.length > 0 && (
        <div className="flex flex-col gap-2">
          {previous.map((example) => (
            <ExampleCard key={example.id} example={example} word={entry.hanzi} />
          ))}
        </div>
      )}
    </div>
  );
}
