"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import type { RatingEnum } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const RATING_BUTTONS: { rating: RatingEnum; label: string; key: string; tone: string }[] = [
  { rating: "again", label: "Faux", key: "1", tone: "border-destructive/40 hover:bg-destructive/10 text-destructive" },
  { rating: "hard", label: "Difficile", key: "2", tone: "border-amber-500/40 hover:bg-amber-500/10 text-amber-600 dark:text-amber-400" },
  { rating: "good", label: "Juste", key: "3", tone: "border-emerald-500/40 hover:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" },
  { rating: "easy", label: "Je connais", key: "4", tone: "border-sky-500/40 hover:bg-sky-500/10 text-sky-600 dark:text-sky-400" },
];

export function RatingButtons({
  onRate,
  disabled,
  enableShortcuts = true,
}: {
  onRate: (rating: RatingEnum) => void;
  disabled?: boolean;
  enableShortcuts?: boolean;
}) {
  useEffect(() => {
    if (!enableShortcuts || disabled) return;
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
        return;
      }
      const match = RATING_BUTTONS.find((b) => b.key === event.key);
      if (match) {
        event.preventDefault();
        onRate(match.rating);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onRate, disabled, enableShortcuts]);

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
      {RATING_BUTTONS.map((btn) => (
        <Button
          key={btn.rating}
          type="button"
          variant="outline"
          size="xl"
          disabled={disabled}
          onClick={() => onRate(btn.rating)}
          className={cn(
            "flex h-16 flex-col items-center justify-center gap-0.5 text-base font-semibold sm:h-20",
            btn.tone
          )}
        >
          <span>{btn.label}</span>
          {enableShortcuts && (
            <span className="text-xs font-normal opacity-60">[{btn.key}]</span>
          )}
        </Button>
      ))}
    </div>
  );
}
