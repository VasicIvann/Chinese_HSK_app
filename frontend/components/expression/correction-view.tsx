"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, RefreshCw, Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CorrectionPayload } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type Props = {
  isStreaming: boolean;
  tokensReceived: number;
  correction: CorrectionPayload | null;
  relearnedCount: number;
};

const ERROR_TONE: Record<string, string> = {
  grammaire: "bg-red-500/10 text-red-700 dark:text-red-300",
  vocabulaire: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
  tons: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  orthographe: "bg-purple-500/10 text-purple-700 dark:text-purple-300",
  structure: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
};

export function CorrectionView({ isStreaming, tokensReceived, correction, relearnedCount }: Props) {
  if (!isStreaming && !correction) return null;

  return (
    <AnimatePresence mode="wait">
      {isStreaming && !correction && (
        <motion.div
          key="streaming"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="font-medium">Claude analyse ta production…</p>
              <p className="text-xs text-muted-foreground">
                {tokensReceived} tokens reçus
              </p>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {correction && (
        <motion.div
          key="result"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col gap-4"
        >
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Correction
                </CardTitle>
                {typeof correction.score === "number" && (
                  <div className="text-right">
                    <p className="text-3xl font-semibold text-primary">{correction.score}</p>
                    <p className="text-xs text-muted-foreground">/ 100</p>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              {correction.corrected_version && (
                <section>
                  <p className="text-sm font-medium text-muted-foreground">Version corrigée</p>
                  <p className="hanzi mt-1 text-2xl leading-relaxed">{correction.corrected_version}</p>
                  {correction.pinyin && (
                    <p className="mt-1 text-sm text-muted-foreground">{correction.pinyin}</p>
                  )}
                  {correction.french_translation && (
                    <p className="mt-1 text-sm italic text-muted-foreground">
                      « {correction.french_translation} »
                    </p>
                  )}
                </section>
              )}

              {relearnedCount > 0 && (
                <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                  <RefreshCw className="h-4 w-4" />
                  <span>
                    {relearnedCount} mot{relearnedCount > 1 ? "s" : ""} ré-injecté
                    {relearnedCount > 1 ? "s" : ""} dans ta file de révision SRS.
                  </span>
                </div>
              )}

              {correction.errors.length > 0 ? (
                <section>
                  <p className="text-sm font-medium text-muted-foreground">
                    Erreurs détectées ({correction.errors.length})
                  </p>
                  <ul className="mt-2 space-y-2">
                    {correction.errors.map((err, idx) => (
                      <li
                        key={`${err.segment}-${idx}`}
                        className="rounded-lg border border-border p-3"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-xs font-medium uppercase",
                              ERROR_TONE[err.type] || "bg-muted text-muted-foreground"
                            )}
                          >
                            {err.type}
                          </span>
                          <span className="hanzi text-base font-medium">{err.segment}</span>
                          <span className="text-muted-foreground">→</span>
                          <span className="hanzi text-base font-medium text-primary">
                            {err.correction}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{err.explanation}</p>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : (
                <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Aucune erreur détectée. Belle production.</span>
                </div>
              )}

              {correction.strengths.length > 0 && (
                <section>
                  <p className="text-sm font-medium text-muted-foreground">Points forts</p>
                  <ul className="mt-2 space-y-1 text-sm">
                    {correction.strengths.map((s, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-primary">▸</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {correction.next_step_advice && (
                <section className="rounded-lg border-l-4 border-primary bg-accent/30 px-4 py-3">
                  <p className="text-sm font-medium">Conseil pour progresser</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {correction.next_step_advice}
                  </p>
                </section>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
