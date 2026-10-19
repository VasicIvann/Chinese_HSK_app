"use client";

import { useMutation } from "@tanstack/react-query";
import { Check, Delete, Loader2, Sparkles, X } from "lucide-react";
import { useMemo, useState } from "react";

import { AudioPanel } from "@/components/exercises/audio-panel";
import { JudgeChoices, PictureChoices, TextChoices } from "@/components/exercises/choices";
import { toPinyin, ZhText } from "@/components/exercises/zh-text";
import { ListenButton } from "@/components/listen-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import {
  checkSentence,
  type AudioLine,
  type CharPinyinItem,
  type ExerciseItem,
  type ExerciseLevel,
  type MakeSentenceItem,
  type ReorderItem,
  type SentenceCheck,
} from "@/lib/api/exercises";
import { cn } from "@/lib/utils";

export type Given = number | boolean | string;
export type QuestionResult = { correct: boolean; given: Given };

type Props = {
  item: ExerciseItem;
  sub?: number;
  level: ExerciseLevel;
  showPinyin: boolean;
  result?: QuestionResult;
  onAnswer: (result: QuestionResult) => void;
};

const SPEAKER = { m: "男", f: "女", n: "" } as const;

/** What was said, shown after answering: speaker, characters + pinyin, French. */
export function Transcript({ lines, fr, question, questionFr }: { lines: AudioLine[]; fr: string; question?: string; questionFr?: string }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-muted/40 p-4 text-left">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Enregistrement</p>
      {lines.map((line, i) => (
        <p key={i} className="flex gap-2">
          {line.s !== "n" && <span className="hanzi shrink-0 text-muted-foreground">{SPEAKER[line.s]}：</span>}
          <ZhText text={line.t} showPinyin className="text-lg" />
        </p>
      ))}
      {question && (
        <p className="flex gap-2">
          <span className="hanzi shrink-0 text-muted-foreground">问：</span>
          <ZhText text={question} showPinyin className="text-lg" />
        </p>
      )}
      <p className="text-sm italic">{fr}</p>
      {questionFr && <p className="text-sm italic text-muted-foreground">Question : {questionFr}</p>}
    </div>
  );
}

function Verdict({ correct, children }: { correct: boolean; children?: React.ReactNode }) {
  return (
    <div
      role="status"
      className={cn(
        "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium",
        correct ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" : "bg-destructive/10 text-destructive"
      )}
    >
      {correct ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
      {correct ? "Bonne réponse" : "Mauvaise réponse"}
      {children}
    </div>
  );
}

export function QuestionView({ item, sub = 0, level, showPinyin, result, onAnswer }: Props) {
  const choose = (given: number, answer: number) => onAnswer({ correct: given === answer, given });
  const judge = (given: boolean, answer: boolean) => onAnswer({ correct: given === answer, given });

  switch (item.type) {
    case "pic_choice":
    case "pic_answer":
      return (
        <div className="flex flex-col gap-4">
          <AudioPanel script={item.audio} />
          <PictureChoices
            options={item.options}
            state={{ given: (result?.given as number) ?? null, answer: item.answer }}
            onPick={(i) => choose(i, item.answer)}
          />
          {result && <Verdict correct={result.correct} />}
          {result && <Transcript lines={item.audio} fr={item.fr} />}
        </div>
      );
    case "pic_judge":
      return (
        <div className="flex flex-col gap-4">
          <AudioPanel script={item.audio} />
          <div className="rounded-lg border-2 border-dashed border-border p-4 text-center italic">🖼 {item.picture}</div>
          <JudgeChoices state={{ given: (result?.given as boolean) ?? null, answer: item.answer }} onPick={(v) => judge(v, item.answer)} />
          {result && <Verdict correct={result.correct} />}
          {result && <Transcript lines={item.audio} fr={item.fr} />}
        </div>
      );
    case "pic_match":
    case "word_match": {
      const q = item.items[sub];
      const state = { given: (result?.given as number) ?? null, answer: q.answer };
      return (
        <div className="flex flex-col gap-4">
          <AudioPanel key={sub} script={q.audio} />
          {item.type === "pic_match" ? (
            <PictureChoices options={item.options} state={state} onPick={(i) => choose(i, q.answer)} />
          ) : (
            <TextChoices options={item.options} state={state} onPick={(i) => choose(i, q.answer)} showPinyin={showPinyin} />
          )}
          {result && <Verdict correct={result.correct} />}
          {result && <Transcript lines={q.audio} fr={q.fr} />}
        </div>
      );
    }
    case "short_mcq":
    case "long_mcq":
    case "passage_mcq":
      return (
        <div className="flex flex-col gap-4">
          <AudioPanel script={[...item.audio, { s: "n", t: item.question }]} />
          <TextChoices
            options={item.options}
            translations={item.options_fr}
            state={{ given: (result?.given as number) ?? null, answer: item.answer }}
            onPick={(i) => choose(i, item.answer)}
            showPinyin={showPinyin}
          />
          {result && <Verdict correct={result.correct} />}
          {result && <Transcript lines={item.audio} fr={item.fr} question={item.question} questionFr={item.question_fr} />}
        </div>
      );
    case "passage_judge":
      return (
        <div className="flex flex-col gap-4">
          <AudioPanel script={item.audio} />
          <p className="rounded-lg border border-border bg-card p-4 text-center">
            <span className="mr-1 text-primary">★</span>
            <ZhText text={item.statement} showPinyin={showPinyin} className="text-xl" />
            {result && <span className="mt-1 block text-sm italic text-muted-foreground">{item.statement_fr}</span>}
          </p>
          <JudgeChoices state={{ given: (result?.given as boolean) ?? null, answer: item.answer }} onPick={(v) => judge(v, item.answer)} />
          {result && <Verdict correct={result.correct} />}
          {result && <Transcript lines={item.audio} fr={item.fr} />}
        </div>
      );
    case "char_pinyin":
      return <CharPinyinQuestion item={item} showPinyin={showPinyin} result={result} onAnswer={onAnswer} />;
    case "reorder":
      return <ReorderQuestion item={item} result={result} onAnswer={onAnswer} />;
    case "make_sentence":
      return <MakeSentenceQuestion item={item} level={level} showPinyin={showPinyin} result={result} onAnswer={onAnswer} />;
  }
}

// --------------------------------------------------------------------------- writing

const normalize = (s: string) => s.replace(/[\s。？！，、.?!,]/g, "");

function CharPinyinQuestion({
  item,
  showPinyin,
  result,
  onAnswer,
}: {
  item: CharPinyinItem;
  showPinyin: boolean;
  result?: QuestionResult;
  onAnswer: (r: QuestionResult) => void;
}) {
  const [value, setValue] = useState("");
  const submit = () => {
    const given = value.trim();
    if (!given) return;
    onAnswer({ correct: normalize(given) === normalize(item.answer), given });
  };
  const full = `${item.before}${item.answer}${item.after}`;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-center gap-x-1 gap-y-3 rounded-xl border border-border bg-card px-4 py-8 text-2xl">
        <ZhText text={item.before} showPinyin={showPinyin} />
        <span className="inline-flex flex-col items-center">
          <span className="font-sans text-base font-medium text-primary">{item.pinyin}</span>
          <span
            className={cn(
              "hanzi min-w-12 border-b-2 px-2 text-center",
              result ? (result.correct ? "border-emerald-500 text-emerald-600" : "border-destructive text-destructive") : "border-primary"
            )}
          >
            {result ? String(result.given) : " "}
          </span>
        </span>
        <ZhText text={item.after} showPinyin={showPinyin} />
      </div>
      {!result ? (
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={`Écris le caractère (${item.pinyin})`}
            className="hanzi text-lg"
            autoComplete="off"
            lang="zh-CN"
            aria-label="Caractère manquant"
          />
          <Button type="submit" disabled={!value.trim()}>
            Valider
          </Button>
        </form>
      ) : (
        <>
          <Verdict correct={result.correct}>
            {!result.correct && (
              <span className="ml-1">
                — il fallait <span className="hanzi text-lg">{item.answer}</span>
              </span>
            )}
          </Verdict>
          <div className="flex items-start justify-between gap-2 rounded-lg border border-border bg-muted/40 p-4">
            <div>
              <ZhText text={full} showPinyin className="text-lg" />
              <p className="text-sm italic">{item.fr}</p>
            </div>
            <ListenButton text={full} />
          </div>
        </>
      )}
    </div>
  );
}

function ReorderQuestion({
  item,
  result,
  onAnswer,
}: {
  item: ReorderItem;
  result?: QuestionResult;
  onAnswer: (r: QuestionResult) => void;
}) {
  const [picked, setPicked] = useState<number[]>([]);
  const sentence = picked.map((i) => item.words[i]).join("");
  const submit = () => {
    const correct = item.answers.some((a) => normalize(a) === normalize(sentence));
    onAnswer({ correct, given: sentence });
  };
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">Touche les mots dans l&apos;ordre pour écrire la phrase.</p>
      <div className="flex flex-wrap justify-center gap-2 rounded-xl border border-border bg-card p-4">
        {item.words.map((w, i) => (
          <button
            key={i}
            type="button"
            disabled={picked.includes(i) || !!result}
            onClick={() => setPicked((p) => [...p, i])}
            className="hanzi rounded-md border border-input bg-background px-3 py-2 text-xl transition-colors hover:border-primary disabled:opacity-30"
          >
            {w}
          </button>
        ))}
      </div>
      <div className="flex min-h-14 items-center gap-2 rounded-lg border-2 border-dashed border-primary/40 px-4 py-2">
        <span className="hanzi flex-1 text-2xl">{sentence || <span className="text-base text-muted-foreground">Ta phrase…</span>}</span>
        {!result && picked.length > 0 && (
          <Button type="button" variant="ghost" size="icon" onClick={() => setPicked((p) => p.slice(0, -1))} aria-label="Retirer le dernier mot">
            <Delete className="h-4 w-4" />
          </Button>
        )}
      </div>
      {!result ? (
        <Button type="button" onClick={submit} disabled={picked.length !== item.words.length}>
          Valider
        </Button>
      ) : (
        <>
          <Verdict correct={result.correct} />
          <div className="flex items-start justify-between gap-2 rounded-lg border border-border bg-muted/40 p-4">
            <div>
              <ZhText text={item.answers[0]} showPinyin className="text-lg" />
              {item.answers.length > 1 && (
                <p className="hanzi text-sm text-muted-foreground">Aussi correct : {item.answers.slice(1).join(" / ")}</p>
              )}
              <p className="text-sm italic">{item.fr}</p>
            </div>
            <ListenButton text={item.answers[0]} />
          </div>
        </>
      )}
    </div>
  );
}

function MakeSentenceQuestion({
  item,
  level,
  showPinyin,
  result,
  onAnswer,
}: {
  item: MakeSentenceItem;
  level: ExerciseLevel;
  showPinyin: boolean;
  result?: QuestionResult;
  onAnswer: (r: QuestionResult) => void;
}) {
  const [value, setValue] = useState("");
  const [check, setCheck] = useState<SentenceCheck | null>(null);
  const [selfCheck, setSelfCheck] = useState(false);
  const wordPinyin = useMemo(() => toPinyin(item.word), [item.word]);
  const grade = useMutation({
    mutationFn: () => checkSentence(level, item.word, value.trim()),
    retry: 0,
    onSuccess: (res) => {
      setCheck(res);
      onAnswer({ correct: res.correct, given: value.trim() });
    },
    onError: () => setSelfCheck(true),
  });
  const error =
    grade.error instanceof ApiError ? grade.error.detail : grade.error ? "La correction a échoué." : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col items-center gap-1 rounded-xl border border-border bg-card px-4 py-6">
        <p className="text-sm text-muted-foreground">Écris une phrase avec :</p>
        <p className="hanzi text-4xl">{item.word}</p>
        {showPinyin && <p className="text-sm text-muted-foreground">{wordPinyin}</p>}
      </div>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={!!result}
        rows={2}
        lang="zh-CN"
        maxLength={120}
        placeholder="Ta phrase en chinois…"
        className="hanzi w-full rounded-md border border-input bg-background px-3 py-2 text-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-80"
        aria-label="Ta phrase"
      />
      {!result && !selfCheck && (
        <Button type="button" onClick={() => grade.mutate()} disabled={!value.trim() || grade.isPending}>
          {grade.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {grade.isPending ? "Correction…" : "Faire corriger par Claude"}
        </Button>
      )}
      {!result && selfCheck && (
        <div className="flex flex-col gap-3 rounded-lg border border-border bg-muted/40 p-4">
          {error && <p className="text-sm text-destructive">{error} Compare toi-même avec la phrase modèle :</p>}
          <ZhText text={item.reference} showPinyin className="text-lg" />
          <p className="text-sm italic">{item.fr}</p>
          <div className="grid grid-cols-2 gap-2">
            <Button type="button" variant="outline" onClick={() => onAnswer({ correct: true, given: value.trim() })}>
              Ma phrase est juste
            </Button>
            <Button type="button" variant="outline" onClick={() => onAnswer({ correct: false, given: value.trim() })}>
              Elle est fausse
            </Button>
          </div>
        </div>
      )}
      {result && (
        <>
          <Verdict correct={result.correct} />
          {check && (
            <div className="flex flex-col gap-1 rounded-lg border border-border bg-muted/40 p-4">
              {!check.correct && (
                <>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Correction</p>
                  <p className="hanzi text-lg">{check.corrected}</p>
                  {check.pinyin && <p className="text-sm text-muted-foreground">{check.pinyin}</p>}
                </>
              )}
              {check.translation && <p className="text-sm italic">{check.translation}</p>}
              {check.explanation && <p className="text-sm">{check.explanation}</p>}
            </div>
          )}
          <div className="flex items-start justify-between gap-2 rounded-lg border border-border bg-card p-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Phrase modèle</p>
              <ZhText text={item.reference} showPinyin className="text-lg" />
              <p className="text-sm italic">{item.fr}</p>
            </div>
            <ListenButton text={item.reference} />
          </div>
        </>
      )}
    </div>
  );
}
