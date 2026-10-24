"use client";

import { Check, Lightbulb, RotateCcw, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { LETTERS } from "@/components/exercises/choices";
import { ZhText } from "@/components/exercises/zh-text";
import { ListenButton } from "@/components/listen-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { ClassifierQuestion, FillQuestion, UsageQuestion } from "@/lib/api/classifiers";
import { cn } from "@/lib/utils";

type Props = {
  title: string;
  questions: ClassifierQuestion[];
  defaultPinyin: boolean;
  onExit: () => void;
  onRestart: () => void;
  restarting?: boolean;
  /** Called once, when the last question is answered (saved for the stats). */
  onFinish?: (answers: { id: string; correct: boolean }[]) => void;
  /** Fill-in sentences without options: the classifier is typed in Chinese. */
  typed?: boolean;
};

const HANZI_ONLY = /^[\u3400-\u9fff\uf900-\ufaff]+$/;

/** Runs a set of classifier questions: one at a time, checked on the spot, score at the end. */
export function ClassifierQuiz({ title, questions, defaultPinyin, onExit, onRestart, restarting, onFinish, typed = false }: Props) {
  const [index, setIndex] = useState(0);
  const [given, setGiven] = useState<Record<number, number>>({});
  const [showPinyin, setShowPinyin] = useState(defaultPinyin);
  // Typed mode: what was written for each question, and whether the hint was opened.
  const [written, setWritten] = useState<Record<number, string>>({});
  const [hinted, setHinted] = useState<Record<number, boolean>>({});
  const done = index >= questions.length;
  const current = questions[index];
  const picked = given[index];
  const score = questions.filter((q, i) => given[i] === q.answer).length;
  const reported = useRef(false);

  useEffect(() => {
    if (!done || reported.current || questions.length === 0) return;
    reported.current = true;
    onFinish?.(questions.map((q, i) => ({ id: q.id, correct: given[i] === q.answer })));
  }, [done, questions, given, onFinish]);

  const pick = useCallback(
    (i: number) => {
      if (done || picked !== undefined) return;
      setGiven((g) => ({ ...g, [index]: i }));
    },
    [done, picked, index]
  );
  const next = useCallback(() => setIndex((i) => i + 1), []);
  const write = (text: string) => {
    if (done || picked !== undefined) return;
    setWritten((w) => ({ ...w, [index]: text }));
    // Strict: only the expected character is right (-1 = wrong, no option to point at).
    setGiven((g) => ({ ...g, [index]: text === current.classifier ? current.answer : -1 }));
  };
  const typing = typed && current?.mode === "fill";

  // Keyboard: 1-4 / A-D to answer, Enter or → for the next question.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Inputs handle their own keys; a focused button already reacts to Enter.
      if (done || e.target instanceof HTMLInputElement || e.target instanceof HTMLButtonElement) return;
      const n = "1234".indexOf(e.key) >= 0 ? "1234".indexOf(e.key) : "abcd".indexOf(e.key.toLowerCase());
      if (picked === undefined && n >= 0 && n < (current?.options.length ?? 0) && !typing) pick(n);
      else if (picked !== undefined && (e.key === "Enter" || e.key === "ArrowRight")) next();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [done, picked, current, pick, next, typing]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium">
          {title}
          {!done && <span className="text-muted-foreground"> · {index + 1} / {questions.length}</span>}
        </p>
        <div className="flex items-center gap-2">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" className="h-4 w-4" checked={showPinyin} onChange={(e) => setShowPinyin(e.target.checked)} />
            Pinyin
          </label>
          <Button variant="ghost" size="sm" onClick={onExit}>
            Quitter
          </Button>
        </div>
      </div>
      {!done && (
        <div className="h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden>
          <div className="h-full bg-primary transition-all" style={{ width: `${(index / questions.length) * 100}%` }} />
        </div>
      )}

      {done ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-8 text-center">
            <p className="text-sm text-muted-foreground">Ton score</p>
            <p className="text-5xl font-semibold">
              {score}
              <span className="text-2xl text-muted-foreground"> / {questions.length}</span>
            </p>
            <ul className="flex w-full max-w-md flex-col gap-1 text-left text-sm">
              {questions.map((q, i) => (
                <li key={i} className={cn("flex items-start gap-2", given[i] === q.answer ? "text-muted-foreground" : "text-destructive")}>
                  {given[i] === q.answer ? <Check className="mt-0.5 h-4 w-4 shrink-0" /> : <X className="mt-0.5 h-4 w-4 shrink-0" />}
                  <span>
                    <span className="hanzi font-medium text-foreground">{q.classifier}</span> · {summary(q)}
                    {typed && given[i] !== q.answer && written[i] && (
                      <span className="text-muted-foreground"> (tu as écrit <span className="hanzi">{written[i]}</span>)</span>
                    )}
                    {hinted[i] && <span className="text-muted-foreground"> · avec indice</span>}
                  </span>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap justify-center gap-2">
              <Button onClick={onRestart} disabled={restarting}>
                <RotateCcw className="h-4 w-4" />
                Nouvelle série
              </Button>
              <Button variant="outline" onClick={onExit}>
                Retour
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col gap-5 pt-6">
            {current.mode === "fill" ? (
              <FillPrompt q={current} picked={picked} showPinyin={showPinyin} typed={typing} written={written[index]} />
            ) : (
              <UsagePrompt q={current} showPinyin={showPinyin} />
            )}
            {typing && current.mode === "fill" ? (
              picked === undefined && (
                <TypedAnswer
                  key={index}
                  q={current}
                  onSubmit={write}
                  hintShown={!!hinted[index]}
                  onHint={() => setHinted((h) => ({ ...h, [index]: true }))}
                />
              )
            ) : (
              <Options q={current} picked={picked} showPinyin={showPinyin} onPick={pick} />
            )}
            {picked !== undefined && (
              <div className="flex flex-col gap-3">
                <Feedback q={current} picked={picked} showPinyin={showPinyin} written={typing ? written[index] : undefined} />
                <Button onClick={next} autoFocus>
                  {index + 1 === questions.length ? "Voir mon score" : "Question suivante"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function summary(q: ClassifierQuestion): string {
  if (q.mode === "fill") return q.sentence;
  if (q.kind === "noun_to_cl") return `一${q.classifier}${q.prompt}`;
  return q.kind === "cl_to_usage" ? q.options[q.answer] : q.prompt;
}

function FillPrompt({
  q,
  picked,
  showPinyin,
  typed,
  written,
}: {
  q: FillQuestion;
  picked: number | undefined;
  showPinyin: boolean;
  typed: boolean;
  written?: string;
}) {
  const filled = picked !== undefined;
  const wrongWritten = typed && filled && picked !== q.answer ? written : undefined;
  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm text-muted-foreground">
        {typed ? "Écris le classificateur manquant (en caractère chinois)." : "Choisis le bon classificateur."}
      </p>
      <p className="text-2xl sm:text-3xl">
        <ZhText text={q.before} showPinyin={showPinyin} />
        <span
          className={cn(
            "hanzi mx-1 inline-flex min-w-[2.2em] justify-center rounded-md border-2 border-dashed px-1 align-middle",
            !filled && "border-primary/60 text-transparent",
            filled && "border-solid border-emerald-500 bg-emerald-500/10"
          )}
          aria-label={filled ? q.classifier : "trou à compléter"}
        >
          {wrongWritten && <span className="hanzi mr-1 text-destructive line-through decoration-2">{wrongWritten}</span>}
          {filled ? <ZhText text={q.classifier} showPinyin={showPinyin} /> : "　"}
        </span>
        <ZhText text={q.after} showPinyin={showPinyin} />
      </p>
    </div>
  );
}

function UsagePrompt({ q, showPinyin }: { q: UsageQuestion; showPinyin: boolean }) {
  if (q.kind === "cl_to_usage") {
    return (
      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-sm text-muted-foreground">À quoi sert ce classificateur ?</p>
        <p className="hanzi text-6xl">{q.prompt}</p>
        {showPinyin && <p className="text-lg text-muted-foreground">{q.pinyin}</p>}
      </div>
    );
  }
  if (q.kind === "noun_to_cl") {
    return (
      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-sm text-muted-foreground">Quel classificateur va avec ce nom ?</p>
        <p className="text-4xl">
          <span className="hanzi">一</span>
          <span className="hanzi mx-1 inline-block min-w-[1.6em] rounded-md border-2 border-dashed border-primary/60 align-middle text-transparent">

          </span>
          <ZhText text={q.prompt} showPinyin={showPinyin} />
        </p>
        {q.prompt_fr && <p className="text-sm italic text-muted-foreground">{q.prompt_fr}</p>}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm text-muted-foreground">Quel classificateur utilise-t-on pour…</p>
      <p className="text-lg font-medium">{q.prompt}</p>
    </div>
  );
}

function optionClass(i: number, picked: number | undefined, answer: number) {
  if (picked === undefined) return "border-input hover:border-primary/60 hover:bg-accent/50";
  if (i === answer) return "border-emerald-500 bg-emerald-500/10";
  if (i === picked) return "border-destructive bg-destructive/10";
  return "border-input opacity-60";
}

function Options({
  q,
  picked,
  showPinyin,
  onPick,
}: {
  q: ClassifierQuestion;
  picked: number | undefined;
  showPinyin: boolean;
  onPick: (i: number) => void;
}) {
  const french = q.mode === "usage" && q.kind === "cl_to_usage";
  return (
    <div className={cn("grid gap-2", french ? "grid-cols-1" : "grid-cols-2 sm:grid-cols-4")}>
      {q.options.map((text, i) => (
        <button
          key={i}
          type="button"
          disabled={picked !== undefined}
          onClick={() => onPick(i)}
          className={cn(
            "flex items-center gap-3 rounded-lg border-2 px-4 py-3 text-left transition-colors disabled:cursor-default",
            optionClass(i, picked, q.answer)
          )}
        >
          <span className="text-sm font-semibold text-primary">{LETTERS[i]}</span>
          {french ? (
            <span className="flex-1 text-sm">
              {text}
              {picked !== undefined && q.mode === "usage" && q.option_hanzi && (
                <span className="hanzi ml-2 text-muted-foreground">({q.option_hanzi[i]})</span>
              )}
            </span>
          ) : (
            <ZhText text={text} showPinyin={showPinyin} className="flex-1 text-2xl" />
          )}
          {picked !== undefined && i === q.answer && <Check className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />}
          {picked !== undefined && i === picked && i !== q.answer && <X className="h-4 w-4 shrink-0 text-destructive" />}
        </button>
      ))}
    </div>
  );
}

function Feedback({
  q,
  picked,
  showPinyin,
  written,
}: {
  q: ClassifierQuestion;
  picked: number;
  showPinyin: boolean;
  written?: string;
}) {
  const ok = picked === q.answer;
  return (
    <div
      role="status"
      className={cn(
        "flex flex-col gap-2 rounded-lg p-4 text-sm",
        ok ? "bg-emerald-500/10 text-emerald-900 dark:text-emerald-100" : "bg-destructive/10 text-foreground"
      )}
    >
      <p className="font-semibold">
        {ok
          ? "Bonne réponse !"
          : written
            ? `Mauvaise réponse : tu as écrit « ${written} », c'était ${q.classifier}.`
            : `Mauvaise réponse : c'était ${q.classifier}.`}
      </p>
      {q.mode === "fill" && (
        <div className="flex items-start justify-between gap-2">
          <div>
            <ZhText text={q.sentence} showPinyin={showPinyin} className="text-lg text-foreground" />
            {q.fr && <p className="italic text-muted-foreground">{q.fr}</p>}
          </div>
          <ListenButton text={q.sentence} />
        </div>
      )}
      <p className="text-foreground">
        {q.mode === "fill" ? (
          <>
            <span className="hanzi font-medium">{q.classifier}</span> : {q.explain}
          </>
        ) : (
          q.explain
        )}
      </p>
    </div>
  );
}

function TypedAnswer({
  q,
  onSubmit,
  hintShown,
  onHint,
}: {
  q: FillQuestion;
  onSubmit: (text: string) => void;
  hintShown: boolean;
  onHint: () => void;
}) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const submit = () => {
    const text = value.replace(/\s+/g, "");
    if (!text) return;
    if (!HANZI_ONLY.test(text)) {
      setError("Écris le caractère chinois (clavier chinois / saisie pinyin de ton appareil).");
      return;
    }
    onSubmit(text);
  };
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          aria-label="Classificateur manquant"
          lang="zh-CN"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setError(null);
          }}
          onKeyDown={(e) => {
            // Enter also validates the character chosen in the IME: wait until it is done.
            if (e.key === "Enter" && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          autoFocus
          autoComplete="off"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          maxLength={4}
          className="hanzi h-14 w-28 text-center text-3xl"
        />
        <Button size="lg" onClick={submit} disabled={!value.trim()}>
          Valider
        </Button>
        {!hintShown && (
          <Button variant="ghost" size="sm" onClick={onHint} className="text-muted-foreground">
            <Lightbulb className="h-4 w-4" />
            Indice
          </Button>
        )}
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {hintShown && (
        <p className="flex items-start gap-2 rounded-lg bg-muted p-3 text-sm">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <span>
            <span className="font-medium">Indice :</span> {q.hint}
          </span>
        </p>
      )}
    </div>
  );
}
