"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ChevronDown, ChevronUp, History } from "lucide-react";
import { useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getAttempts } from "@/lib/api/endpoints";
import type { ExpressionAttemptItem } from "@/lib/api/types";

export function AttemptsList({ limit = 5 }: { limit?: number }) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ["expression-attempts", limit],
    queryFn: () => getAttempts(limit),
  });

  if (query.isLoading) {
    return <Skeleton className="h-32 w-full" />;
  }

  if (!query.data || query.data.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5 text-primary" />
          Dernières productions
        </CardTitle>
        <CardDescription>
          Tes {Math.min(limit, query.data.length)} dernières corrections.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {query.data.map((attempt: ExpressionAttemptItem) => {
          const isOpen = expandedId === attempt.id;
          return (
            <div key={attempt.id} className="rounded-lg border border-border">
              <button
                type="button"
                onClick={() => setExpandedId(isOpen ? null : attempt.id)}
                className="flex w-full items-center justify-between gap-3 p-3 text-left hover:bg-accent/30"
              >
                <div className="flex flex-1 items-center gap-3 min-w-0">
                  <span className="rounded-md bg-muted px-2 py-1 text-xs font-semibold">
                    HSK{attempt.hsk_level}
                  </span>
                  <span className="font-semibold text-primary tabular-nums">
                    {attempt.score ?? "?"}/100
                  </span>
                  <span className="flex-1 truncate text-sm text-muted-foreground">
                    {attempt.subject}
                  </span>
                </div>
                {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
              {isOpen && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="border-t border-border p-3 text-sm"
                >
                  <p className="text-xs text-muted-foreground">Ta production</p>
                  <p className="hanzi mt-1 text-base">{attempt.user_text}</p>
                  {attempt.correction.corrected_version && (
                    <>
                      <p className="mt-3 text-xs text-muted-foreground">Version corrigée</p>
                      <p className="hanzi mt-1 text-base">{attempt.correction.corrected_version}</p>
                    </>
                  )}
                  <p className="mt-3 text-xs text-muted-foreground">
                    {new Date(attempt.created_at).toLocaleString("fr-FR")}
                    {" · "}
                    {attempt.tokens_input + attempt.tokens_output} tokens
                  </p>
                </motion.div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
