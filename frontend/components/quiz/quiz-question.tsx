"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Eye, EyeOff, Lightbulb } from "lucide-react";
import { useEffect, useState } from "react";

import { RatingButtons } from "@/components/quiz/rating-buttons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { DueEntry, RatingEnum } from "@/lib/api/types";
import type { QuizMode } from "@/lib/hooks/use-quiz-session";
import { pinyinMatches } from "@/lib/pinyin";

type Props = {
  entry: DueEntry;
  mode: QuizMode;
  onRate: (rating: RatingEnum, meta?: { userInput?: string; inputCorrect?: boolean }) => void;
};

export function QuizQuestion({ entry, mode, onRate }: Props) {
  const [pinyinHintVisible, setPinyinHintVisible] = useState(false);
  const [hintVisible, setHintVisible] = useState(false);
  const [pinyinInput, setPinyinInput] = useState("");
  const [pinyinChecked, setPinyinChecked] = useState<null | { correct: boolean; value: string }>(null);

  // Reset transient state when the question changes.
  useEffect(() => {
    setPinyinHintVisible(false);
    setHintVisible(false);
    setPinyinInput("");
    setPinyinChecked(null);
  }, [entry.id]);

  const handleCheck = () => {
    const correct = pinyinMatches(pinyinInput, entry.pinyin);
    setPinyinChecked({ correct, value: pinyinInput });
    setHintVisible(true);
  };

  const handleAutoRate = (rating: RatingEnum) => {
    if (mode === "pinyin-input" && pinyinChecked) {
      onRate(rating, { userInput: pinyinChecked.value, inputCorrect: pinyinChecked.correct });
    } else {
      onRate(rating);
    }
  };

  // In auto-assess mode, "show full solution" implies pinyin is also revealed.
  const showPinyin = pinyinHintVisible || hintVisible;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={entry.id}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className="flex flex-col items-center gap-6"
      >
        <div className="flex flex-col items-center gap-2">
          <p className="hanzi text-6xl font-semibold tracking-wide sm:text-7xl">{entry.hanzi}</p>
          <p className="text-sm text-muted-foreground">
            {mode === "auto-assess" ? "Auto-évaluation" : "Tape le pinyin"}
          </p>
        </div>

        {mode === "pinyin-input" && (
          <div className="w-full max-w-md">
            <div className="flex items-center gap-2">
              <Input
                value={pinyinInput}
                onChange={(e) => setPinyinInput(e.target.value)}
                placeholder="Ex. : ni hao"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !pinyinChecked) {
                    e.preventDefault();
                    handleCheck();
                  }
                }}
                autoFocus
                disabled={!!pinyinChecked}
                inputMode="text"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
              />
              <Button
                type="button"
                onClick={handleCheck}
                disabled={!pinyinInput.trim() || !!pinyinChecked}
              >
                Vérifier
              </Button>
            </div>
            {pinyinChecked && (
              <p
                className={`mt-2 text-sm font-medium ${
                  pinyinChecked.correct ? "text-emerald-600 dark:text-emerald-400" : "text-destructive"
                }`}
              >
                {pinyinChecked.correct
                  ? "Bonne réponse !"
                  : `Pinyin attendu : ${entry.pinyin}`}
              </p>
            )}
          </div>
        )}

        <div className="flex flex-col items-center gap-3">
          {mode === "auto-assess" ? (
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setPinyinHintVisible((v) => !v)}
                disabled={hintVisible}
                className="text-muted-foreground"
              >
                <Lightbulb className="mr-1 h-4 w-4" />
                {pinyinHintVisible || hintVisible ? "Pinyin affiché" : "Indice pinyin"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setHintVisible((v) => !v)}
                className="text-muted-foreground"
              >
                {hintVisible ? <EyeOff className="mr-1 h-4 w-4" /> : <Eye className="mr-1 h-4 w-4" />}
                {hintVisible ? "Masquer la solution" : "Afficher la solution"}
              </Button>
            </div>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setHintVisible((v) => !v)}
              className="text-muted-foreground"
            >
              {hintVisible ? <EyeOff className="mr-1 h-4 w-4" /> : <Eye className="mr-1 h-4 w-4" />}
              {hintVisible ? "Masquer la solution" : "Afficher la solution"}
            </Button>
          )}

          {(showPinyin || hintVisible) && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.15 }}
              className="text-center"
            >
              {showPinyin && (
                <p className="text-lg font-medium">{entry.pinyin}</p>
              )}
              {hintVisible && (
                <>
                  <p className="text-base text-muted-foreground">{entry.translation}</p>
                  {entry.alt_translations && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {entry.alt_translations}
                    </p>
                  )}
                </>
              )}
            </motion.div>
          )}
        </div>

        <div className="w-full pt-2">
          <p className="mb-2 text-center text-sm text-muted-foreground">
            Comment t&apos;as senti sur ce mot ?
          </p>
          <RatingButtons onRate={handleAutoRate} />
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
