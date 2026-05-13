"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { AttemptsList } from "@/components/expression/attempts-list";
import { CorrectionView } from "@/components/expression/correction-view";
import { SubjectPicker } from "@/components/expression/subject-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { expressionCorrectUrl, getQuota } from "@/lib/api/endpoints";
import { streamSse } from "@/lib/api/sse";
import type { CorrectionPayload } from "@/lib/api/types";
import { getStoredToken } from "@/lib/auth/storage";

const HANZI_REGEX = /[一-鿿]/;

const LEVEL_GUIDANCE = {
  1: "1 à 2 phrases courtes",
  2: "2 à 4 phrases",
  3: "Petit paragraphe de 4 à 7 phrases",
} as const;

type Phase = "idle" | "streaming" | "complete" | "error";

export default function ExpressionPage() {
  const queryClient = useQueryClient();
  const [level, setLevel] = useState<1 | 2 | 3>(2);
  const [subject, setSubject] = useState<{ subject: string; keywords: string[] } | null>(null);
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [tokensReceived, setTokensReceived] = useState(0);
  const [correction, setCorrection] = useState<CorrectionPayload | null>(null);
  const [relearned, setRelearned] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const quotaQuery = useQuery({
    queryKey: ["expression-quota"],
    queryFn: getQuota,
  });

  const remainingCorrections = quotaQuery.data?.correction.remaining ?? 20;

  const submit = useCallback(() => {
    if (!subject) {
      toast.error("Choisis un sujet d'abord.");
      return;
    }
    if (!HANZI_REGEX.test(text)) {
      toast.error("Le texte doit contenir des caractères chinois.");
      return;
    }
    if (remainingCorrections <= 0) {
      toast.error("Quota quotidien atteint. Réessaie demain.");
      return;
    }

    const token = getStoredToken();
    if (!token) {
      toast.error("Tu n'es plus connecté. Reconnecte-toi.");
      return;
    }

    setPhase("streaming");
    setTokensReceived(0);
    setCorrection(null);
    setRelearned(0);
    const controller = new AbortController();
    abortRef.current = controller;

    streamSse<{ delta?: string; correction?: CorrectionPayload; usage?: { input_tokens: number; output_tokens: number }; attempt_id?: number; relearned_count?: number; message?: string }>(
      expressionCorrectUrl(),
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          level,
          subject: subject.subject,
          user_text: text,
        }),
      },
      {
        signal: controller.signal,
        onEvent: ({ event, data }) => {
          if (event === "partial" && data.delta) {
            setTokensReceived((n) => n + 1);
          } else if (event === "complete" && data.correction) {
            setCorrection(data.correction);
          } else if (event === "persisted") {
            setRelearned(data.relearned_count ?? 0);
            setPhase("complete");
            queryClient.invalidateQueries({ queryKey: ["expression-attempts"] });
            queryClient.invalidateQueries({ queryKey: ["expression-quota"] });
            queryClient.invalidateQueries({ queryKey: ["account-overview"] });
            queryClient.invalidateQueries({ queryKey: ["srs-stats"] });
          } else if (event === "error") {
            toast.error(data.message ?? "Erreur Claude");
            setPhase("error");
          }
        },
        onError: (err) => {
          toast.error(`Stream interrompu : ${err.message}`);
          setPhase("error");
        },
      }
    );
  }, [subject, text, remainingCorrections, level, queryClient]);

  const charCount = text.length;
  const maxChars = level === 1 ? 200 : level === 2 ? 400 : 700;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Expression écrite
        </h1>
        <p className="mt-1 text-muted-foreground">
          Rédige en chinois, Claude corrige et alimente ta file SRS.
        </p>
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <div className="rounded-lg border border-border bg-card px-3 py-2">
          Quota corrections : <strong>{remainingCorrections}/20</strong>
        </div>
        <div className="rounded-lg border border-border bg-card px-3 py-2">
          Quota générations : <strong>{quotaQuery.data?.subject_generation.remaining ?? 50}/50</strong>
        </div>
      </div>

      <SubjectPicker
        level={level}
        onLevelChange={setLevel}
        selectedSubject={subject}
        onSelectSubject={setSubject}
      />

      <Card>
        <CardHeader>
          <CardTitle>Ta production</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Label htmlFor="expression-text" className="text-sm text-muted-foreground">
            {LEVEL_GUIDANCE[level]} en chinois (max {maxChars} caractères).
          </Label>
          <textarea
            id="expression-text"
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, maxChars))}
            disabled={phase === "streaming"}
            placeholder="例如 : 我今天很高兴…"
            lang="zh"
            inputMode="text"
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
            className="hanzi flex min-h-32 w-full rounded-md border border-input bg-background px-3 py-2 text-lg shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {charCount} / {maxChars} caractères
            </span>
            {HANZI_REGEX.test(text) ? (
              <span className="text-emerald-600 dark:text-emerald-400">✓ Caractères chinois détectés</span>
            ) : (
              <span>Tape en pinyin, l&apos;IME du système convertira en hanzi.</span>
            )}
          </div>
          <Button
            type="button"
            size="xl"
            className="w-full"
            disabled={phase === "streaming" || !subject || !HANZI_REGEX.test(text)}
            onClick={submit}
          >
            <Send className="h-4 w-4" />
            {phase === "streaming" ? "Analyse en cours…" : "Demander la correction"}
          </Button>
        </CardContent>
      </Card>

      <CorrectionView
        isStreaming={phase === "streaming"}
        tokensReceived={tokensReceived}
        correction={correction}
        relearnedCount={relearned}
      />

      <AttemptsList limit={5} />
    </div>
  );
}
