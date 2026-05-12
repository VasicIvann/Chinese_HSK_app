"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <Button variant="ghost" size="icon" aria-label="Theme" disabled />;
  }

  const next = theme === "dark" ? "system" : theme === "light" ? "dark" : "light";
  const Icon =
    theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  const label =
    theme === "dark"
      ? "Mode sombre"
      : theme === "light"
        ? "Mode clair"
        : "Mode système";

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={`Changer le thème (actuel : ${label})`}
      title={label}
      onClick={() => setTheme(next)}
    >
      <Icon className="h-5 w-5" />
    </Button>
  );
}
