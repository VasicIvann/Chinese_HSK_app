"use client";

import { Headphones, RotateCcw, Square } from "lucide-react";
import { useEffect, useRef } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import type { AudioLine } from "@/lib/api/exercises";
import { useScriptPlayer } from "@/lib/speech";
import { cn } from "@/lib/utils";

/**
 * The recording of one question. Like the real paper, it plays twice on its own
 * when the question appears; "Réécouter" plays it once more.
 */
export function AudioPanel({ script, autoPlay = true, className }: { script: AudioLine[]; autoPlay?: boolean; className?: string }) {
  const { play, stop, playing, supported } = useScriptPlayer();
  const started = useRef(false);

  useEffect(() => {
    if (!autoPlay || started.current) return;
    started.current = true;
    // Let the voices load (first question of a set) before speaking.
    const timer = window.setTimeout(() => {
      const error = play(script, { times: 2 });
      if (error) toast.error(error);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [autoPlay, play, script]);

  const replay = () => {
    const error = play(script, { times: 1 });
    if (error) toast.error(error);
  };

  return (
    <div className={cn("flex flex-col items-center gap-3 rounded-xl border border-border bg-card px-4 py-6", className)}>
      <div
        className={cn(
          "flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform",
          playing && "animate-pulse"
        )}
        aria-hidden
      >
        <Headphones className="h-7 w-7" />
      </div>
      <p className="text-sm text-muted-foreground" aria-live="polite">
        {!supported ? "Audio indisponible dans ce navigateur." : playing ? "Écoute…" : "Écoute l'enregistrement (lu deux fois)."}
      </p>
      {playing ? (
        <Button type="button" variant="outline" size="sm" onClick={stop}>
          <Square className="h-4 w-4" />
          Arrêter
        </Button>
      ) : (
        <Button type="button" variant="outline" size="sm" onClick={replay} disabled={!supported}>
          <RotateCcw className="h-4 w-4" />
          Réécouter
        </Button>
      )}
    </div>
  );
}
