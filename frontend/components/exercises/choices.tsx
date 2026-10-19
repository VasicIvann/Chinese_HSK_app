"use client";

import { Check, ImageIcon, X } from "lucide-react";

import { ZhText } from "@/components/exercises/zh-text";
import { cn } from "@/lib/utils";

export const LETTERS = "ABCDEF";

type ChoiceState = { given: number | null; answer: number };

function stateClass(i: number, { given, answer }: ChoiceState) {
  if (given === null) return "border-input hover:border-primary/60 hover:bg-accent/50";
  if (i === answer) return "border-emerald-500 bg-emerald-500/10";
  if (i === given) return "border-destructive bg-destructive/10";
  return "border-input opacity-60";
}

function Mark({ i, state }: { i: number; state: ChoiceState }) {
  if (state.given === null) return null;
  if (i === state.answer) return <Check className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />;
  if (i === state.given) return <X className="h-4 w-4 shrink-0 text-destructive" />;
  return null;
}

/** Options shown as "pictures": the real paper's image, described in French. */
export function PictureChoices({
  options,
  state,
  onPick,
  disabledOptions = [],
}: {
  options: string[];
  state: ChoiceState;
  onPick: (i: number) => void;
  disabledOptions?: number[];
}) {
  return (
    <div className={cn("grid gap-2", options.length > 3 ? "sm:grid-cols-2 lg:grid-cols-3" : "sm:grid-cols-3")}>
      {options.map((text, i) => (
        <button
          key={i}
          type="button"
          disabled={state.given !== null || disabledOptions.includes(i)}
          onClick={() => onPick(i)}
          className={cn(
            "flex min-h-24 flex-col gap-2 rounded-lg border-2 p-3 text-left transition-colors disabled:cursor-default",
            stateClass(i, state),
            disabledOptions.includes(i) && state.given === null && "opacity-40"
          )}
        >
          <span className="flex items-center justify-between gap-2">
            <span className="text-sm font-semibold text-primary">{LETTERS[i]}</span>
            <Mark i={i} state={state} />
          </span>
          <span className="flex items-start gap-2 text-sm">
            <ImageIcon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
            <span className="italic">{text}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

/** Options in Chinese (words or short answers), pinyin above when the paper prints it. */
export function TextChoices({
  options,
  translations,
  state,
  onPick,
  showPinyin,
}: {
  options: string[];
  translations?: string[];
  state: ChoiceState;
  onPick: (i: number) => void;
  showPinyin: boolean;
}) {
  return (
    <div className={cn("grid gap-2", options.length > 3 ? "grid-cols-2 sm:grid-cols-3" : "sm:grid-cols-3")}>
      {options.map((text, i) => (
        <button
          key={i}
          type="button"
          disabled={state.given !== null}
          onClick={() => onPick(i)}
          className={cn(
            "flex items-center gap-3 rounded-lg border-2 px-4 py-3 text-left transition-colors disabled:cursor-default",
            stateClass(i, state)
          )}
        >
          <span className="text-sm font-semibold text-primary">{LETTERS[i]}</span>
          <span className="flex min-w-0 flex-1 flex-col">
            <ZhText text={text} showPinyin={showPinyin} className="text-xl" />
            {state.given !== null && translations?.[i] && (
              <span className="text-xs text-muted-foreground">{translations[i]}</span>
            )}
          </span>
          <Mark i={i} state={state} />
        </button>
      ))}
    </div>
  );
}

/** ✓ / ✗ buttons of the "true or false" parts. */
export function JudgeChoices({ state, onPick }: { state: { given: boolean | null; answer: boolean }; onPick: (v: boolean) => void }) {
  const cls = (v: boolean) => {
    if (state.given === null) return "border-input hover:border-primary/60 hover:bg-accent/50";
    if (v === state.answer) return "border-emerald-500 bg-emerald-500/10";
    if (v === state.given) return "border-destructive bg-destructive/10";
    return "border-input opacity-60";
  };
  return (
    <div className="grid grid-cols-2 gap-3">
      {[true, false].map((v) => (
        <button
          key={String(v)}
          type="button"
          disabled={state.given !== null}
          onClick={() => onPick(v)}
          className={cn("flex items-center justify-center gap-2 rounded-lg border-2 py-4 text-lg font-semibold", cls(v))}
          aria-label={v ? "Vrai" : "Faux"}
        >
          {v ? <Check className="h-6 w-6" /> : <X className="h-6 w-6" />}
          {v ? "Vrai" : "Faux"}
        </button>
      ))}
    </div>
  );
}
