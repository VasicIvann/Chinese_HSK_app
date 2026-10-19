"use client";

import { pinyin } from "pinyin-pro";
import { Fragment, useMemo } from "react";

import { cn } from "@/lib/utils";

// 儿 is a full syllable (ér) only in these words; elsewhere it is the erhua suffix: 这儿 zhèr.
const FULL_ER = ["儿子", "女儿", "儿童", "婴儿", "幼儿", "孤儿", "健儿", "儿女", "儿科", "男儿"];

type Syllable = { origin: string; pinyin: string; isZh: boolean };

function syllables(text: string): Syllable[] {
  const parts = pinyin(text, { type: "all", toneSandhi: true }) as Syllable[];
  return parts.map((p, i) => {
    if (p.origin !== "儿" || i === 0 || !parts[i - 1].isZh) return p;
    const around = text.slice(Math.max(0, i - 1), i + 2);
    return FULL_ER.some((w) => around.includes(w)) ? p : { ...p, pinyin: "r" };
  });
}

/** Pinyin of a whole string, tone sandhi of 一 / 不 applied like in the HSK papers. */
export function toPinyin(text: string): string {
  return syllables(text)
    .map((p, i, all) => (p.isZh ? (p.pinyin === "r" ? p.pinyin : (i > 0 && all[i - 1].isZh ? " " : "") + p.pinyin) : p.origin))
    .join("")
    .trim();
}

/**
 * Chinese text, optionally with pinyin above each character (as printed on the
 * HSK 1–2 papers). Pinyin comes from pinyin-pro (context-aware for most polyphones).
 */
export function ZhText({ text, showPinyin, className }: { text: string; showPinyin: boolean; className?: string }) {
  const parts = useMemo(() => (showPinyin ? syllables(text) : null), [text, showPinyin]);
  if (!parts) return <span className={cn("hanzi", className)}>{text}</span>;
  return (
    <span className={cn("hanzi leading-[2.4]", className)}>
      {parts.map((p, i) =>
        p.isZh ? (
          <ruby key={i} className="mx-[0.04em]">
            {p.origin}
            <rt className="font-sans text-[0.55em] font-normal tracking-normal text-muted-foreground">{p.pinyin}</rt>
          </ruby>
        ) : (
          <Fragment key={i}>{p.origin}</Fragment>
        )
      )}
    </span>
  );
}
