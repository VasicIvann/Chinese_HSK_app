"use client";

import { useState } from "react";

import type { ExerciseLevel } from "@/lib/api/exercises";
import { cn } from "@/lib/utils";

const KEY = "hsk.exercise-level";
const LEVELS: ExerciseLevel[] = [1, 2, 3];

function readLevel(): ExerciseLevel {
  try {
    const value = Number(window.localStorage.getItem(KEY));
    return (LEVELS as number[]).includes(value) ? (value as ExerciseLevel) : 1;
  } catch {
    return 1;
  }
}

/** Level shared by the Écoute / Écriture / Grammaire tabs (remembered on this device). */
export function useExerciseLevel(): [ExerciseLevel, (level: ExerciseLevel) => void] {
  const [level, setLevelState] = useState<ExerciseLevel>(() => (typeof window === "undefined" ? 1 : readLevel()));
  const setLevel = (next: ExerciseLevel) => {
    setLevelState(next);
    try {
      window.localStorage.setItem(KEY, String(next));
    } catch {
      // private mode: the choice just isn't remembered
    }
  };
  return [level, setLevel];
}

export function LevelPicker({ level, onChange }: { level: ExerciseLevel; onChange: (level: ExerciseLevel) => void }) {
  return (
    <div role="radiogroup" aria-label="Niveau HSK" className="flex gap-2">
      {LEVELS.map((lv) => (
        <button
          key={lv}
          type="button"
          role="radio"
          aria-checked={lv === level}
          onClick={() => onChange(lv)}
          className={cn(
            "h-11 rounded-md border px-5 text-sm font-medium transition-colors",
            lv === level ? "border-primary bg-primary text-primary-foreground shadow" : "border-input hover:bg-accent"
          )}
        >
          HSK {lv}
        </button>
      ))}
    </div>
  );
}
