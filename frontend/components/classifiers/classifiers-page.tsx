"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, ChevronDown, Keyboard, ListChecks, PenLine, Search, Sparkles, Target } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { ClassifierQuiz } from "@/components/classifiers/classifier-quiz";
import { LevelPicker, useExerciseLevel } from "@/components/exercises/level-picker";
import { toPinyin, ZhText } from "@/components/exercises/zh-text";
import { HskVersionToggle } from "@/components/hsk-version-toggle";
import { ListenButton } from "@/components/listen-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import {
  generateClassifierSentences,
  getClassifierQuiz,
  getClassifiers,
  type Classifier,
  type ClassifierKind,
  type ClassifierQuiz as Quiz,
  type QuizMode,
} from "@/lib/api/classifiers";
import { postExerciseResult, type ExerciseLevel } from "@/lib/api/exercises";
import { useHskVersion, VERSION_INFO } from "@/lib/hsk-version";
import { cn } from "@/lib/utils";

type Tab = "fiches" | "fill" | "write" | "usage";
type KindFilter = "all" | "nominal" | "verbal";
/** `typed`: fill-in sentences answered by writing the classifier (no options). */
type Running = { quiz: Quiz; title: string; typed: boolean; request: () => Promise<Quiz> };

const KIND_LABEL: Record<ClassifierKind, string> = {
  nominal: "nominal",
  verbal: "verbal",
  both: "nominal et verbal",
};

const errorText = (error: unknown, fallback: string) =>
  error instanceof ApiError && error.detail ? error.detail : fallback;

export function ClassifiersPage() {
  const { version } = useHskVersion();
  const [level, setLevel] = useExerciseLevel();
  const [tab, setTab] = useState<Tab>("fiches");
  const [running, setRunning] = useState<Running | null>(null);

  const list = useQuery({
    queryKey: ["classifiers", level, version],
    queryFn: () => getClassifiers(level, version),
  });

  const start = useMutation({
    mutationFn: async (run: Omit<Running, "quiz">) => ({ ...run, quiz: await run.request() }),
    retry: 0,
    onSuccess: (run) => {
      if (run.quiz.questions.length === 0) {
        toast.error("Pas encore de questions pour ce choix.");
        return;
      }
      setRunning(run);
      if (run.quiz.quota_remaining !== undefined) {
        toast.success(`${run.quiz.questions.length} nouvelles phrases (encore ${run.quiz.quota_remaining} générations aujourd'hui).`);
      }
    },
    onError: (error) => toast.error(errorText(error, "Impossible de charger les questions.")),
  });

  const fillTitle = (typed: boolean, hanzi?: string) =>
    `${typed ? "Écrire le classificateur" : "Phrases à compléter"}${hanzi ? ` · ${hanzi}` : ""}`;
  const startQuiz = (mode: QuizMode, hanzi?: string, typed = false) =>
    start.mutate({
      title: mode === "fill" ? fillTitle(typed, hanzi) : "Quiz des usages",
      typed: mode === "fill" && typed,
      request: () => getClassifierQuiz(mode, level, version, hanzi),
    });
  const generate = (hanzi?: string, typed = false) =>
    start.mutate({
      title: `${fillTitle(typed, hanzi)} · nouvelles phrases`,
      typed,
      request: () => generateClassifierSentences(level, version, hanzi),
    });

  if (running) {
    return (
      <ClassifierQuiz
        key={running.quiz.questions.map((q) => q.id).join()}
        title={`${running.title} · HSK ${level}`}
        questions={running.quiz.questions}
        typed={running.typed}
        defaultPinyin={level < 3}
        onExit={() => {
          setRunning(null);
          list.refetch();
        }}
        // A generated series is replayed from the pool (no new Claude call on "Nouvelle série").
        onRestart={() =>
          start.mutate({
            title: running.title.replace(" · nouvelles phrases", ""),
            typed: running.typed,
            request: () => getClassifierQuiz(running.quiz.mode, level, version, running.quiz.hanzi ?? undefined),
          })
        }
        restarting={start.isPending}
        onFinish={(answers) => {
          const { mode, hanzi } = running.quiz;
          const base = mode === "fill" && running.typed ? "write" : mode;
          const part = mode === "fill" && hanzi ? `${base}-${hanzi}` : base;
          // Saved for the Account statistics; a failure only loses that data point.
          postExerciseResult({ section: "classifiers", version, level, part, answers }).catch(() => undefined);
        }}
      />
    );
  }

  const classifiers = list.data?.classifiers ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Classificateurs</h1>
          <p className="mt-1 text-muted-foreground">
            Les classificateurs (量词) du niveau choisi et des niveaux précédents : à quoi sert chacun, avec quels mots, et des
            exercices pour ne plus les confondre.
          </p>
        </div>
        <HskVersionToggle />
      </div>
      <LevelPicker level={level} onChange={setLevel} />

      <div role="tablist" aria-label="Section" className="flex gap-1 overflow-x-auto rounded-lg bg-muted p-1">
        {(
          [
            ["fiches", "Fiches", "Fiches", BookOpen],
            ["fill", "Phrases à compléter", "Phrases", PenLine],
            ["write", "Écrire le classificateur", "Écrire", Keyboard],
            ["usage", "Quiz des usages", "Usages", ListChecks],
          ] as const
        ).map(([value, label, short, Icon]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-label={label}
            aria-selected={tab === value}
            onClick={() => setTab(value)}
            className={cn(
              "flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors",
              tab === value ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            <span className="sm:hidden">{short}</span>
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {list.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : list.isError ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">Impossible de charger les classificateurs.</CardContent>
        </Card>
      ) : tab === "fiches" ? (
        <Fiches
          classifiers={classifiers}
          level={level}
          busy={start.isPending}
          onPractice={(hz) => startQuiz("fill", hz)}
          onWrite={(hz) => startQuiz("fill", hz, true)}
          onGenerate={(hz) => generate(hz)}
        />
      ) : tab === "fill" ? (
        <Card>
          <CardHeader>
            <CardTitle>Phrases à compléter</CardTitle>
            <CardDescription>
              Une phrase, un trou : choisis le classificateur qui convient parmi quatre. Les phrases restent dans le vocabulaire
              du niveau ({VERSION_INFO[version].label}), la moitié porte sur les classificateurs nouveaux au HSK {level}.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              {list.data?.sentences ?? 0} phrases disponibles · {classifiers.length} classificateurs
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="lg" onClick={() => startQuiz("fill")} disabled={start.isPending}>
                <PenLine className="h-4 w-4" />
                Commencer (10 phrases)
              </Button>
              <Button size="lg" variant="outline" onClick={() => generate()} disabled={start.isPending}>
                <Sparkles className="h-4 w-4" />
                Plus de phrases (Claude)
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              « Plus de phrases » demande 10 nouvelles phrases à Claude ; elles s&apos;ajoutent à ta banque.
            </p>
          </CardContent>
        </Card>
      ) : tab === "write" ? (
        <Card>
          <CardHeader>
            <CardTitle>Écrire le classificateur</CardTitle>
            <CardDescription>
              Les mêmes phrases, mais sans propositions : écris toi-même le classificateur manquant en caractère chinois
              (clavier chinois de ton appareil), puis découvre si c&apos;est juste. Un indice donne l&apos;usage en français si tu
              bloques.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              {list.data?.sentences ?? 0} phrases disponibles · seule la réponse attendue est comptée juste
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="lg" onClick={() => startQuiz("fill", undefined, true)} disabled={start.isPending}>
                <Keyboard className="h-4 w-4" />
                Commencer (10 phrases)
              </Button>
              <Button size="lg" variant="outline" onClick={() => generate(undefined, true)} disabled={start.isPending}>
                <Sparkles className="h-4 w-4" />
                Plus de phrases (Claude)
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Quiz des usages</CardTitle>
            <CardDescription>Trois sortes de questions, mélangées :</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <ul className="flex flex-col gap-2 text-sm">
              <li className="flex gap-2">
                <Target className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                un usage (« les véhicules à roues ») → quel classificateur ?
              </li>
              <li className="flex gap-2">
                <Target className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                un nom (<span className="hanzi">一（ ）车</span>) → quel classificateur ?
              </li>
              <li className="flex gap-2">
                <Target className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                un classificateur (<span className="hanzi">辆</span>) → à quoi sert-il ?
              </li>
            </ul>
            <Button size="lg" className="self-start" onClick={() => startQuiz("usage")} disabled={start.isPending || classifiers.length < 4}>
              <ListChecks className="h-4 w-4" />
              Commencer (10 questions)
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Fiches({
  classifiers,
  level,
  busy,
  onPractice,
  onWrite,
  onGenerate,
}: {
  classifiers: Classifier[];
  level: ExerciseLevel;
  busy: boolean;
  onPractice: (hanzi: string) => void;
  onWrite: (hanzi: string) => void;
  onGenerate: (hanzi: string) => void;
}) {
  const [kind, setKind] = useState<KindFilter>("all");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const groups = useMemo(() => {
    const term = search.trim().toLowerCase();
    const visible = classifiers.filter((c) => {
      if (kind === "nominal" && c.kind === "verbal") return false;
      if (kind === "verbal" && c.kind === "nominal") return false;
      if (!term) return true;
      return [c.hanzi, c.pinyin, c.usage, ...c.nouns.map((n) => `${n.zh} ${n.fr}`)].some((t) => t.toLowerCase().includes(term));
    });
    const byLevel = new Map<number, Classifier[]>();
    for (const c of visible) byLevel.set(c.level, [...(byLevel.get(c.level) ?? []), c]);
    return [...byLevel].sort(([a], [b]) => b - a);
  }, [classifiers, kind, search]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        {(
          [
            ["all", "Tous"],
            ["nominal", "Nominaux"],
            ["verbal", "Verbaux"],
          ] as [KindFilter, string][]
        ).map(([value, label]) => (
          <Button key={value} size="sm" variant={kind === value ? "default" : "outline"} onClick={() => setKind(value)}>
            {label}
          </Button>
        ))}
        <div className="relative ml-auto w-full sm:w-64">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Chercher (车, livre, zhāng…)" className="pl-9" />
        </div>
      </div>
      <p className="-mt-1 text-xs text-muted-foreground">
        Nominal : compte des choses (一本书). Verbal : compte des actions (去过两次).
      </p>

      {groups.length === 0 && <p className="text-center text-sm text-muted-foreground">Aucun classificateur ne correspond.</p>}
      {groups.map(([lv, items]) => (
        <section key={lv} className="flex flex-col gap-2">
          <h2 className="text-lg font-semibold">
            {lv === level ? `Nouveaux au HSK ${lv}` : `Vus au HSK ${lv}`}
            <span className="ml-2 text-sm font-normal text-muted-foreground">{items.length}</span>
          </h2>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((c) => (
              <FicheCard
                key={c.hanzi}
                c={c}
                level={level}
                open={open === c.hanzi}
                onToggle={() => setOpen(open === c.hanzi ? null : c.hanzi)}
                busy={busy}
                onPractice={() => onPractice(c.hanzi)}
                onWrite={() => onWrite(c.hanzi)}
                onGenerate={() => onGenerate(c.hanzi)}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function FicheCard({
  c,
  level,
  open,
  onToggle,
  busy,
  onPractice,
  onWrite,
  onGenerate,
}: {
  c: Classifier;
  level: ExerciseLevel;
  open: boolean;
  onToggle: () => void;
  busy: boolean;
  onPractice: () => void;
  onWrite: () => void;
  onGenerate: () => void;
}) {
  const [showPinyin, setShowPinyin] = useState(level < 3);
  return (
    <Card className={cn(open && "border-primary/40 sm:col-span-2 lg:col-span-3")}>
      <button type="button" onClick={onToggle} aria-expanded={open} className="flex w-full items-start gap-4 p-4 text-left">
        <span className="flex w-14 shrink-0 flex-col items-center">
          <span className="hanzi text-4xl leading-none">{c.hanzi}</span>
          <span className="mt-1 text-sm text-muted-foreground">{c.pinyin}</span>
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="text-sm">{c.usage}</span>
          <span className="flex flex-wrap gap-1 text-xs text-muted-foreground">
            <span className="rounded bg-muted px-1.5 py-0.5">HSK {c.level}</span>
            <span className="rounded bg-muted px-1.5 py-0.5">{KIND_LABEL[c.kind]}</span>
          </span>
        </span>
        <ChevronDown className={cn("mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <CardContent className="flex flex-col gap-4 border-t border-border pt-4">
          <p className="leading-relaxed">{c.explanation}</p>

          {c.nouns.length > 0 && (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">S&apos;emploie avec</p>
              <ul className="flex flex-wrap gap-2">
                {c.nouns.map((n) => (
                  <li
                    key={n.zh}
                    className={cn("rounded-lg border border-border px-3 py-1.5", !n.in_level && "opacity-60")}
                    title={n.in_level ? undefined : "Mot d'un niveau supérieur"}
                  >
                    <span className="hanzi text-lg">
                      一{c.hanzi}
                      {n.zh}
                    </span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {toPinyin(`一${c.hanzi}${n.zh}`)} · {n.fr}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Exemples</p>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
              <input type="checkbox" className="h-4 w-4" checked={showPinyin} onChange={(e) => setShowPinyin(e.target.checked)} />
              Pinyin
            </label>
          </div>
          <ul className="flex flex-col gap-2">
            {c.examples.map((ex) => (
              <li key={ex.zh} className="flex items-start justify-between gap-2 rounded-lg border border-border p-3">
                <div>
                  <ZhText text={ex.zh} showPinyin={showPinyin} className="text-lg" />
                  <p className="text-sm italic text-muted-foreground">{ex.fr}</p>
                </div>
                <ListenButton text={ex.zh} />
              </li>
            ))}
          </ul>

          {c.traps && (
            <div className="rounded-lg bg-amber-500/10 p-3 text-sm">
              <p className="mb-1 font-medium text-amber-800 dark:text-amber-200">Pièges</p>
              <p className="leading-relaxed">{c.traps}</p>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button onClick={onPractice} disabled={busy || c.sentence_count === 0}>
              <PenLine className="h-4 w-4" />
              S&apos;entraîner sur {c.hanzi} ({c.sentence_count} phrases)
            </Button>
            <Button variant="outline" onClick={onWrite} disabled={busy || c.sentence_count === 0}>
              <Keyboard className="h-4 w-4" />
              Sans choix
            </Button>
            <Button variant="outline" onClick={onGenerate} disabled={busy}>
              <Sparkles className="h-4 w-4" />
              Nouvelles phrases avec {c.hanzi}
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
