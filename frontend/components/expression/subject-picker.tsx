"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Pencil, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { getSubjects, postGenerateSubject } from "@/lib/api/endpoints";
import type { SubjectItem } from "@/lib/api/types";

type Props = {
  level: 1 | 2 | 3;
  onLevelChange: (level: 1 | 2 | 3) => void;
  selectedSubject: { subject: string; keywords: string[] } | null;
  onSelectSubject: (subject: { subject: string; keywords: string[] }) => void;
};

export function SubjectPicker({ level, onLevelChange, selectedSubject, onSelectSubject }: Props) {
  const queryClient = useQueryClient();
  const [customSubject, setCustomSubject] = useState("");

  const subjectsQuery = useQuery({
    queryKey: ["subjects", level],
    queryFn: () => getSubjects(level),
  });

  const generateMutation = useMutation({
    mutationFn: () => postGenerateSubject(level),
    onSuccess: (payload) => {
      onSelectSubject({ subject: payload.subject, keywords: payload.keywords });
      toast.success("Nouveau sujet généré", {
        description: `Quota restant : ${payload.quota_remaining}`,
      });
      queryClient.invalidateQueries({ queryKey: ["expression-quota"] });
    },
    onError: (error: unknown) => {
      const detail = error instanceof ApiError ? error.detail : "Erreur réseau";
      toast.error(`Génération impossible : ${detail}`);
    },
  });

  const handleCustomSubmit = () => {
    const trimmed = customSubject.trim();
    if (trimmed.length < 3) return;
    onSelectSubject({ subject: trimmed, keywords: [] });
    setCustomSubject("");
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sujet</CardTitle>
        <CardDescription>
          Choisis un sujet curaté, fais-en générer un nouveau ou écris le tien.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div>
          <Label className="mb-2 block">Niveau HSK</Label>
          <div className="flex gap-2">
            {([1, 2, 3] as const).map((l) => (
              <Button
                key={l}
                type="button"
                variant={level === l ? "default" : "outline"}
                size="sm"
                onClick={() => onLevelChange(l)}
              >
                HSK {l}
              </Button>
            ))}
          </div>
        </div>

        <div>
          <Label className="mb-2 block">Pool curaté</Label>
          {subjectsQuery.isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {subjectsQuery.data?.map((item: SubjectItem) => {
                const isActive = selectedSubject?.subject === item.subject;
                return (
                  <button
                    key={item.subject}
                    type="button"
                    onClick={() => onSelectSubject(item)}
                    className={`rounded-lg border-2 p-3 text-left text-sm transition-colors ${
                      isActive
                        ? "border-primary bg-accent/50"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    {item.subject}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2 border-t border-border pt-5 sm:flex-row sm:gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="sm:flex-1"
          >
            <Sparkles className="h-4 w-4" />
            {generateMutation.isPending ? "Génération…" : "Générer un nouveau sujet"}
          </Button>
          <div className="flex flex-1 gap-2">
            <Input
              value={customSubject}
              onChange={(e) => setCustomSubject(e.target.value)}
              placeholder="Ou tape ton propre sujet…"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleCustomSubmit();
                }
              }}
            />
            <Button
              type="button"
              variant="ghost"
              onClick={handleCustomSubmit}
              disabled={customSubject.trim().length < 3}
            >
              <Pencil className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {selectedSubject && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg bg-accent/40 p-4"
          >
            <p className="text-sm text-muted-foreground">Sujet retenu :</p>
            <p className="mt-1 font-medium">{selectedSubject.subject}</p>
            {selectedSubject.keywords.length > 0 && (
              <p className="mt-2 text-sm text-muted-foreground">
                Mots-clés HSK : {selectedSubject.keywords.join(", ")}
              </p>
            )}
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
}
