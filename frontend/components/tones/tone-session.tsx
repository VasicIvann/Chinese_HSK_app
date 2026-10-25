"use client";

import { Check, Eye, EyeOff, Headphones, RotateCcw, Snail, Volume2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { ListenButton } from "@/components/listen-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useChineseSpeech } from "@/lib/speech";
import {
  markTone,
  normalizePlain,
  samePlain,
  sandhiNotes,
  TONE_LABEL,
  TONE_SIGN,
  TONES,
  typedTone,
  type Tone,
  type ToneWord,
} from "@/lib/tones";
import { cn } from "@/lib/utils";

export type ToneMode = "read" | "listen";

type Turn = { word: ToneWord; retry: boolean };
type Result = { word: ToneWord; correct: boolean; retry: boolean };

type Props = {
  mode: ToneMode;
  words: ToneWord[];
  title: string;
  onExit: () => void;
  onRestart: () => void;
  /** Called once at the end with the first attempt on each word (saved for the stats). */
  onFinish?: (answers: { id: string; correct: boolean }[]) => void;
};

/** A missed word comes back once, a few words later. */
const RETRY_GAP = 3;

export function ToneSession({ mode, words, title, onExit, onRestart, onFinish }: Props) {
  const [queue, setQueue] = useState<Turn[]>(() => words.map((word) => ({ word, retry: false })));
  const [index, setIndex] = useState(0);
  const [results, setResults] = useState<Result[]>([]);
  const done = index >= queue.length;
  const turn = queue[index];
  const reported = useRef(false);

  const firstTries = useMemo(() => results.filter((r) => !r.retry), [results]);
  useEffect(() => {
    if (!done || reported.current) return;
    reported.current = true;
    onFinish?.(firstTries.map((r) => ({ id: String(r.word.id), correct: r.correct })));
  }, [done, firstTries, onFinish]);

  const record = (correct: boolean) => {
    setResults((r) => [...r, { word: turn.word, correct, retry: turn.retry }]);
    if (!correct && !turn.retry) {
      setQueue((q) => {
        const at = Math.min(q.length, index + 1 + RETRY_GAP);
        return [...q.slice(0, at), { word: turn.word, retry: true }, ...q.slice(at)];
      });
    }
  };

  const score = firstTries.filter((r) => r.correct).length;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium">
          {title}
          {!done && (
            <span className="text-muted-foreground">
              {" "}
              · {index + 1} / {queue.length}
              {turn.retry && " · à revoir"}
            </span>
          )}
        </p>
        <Button variant="ghost" size="sm" onClick={onExit}>
          Quitter
        </Button>
      </div>
      {!done && (
        <div className="h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden>
          <div className="h-full bg-primary transition-all" style={{ width: `${(index / queue.length) * 100}%` }} />
        </div>
      )}

      {done ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-8 text-center">
            <p className="text-sm text-muted-foreground">Ton score (premier essai)</p>
            <p className="text-5xl font-semibold">
              {score}
              <span className="text-2xl text-muted-foreground"> / {firstTries.length}</span>
            </p>
            <ul className="flex w-full max-w-md flex-col gap-1 text-left text-sm">
              {firstTries.map((r) => {
                const second = results.find((x) => x.retry && x.word.id === r.word.id);
                return (
                  <li key={r.word.id} className={cn("flex items-start gap-2", r.correct ? "text-muted-foreground" : "text-destructive")}>
                    {r.correct ? <Check className="mt-0.5 h-4 w-4 shrink-0" /> : <X className="mt-0.5 h-4 w-4 shrink-0" />}
                    <span>
                      <span className="hanzi font-medium text-foreground">{r.word.hanzi}</span>{" "}
                      <span className="text-foreground">{r.word.syllables.map((s) => s.pinyin).join(" ")}</span> · {r.word.translation}
                      {second && <span className="text-muted-foreground">{second.correct ? " · réussi au 2e essai" : " · encore raté au 2e essai"}</span>}
                    </span>
                  </li>
                );
              })}
            </ul>
            <div className="flex flex-wrap justify-center gap-2">
              <Button onClick={onRestart}>
                <RotateCcw className="h-4 w-4" />
                Nouvelle série
              </Button>
              <Button variant="outline" onClick={onExit}>
                Retour
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : mode === "read" ? (
        <ReadQuestion key={index} word={turn.word} onChecked={record} onNext={() => setIndex((i) => i + 1)} last={index + 1 === queue.length} />
      ) : (
        <ListenQuestion key={index} word={turn.word} onChecked={record} onNext={() => setIndex((i) => i + 1)} last={index + 1 === queue.length} />
      )}
    </div>
  );
}

type QuestionProps = { word: ToneWord; onChecked: (correct: boolean) => void; onNext: () => void; last: boolean };

// --------------------------------------------------------------------------- mode 1: hanzi → tones

function ReadQuestion({ word, onChecked, onNext, last }: QuestionProps) {
  const n = word.syllables.length;
  const [tones, setTones] = useState<(Tone | null)[]>(() => Array(n).fill(null));
  const [active, setActive] = useState(0);
  const [showPinyin, setShowPinyin] = useState(false);
  const [checked, setChecked] = useState(false);

  const pickTone = useCallback(
    (tone: Tone) => {
      if (checked) return;
      const next = tones.map((t, i) => (i === active ? tone : t));
      setTones(next);
      const empty = next.findIndex((t, i) => t === null && i > active);
      const anyEmpty = next.findIndex((t) => t === null);
      if (anyEmpty < 0) {
        setChecked(true);
        onChecked(next.every((t, i) => t === word.syllables[i].tone));
      } else {
        setActive(empty >= 0 ? empty : anyEmpty);
      }
    },
    [checked, tones, active, onChecked, word]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLButtonElement && (e.key === "Enter" || e.key === " ")) return;
      if (!checked && /^[1-5]$/.test(e.key)) pickTone(Number(e.key) as Tone);
      else if (!checked && e.key === "Backspace" && active > 0) {
        setTones((t) => t.map((x, i) => (i === active - 1 ? null : x)));
        setActive(active - 1);
      } else if (!checked && e.key.toLowerCase() === "p") setShowPinyin((v) => !v);
      else if (checked && (e.key === "Enter" || e.key === "ArrowRight")) onNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [checked, active, pickTone, onNext]);

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-6 pt-6">
        <p className="text-sm text-muted-foreground">
          {n > 1 ? "Donne le ton de chaque syllabe." : "Quel est le ton de ce caractère ?"}
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {word.syllables.map((s, i) => {
            const t = tones[i];
            const ok = checked && t === s.tone;
            return (
              <button
                key={i}
                type="button"
                disabled={checked}
                onClick={() => setActive(i)}
                aria-label={`Syllabe ${i + 1}${t ? ` : ${TONE_LABEL[t]}` : ""}`}
                aria-current={!checked && i === active}
                className={cn(
                  "flex min-w-20 flex-col items-center gap-1 rounded-xl border-2 px-3 py-3 transition-colors",
                  !checked && i === active ? "border-primary bg-accent/40" : "border-transparent",
                  checked && (ok ? "border-emerald-500 bg-emerald-500/10" : "border-destructive bg-destructive/10")
                )}
              >
                <span className="hanzi text-6xl leading-none sm:text-7xl">{s.hanzi}</span>
                <span className="h-7 text-xl font-medium">
                  {checked ? s.pinyin : t ? (showPinyin ? markTone(s.plain, t) : TONE_SIGN[t]) : showPinyin ? s.plain : ""}
                </span>
                {checked && !ok && (
                  <span className="text-xs text-destructive">
                    {t ? `tu as dit : ${TONE_LABEL[t]}` : ""}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {!checked && (
          <>
            <Button variant="ghost" size="sm" onClick={() => setShowPinyin((v) => !v)} className="text-muted-foreground">
              {showPinyin ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {showPinyin ? "Masquer le pinyin" : "Afficher le pinyin (sans ton)"}
            </Button>
            <ToneButtons onPick={pickTone} syllable={showPinyin ? word.syllables[active].plain : undefined} />
            <p className="text-xs text-muted-foreground">Clavier : 1 à 5 · Retour arrière pour corriger · P pour le pinyin</p>
          </>
        )}

        {checked && <Feedback word={word} correct={tones.every((t, i) => t === word.syllables[i].tone)} onNext={onNext} last={last} />}
      </CardContent>
    </Card>
  );
}

function ToneButtons({ onPick, syllable }: { onPick: (t: Tone) => void; syllable?: string }) {
  return (
    <div role="group" aria-label="Tons" className="grid w-full max-w-xl grid-cols-5 gap-2">
      {TONES.map((t) => (
        <button
          key={t}
          type="button"
          onClick={() => onPick(t)}
          aria-label={TONE_LABEL[t]}
          className="flex flex-col items-center gap-0.5 rounded-lg border-2 border-input py-3 transition-colors hover:border-primary/60 hover:bg-accent/50"
        >
          <span className="text-2xl font-semibold leading-none">{t === 5 ? "∅" : t}</span>
          <span className="text-sm text-muted-foreground">{syllable ? markTone(syllable, t) : TONE_SIGN[t]}</span>
          <span className="hidden text-[11px] text-muted-foreground sm:block">{t === 5 ? "neutre" : `${t}${t === 1 ? "er" : "e"} ton`}</span>
        </button>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------------- mode 2: audio → pinyin + tones

function ListenQuestion({ word, onChecked, onNext, last }: QuestionProps) {
  const n = word.syllables.length;
  const [texts, setTexts] = useState<string[]>(() => Array(n).fill(""));
  const [tones, setTones] = useState<(Tone | null)[]>(() => Array(n).fill(null));
  const [checked, setChecked] = useState(false);
  const { speak, speakingKey } = useChineseSpeech();
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  const play = useCallback(
    (rate: number) => {
      const error = speak(word.hanzi, { key: `tone-${rate}`, rate });
      if (error) toast.error(error);
    },
    [speak, word.hanzi]
  );

  // Played once when the question appears (after a click, so browsers allow it).
  useEffect(() => {
    const id = window.setTimeout(() => play(0.8), 150);
    return () => window.clearTimeout(id);
  }, [play]);

  const ready = texts.every((t) => t.trim()) && tones.every((t) => t !== null);
  const letterOk = (i: number) => samePlain(texts[i], word.syllables[i].plain);
  const toneOk = (i: number) => tones[i] === word.syllables[i].tone;

  const check = () => {
    if (!ready || checked) return;
    setChecked(true);
    onChecked(word.syllables.every((_, i) => letterOk(i) && toneOk(i)));
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLButtonElement) return;
      if (checked && (e.key === "Enter" || e.key === "ArrowRight")) onNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [checked, onNext]);

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-6 pt-6">
        <p className="text-sm text-muted-foreground">
          Écoute, puis écris le pinyin de {n > 1 ? `chaque syllabe (${n} syllabes)` : "la syllabe"} et choisis son ton.
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          <Button size="lg" onClick={() => play(0.8)}>
            {speakingKey === "tone-0.8" ? <Volume2 className="h-5 w-5 animate-pulse" /> : <Headphones className="h-5 w-5" />}
            Réécouter
          </Button>
          <Button size="lg" variant="outline" onClick={() => play(0.5)}>
            <Snail className="h-5 w-5" />
            Lentement
          </Button>
        </div>

        <div className="grid w-full max-w-2xl gap-3" style={{ gridTemplateColumns: `repeat(auto-fit, minmax(${n > 2 ? 9.5 : 12}rem, 1fr))` }}>
          {word.syllables.map((s, i) => (
            <div
              key={i}
              className={cn(
                "flex flex-col gap-2 rounded-xl border-2 p-3",
                !checked && "border-border",
                checked && (letterOk(i) && toneOk(i) ? "border-emerald-500 bg-emerald-500/10" : "border-destructive bg-destructive/5")
              )}
            >
              <p className="text-xs font-medium text-muted-foreground">Syllabe {i + 1}</p>
              <Input
                ref={(el) => {
                  inputs.current[i] = el;
                }}
                aria-label={`Pinyin de la syllabe ${i + 1}`}
                value={texts[i]}
                disabled={checked}
                placeholder="ex. xue"
                autoFocus={i === 0}
                autoComplete="off"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                maxLength={8}
                onChange={(e) => {
                  const value = e.target.value;
                  setTexts((t) => t.map((x, k) => (k === i ? value : x)));
                  // "xue2" or "xué" also gives the tone.
                  const typed = typedTone(value);
                  if (typed) setTones((t) => t.map((x, k) => (k === i ? typed : x)));
                }}
                onKeyDown={(e) => {
                  if (e.key !== "Enter") return;
                  e.preventDefault();
                  if (ready) check();
                  else inputs.current[i + 1]?.focus();
                }}
                className="h-11 text-center text-lg"
              />
              <div role="group" aria-label={`Ton de la syllabe ${i + 1}`} className="grid grid-cols-5 gap-1">
                {TONES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    disabled={checked}
                    onClick={() => setTones((x) => x.map((v, k) => (k === i ? t : v)))}
                    aria-label={`${TONE_LABEL[t]} pour la syllabe ${i + 1}`}
                    aria-pressed={tones[i] === t}
                    className={cn(
                      "rounded-md border py-1.5 text-sm font-semibold transition-colors",
                      tones[i] === t ? "border-primary bg-primary text-primary-foreground" : "border-input hover:bg-accent/60",
                      checked && t === s.tone && tones[i] !== t && "border-emerald-500 text-emerald-700 dark:text-emerald-300"
                    )}
                  >
                    {t === 5 ? "∅" : t}
                  </button>
                ))}
              </div>
              {checked && (
                <p className="text-center text-sm">
                  <span className="hanzi mr-1 text-lg">{s.hanzi}</span>
                  <span className="font-medium">{s.pinyin}</span>
                  {!(letterOk(i) && toneOk(i)) && (
                    <span className="block text-xs text-destructive">
                      {!letterOk(i) && `lettres : « ${normalizePlain(texts[i])} » au lieu de « ${s.plain} »`}
                      {!letterOk(i) && !toneOk(i) && " · "}
                      {!toneOk(i) && tones[i] && `ton : ${TONE_LABEL[tones[i]!]} au lieu du ${TONE_LABEL[s.tone]}`}
                    </span>
                  )}
                </p>
              )}
            </div>
          ))}
        </div>

        {!checked ? (
          <div className="flex flex-col items-center gap-1">
            <Button size="lg" onClick={check} disabled={!ready}>
              Valider
            </Button>
            <p className="text-xs text-muted-foreground">∅ = ton neutre · tu peux aussi taper « xue2 » ou « xué »</p>
          </div>
        ) : (
          <Feedback word={word} correct={word.syllables.every((_, i) => letterOk(i) && toneOk(i))} onNext={onNext} last={last} showWord />
        )}
      </CardContent>
    </Card>
  );
}

// --------------------------------------------------------------------------- shared feedback

function Feedback({ word, correct, onNext, last, showWord }: { word: ToneWord; correct: boolean; onNext: () => void; last: boolean; showWord?: boolean }) {
  const notes = sandhiNotes(word);
  return (
    <div className="flex w-full flex-col gap-3">
      <div
        role="status"
        className={cn(
          "flex flex-col gap-2 rounded-lg p-4 text-sm",
          correct ? "bg-emerald-500/10 text-emerald-900 dark:text-emerald-100" : "bg-destructive/10 text-foreground"
        )}
      >
        <p className="font-semibold">{correct ? "Bonne réponse !" : "Pas tout à fait."}</p>
        <div className="flex items-center justify-between gap-2 text-foreground">
          <p>
            {showWord && <span className="hanzi mr-2 text-xl">{word.hanzi}</span>}
            <span className="text-base font-medium">{word.syllables.map((s) => s.pinyin).join(" ")}</span>
            <span className="text-muted-foreground"> — {word.translation}</span>
          </p>
          <ListenButton text={word.hanzi} rate={0.8} />
        </div>
        <p className="text-xs text-muted-foreground">{word.syllables.map((s) => `${s.hanzi} : ${TONE_LABEL[s.tone]}`).join(" · ")}</p>
        {notes.map((note) => (
          <p key={note} className="text-foreground">
            💡 {note}
          </p>
        ))}
      </div>
      <Button onClick={onNext} autoFocus>
        {last ? "Voir mon score" : "Mot suivant"}
      </Button>
    </div>
  );
}
