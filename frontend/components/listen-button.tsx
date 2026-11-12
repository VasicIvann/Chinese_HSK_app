"use client";

import { Volume2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useChineseSpeech } from "@/lib/speech";
import { cn } from "@/lib/utils";

type Props = {
  /** Chinese text to read (hanzi). */
  text: string;
  /** Visible label; omit for an icon-only button. */
  label?: string;
  /** Speech rate, 1 = normal. */
  rate?: number;
  className?: string;
};

/** "Écouter" button: reads Chinese text with the device's voice. Click again to stop. */
export function ListenButton({ text, label, rate, className }: Props) {
  const { speak, stop, speakingKey } = useChineseSpeech();
  const playing = speakingKey === text;

  const onClick = () => {
    if (playing) {
      stop();
      return;
    }
    const error = speak(text, { key: text, rate });
    if (error) toast.error(error);
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size={label ? "sm" : "icon"}
      onClick={onClick}
      aria-label={label ? undefined : `Écouter ${text}`}
      aria-pressed={playing}
      className={cn("text-muted-foreground", playing && "text-primary", className)}
    >
      <Volume2 className={cn("h-4 w-4", label && "mr-1", playing && "animate-pulse")} />
      {label}
    </Button>
  );
}
