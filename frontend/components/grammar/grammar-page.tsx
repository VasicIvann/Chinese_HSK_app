"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpenCheck, Check, ChevronDown, Search, Shuffle, X } from "lucide-react";
import { useMemo, useState } from "react";

import { LevelPicker, useExerciseLevel } from "@/components/exercises/level-picker";
import { TextChoices } from "@/components/exercises/choices";
import { ZhText } from "@/components/exercises/zh-text";
import { HskVersionToggle } from "@/components/hsk-version-toggle";
import { ListenButton } from "@/components/listen-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { getGrammar, postExerciseResult, type ExerciseLevel, type GrammarPoint, type GrammarQuiz } from "@/lib/api/exercises";
import { useHskVersion } from "@/lib/hsk-version";
import { cn } from "@/lib/utils";

/** French names of the official headings (语法项目). */
const ITEM_FR: Record<string, string> = {
  语素: "Préfixes et suffixes",
  词类: "Catégories de mots",
  短语: "Groupes de mots",
  固定格式: "Structures figées",
  句子成分: "Fonctions dans la phrase",
  句子的类型: "Types de phrases",
  动作的态: "Aspects de l'action",
  特殊表达法: "Expressions particulières",
  强调的方法: "Mettre en relief",
  提问的方法: "Poser des questions",
  口语格式: "Tournures de l'oral",
};

type Filter = "all" | "todo" | "review";

const isDone = (p: GrammarPoint) => !!p.last && p.last.score === p.last.total;

export function GrammarPage() {
  const { version } = useHskVersion();
  const [level, setLevel] = useExerciseLevel();
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [mixed, setMixed] = useState<{ point: GrammarPoint; quiz: GrammarQuiz; index: number }[] | null>(null);

  const query = useQuery({ queryKey: ["grammar", level, version], queryFn: () => getGrammar(level, version) });
  const points = useMemo(() => query.data?.points ?? [], [query.data]);
  const done = points.filter(isDone).length;

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return points.filter((p) => {
      if (filter === "todo" && p.last) return false;
      if (filter === "review" && (!p.last || isDone(p))) return false;
      if (!term) return true;
      return [p.title, p.content, p.detail, p.category, p.code].some((t) => t.toLowerCase().includes(term));
    });
  }, [points, filter, search]);

  const groups = useMemo(() => {
    const out: { item: string; points: GrammarPoint[] }[] = [];
    for (const p of visible) {
      const last = out[out.length - 1];
      if (last && last.item === p.item) last.points.push(p);
      else out.push({ item: p.item, points: [p] });
    }
    return out;
  }, [visible]);

  const startMixed = () => {
    const pool = points.flatMap((point) => point.quiz.map((quiz, index) => ({ point, quiz, index })));
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    setMixed(pool.slice(0, 10));
  };

  if (mixed) return <MixedQuiz level={level} questions={mixed} onExit={() => setMixed(null)} />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Grammaire</h1>
          <p className="mt-1 text-muted-foreground">
            Les points de grammaire officiels du niveau (语法等级大纲 du syllabus HSK), expliqués en français, avec des exemples et
            un mini-quiz pour chacun.
          </p>
        </div>
        <HskVersionToggle />
      </div>
      <LevelPicker level={level} onChange={setLevel} />
      {version === "2.0" && (
        <p className="-mt-3 text-sm text-muted-foreground">
          L&apos;ancien HSK 2.0 n&apos;a pas de liste de grammaire officielle par niveau : voici celle du syllabus 3.0, qui
          couvre les mêmes structures de base.
        </p>
      )}

      {query.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : query.isError ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">Impossible de charger la grammaire.</CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
              <div>
                <p className="text-sm text-muted-foreground">Points réussis (quiz sans faute)</p>
                <p className="text-2xl font-semibold">
                  {done} <span className="text-base text-muted-foreground">/ {points.length}</span>
                </p>
              </div>
              <div className="h-2 min-w-40 flex-1 overflow-hidden rounded-full bg-muted" aria-hidden>
                <div className="h-full bg-primary" style={{ width: `${points.length ? (done / points.length) * 100 : 0}%` }} />
              </div>
              <Button onClick={startMixed} disabled={points.length === 0}>
                <Shuffle className="h-4 w-4" />
                Quiz mélangé (10 questions)
              </Button>
            </CardContent>
          </Card>

          <div className="flex flex-wrap items-center gap-2">
            {(
              [
                ["all", "Tous"],
                ["todo", "Pas encore faits"],
                ["review", "À revoir"],
              ] as [Filter, string][]
            ).map(([value, label]) => (
              <Button key={value} size="sm" variant={filter === value ? "default" : "outline"} onClick={() => setFilter(value)}>
                {label}
              </Button>
            ))}
            <div className="relative ml-auto w-full sm:w-64">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Chercher (把, comparaison…)" className="pl-9" />
            </div>
          </div>

          {groups.length === 0 && <p className="text-center text-sm text-muted-foreground">Aucun point ne correspond.</p>}
          {groups.map((group, gi) => (
            <section key={`${group.item}-${gi}`} className="flex flex-col gap-2">
              <h2 className="flex items-baseline gap-2 text-lg font-semibold">
                {ITEM_FR[group.item] ?? group.item}
                <span className="hanzi text-sm font-normal text-muted-foreground">{group.item}</span>
              </h2>
              {group.points.map((point) => (
                <PointCard key={point.id} point={point} level={level} />
              ))}
            </section>
          ))}
        </>
      )}
    </div>
  );
}

function PointCard({ point, level }: { point: GrammarPoint; level: ExerciseLevel }) {
  const [open, setOpen] = useState(false);
  const [showPinyin, setShowPinyin] = useState(level < 3);
  const status = !point.last ? null : isDone(point) ? "ok" : "ko";
  return (
    <Card className={cn(open && "border-primary/40")}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-start gap-3 p-4 text-left"
      >
        <span className="mt-0.5 shrink-0 rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">{point.code}</span>
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="font-medium">{point.title}</span>
          <span className="hanzi truncate text-sm text-muted-foreground">
            {[point.category, point.detail].filter(Boolean).join(" · ")}
            {point.content ? ` — ${point.content}` : ""}
          </span>
        </span>
        {status === "ok" && <Check className="mt-1 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-label="Réussi" />}
        {status === "ko" && <X className="mt-1 h-4 w-4 shrink-0 text-primary" aria-label="À revoir" />}
        <ChevronDown className={cn("mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <CardContent className="flex flex-col gap-4 border-t border-border pt-4">
          <p className="hanzi text-sm text-muted-foreground">
            Syllabus : {point.content || point.detail}
          </p>
          <p className="whitespace-pre-line leading-relaxed">{point.explanation}</p>
          {point.pattern && (
            <pre className="hanzi whitespace-pre-wrap rounded-md bg-muted px-3 py-2 text-sm">{point.pattern}</pre>
          )}
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Exemples</p>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
              <input type="checkbox" className="h-4 w-4" checked={showPinyin} onChange={(e) => setShowPinyin(e.target.checked)} />
              Pinyin
            </label>
          </div>
          <ul className="flex flex-col gap-2">
            {point.examples.map((ex, i) => (
              <li key={i} className="flex items-start justify-between gap-2 rounded-lg border border-border p-3">
                <div>
                  <ZhText text={ex.zh} showPinyin={showPinyin} className="text-lg" />
                  <p className="text-sm italic text-muted-foreground">{ex.fr}</p>
                </div>
                <ListenButton text={ex.zh} />
              </li>
            ))}
          </ul>
          <PointQuiz point={point} level={level} showPinyin={showPinyin} />
        </CardContent>
      )}
    </Card>
  );
}

function PointQuiz({ point, level, showPinyin }: { point: GrammarPoint; level: ExerciseLevel; showPinyin: boolean }) {
  const queryClient = useQueryClient();
  const [given, setGiven] = useState<Record<number, number>>({});
  const save = useMutation({
    mutationFn: (answers: { id: string; correct: boolean }[]) =>
      postExerciseResult({ section: "grammar", level, part: point.id, answers }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["grammar"] }),
  });

  const pick = (qi: number, i: number) => {
    const next = { ...given, [qi]: i };
    setGiven(next);
    if (Object.keys(next).length === point.quiz.length) {
      save.mutate(point.quiz.map((q, k) => ({ id: `${point.id}#${k}`, correct: next[k] === q.answer })));
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg bg-muted/40 p-4">
      <p className="flex items-center gap-2 text-sm font-medium">
        <BookOpenCheck className="h-4 w-4 text-primary" /> Vérifie que tu as compris
      </p>
      {point.quiz.map((q, qi) => (
        <QuizQuestion key={qi} quiz={q} given={given[qi] ?? null} onPick={(i) => pick(qi, i)} showPinyin={showPinyin} />
      ))}
    </div>
  );
}

function QuizQuestion({
  quiz,
  given,
  onPick,
  showPinyin,
}: {
  quiz: GrammarQuiz;
  given: number | null;
  onPick: (i: number) => void;
  showPinyin: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <ZhText text={quiz.q} showPinyin={showPinyin} className="text-lg" />
      <TextChoices options={quiz.options} state={{ given, answer: quiz.answer }} onPick={onPick} showPinyin={showPinyin} />
      {given !== null && (
        <p className={cn("text-sm", given === quiz.answer ? "text-emerald-700 dark:text-emerald-300" : "text-destructive")}>
          {given === quiz.answer ? "✓ " : "✗ "}
          <span className="text-foreground">{quiz.why}</span>
        </p>
      )}
    </div>
  );
}

function MixedQuiz({
  level,
  questions,
  onExit,
}: {
  level: ExerciseLevel;
  questions: { point: GrammarPoint; quiz: GrammarQuiz; index: number }[];
  onExit: () => void;
}) {
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [given, setGiven] = useState<Record<number, number>>({});
  const [showPinyin, setShowPinyin] = useState(level < 3);
  const save = useMutation({
    mutationFn: async () => {
      // Results per point, so the list shows which points to review.
      const byPoint = new Map<string, { id: string; correct: boolean }[]>();
      questions.forEach((q, i) => {
        const list = byPoint.get(q.point.id) ?? [];
        list.push({ id: `${q.point.id}#${q.index}`, correct: given[i] === q.quiz.answer });
        byPoint.set(q.point.id, list);
      });
      await Promise.all(
        [...byPoint].map(([part, answers]) => postExerciseResult({ section: "grammar", level, part, answers }))
      );
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["grammar"] }),
  });
  const done = index >= questions.length;
  const score = questions.filter((q, i) => given[i] === q.quiz.answer).length;
  const current = questions[index];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          Quiz mélangé · HSK {level} {done ? "" : `· ${index + 1} / ${questions.length}`}
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
      {done ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
            <p className="text-5xl font-semibold">
              {score}
              <span className="text-2xl text-muted-foreground"> / {questions.length}</span>
            </p>
            <ul className="flex flex-col gap-1 text-sm">
              {questions.map((q, i) => (
                <li key={i} className={given[i] === q.quiz.answer ? "text-muted-foreground" : "text-destructive"}>
                  {given[i] === q.quiz.answer ? "✓" : "✗"} {q.point.code} · {q.point.title}
                </li>
              ))}
            </ul>
            <Button variant="outline" onClick={onExit}>
              Retour aux points
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col gap-4 pt-6">
            <p className="text-xs text-muted-foreground">
              {current.point.code} · {current.point.title}
            </p>
            <QuizQuestion
              key={index}
              quiz={current.quiz}
              given={given[index] ?? null}
              onPick={(i) => setGiven((g) => ({ ...g, [index]: i }))}
              showPinyin={showPinyin}
            />
            {given[index] !== undefined && (
              <Button
                onClick={() => {
                  if (index + 1 === questions.length) save.mutate();
                  setIndex(index + 1);
                }}
              >
                {index + 1 === questions.length ? "Voir mon score" : "Question suivante"}
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
