"use client";

import { HSK_VERSIONS, VERSION_INFO, useHskVersion } from "@/lib/hsk-version";
import { cn } from "@/lib/utils";

/**
 * HSK 2.0 / HSK 3.0 switch. Saved on the account; it only changes which level
 * each word is listed under — progress on every word is kept.
 */
export function HskVersionToggle({ className }: { className?: string }) {
  const { version, setVersion, isLoading } = useHskVersion();

  return (
    <div
      role="radiogroup"
      aria-label="Version du test HSK"
      className={cn("inline-flex shrink-0 rounded-lg border border-input bg-background p-1", className)}
    >
      {HSK_VERSIONS.map((v) => {
        const active = v === version;
        return (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={active}
            title={VERSION_INFO[v].hint}
            disabled={isLoading}
            onClick={() => setVersion(v)}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50",
              active ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:bg-accent hover:text-foreground"
            )}
          >
            {VERSION_INFO[v].label}
          </button>
        );
      })}
    </div>
  );
}
