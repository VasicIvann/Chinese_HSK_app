import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import {
  markTone,
  normalizePlain,
  samePlain,
  sandhiNotes,
  splitWord,
  stripTone,
  toneOf,
  toToneWord,
  typedTone,
} from "@/lib/tones";

function listWords(folder: string, levels: number[]) {
  const out: { hanzi: string; pinyin: string }[] = [];
  for (const lv of levels) {
    const text = readFileSync(join(__dirname, "..", "..", "backend", "data", folder, `hsk${lv}.csv`), "utf-8").replace(/^﻿/, "");
    for (const line of text.split("\n").slice(1)) {
      const [hanzi, pinyin] = line.split(",");
      if (hanzi && pinyin) out.push({ hanzi: hanzi.replace(/\d+$/, ""), pinyin });
    }
  }
  return out;
}

describe("tones of a syllable", () => {
  it("reads, strips and places tone marks", () => {
    expect([toneOf("mā"), toneOf("má"), toneOf("mǎ"), toneOf("mà"), toneOf("ma")]).toEqual([1, 2, 3, 4, 5]);
    expect(toneOf("lǜ")).toBe(4);
    expect(stripTone("lǜ")).toBe("lü");
    expect(stripTone("xué")).toBe("xue");
    expect(markTone("hao", 3)).toBe("hǎo");
    expect(markTone("gou", 3)).toBe("gǒu");
    expect(markTone("xue", 2)).toBe("xué");
    expect(markTone("dui", 4)).toBe("duì");
    expect(markTone("liu", 2)).toBe("liú");
    expect(markTone("lü", 4)).toBe("lǜ");
    expect(markTone("de", 5)).toBe("de");
  });

  it("normalizes what the learner types", () => {
    expect(normalizePlain(" Lv ")).toBe("lü");
    expect(normalizePlain("lu:")).toBe("lü");
    expect(normalizePlain("xue2")).toBe("xue");
    expect(normalizePlain("xué")).toBe("xue");
    expect(samePlain("lv", "lü")).toBe(true);
    expect(samePlain("lu", "lü")).toBe(false);
    expect(samePlain("xü", "xu")).toBe(true); // ü written u after x
    expect(typedTone("xue2")).toBe(2);
    expect(typedTone("xué")).toBe(2);
    expect(typedTone("xue")).toBeNull();
  });
});

describe("splitting HSK words", () => {
  it("aligns the list's pinyin with the characters, neutral tones included", () => {
    expect(splitWord("学习", "xuéxí")?.map((s) => [s.hanzi, s.pinyin, s.tone])).toEqual([
      ["学", "xué", 2],
      ["习", "xí", 2],
    ]);
    expect(splitWord("那个", "nàge")?.map((s) => s.tone)).toEqual([4, 5]);
    expect(splitWord("左边", "zuǒbian")?.map((s) => s.pinyin)).toEqual(["zuǒ", "bian"]);
    expect(splitWord("北京", "běi jīng")?.map((s) => s.pinyin)).toEqual(["běi", "jīng"]);
    expect(splitWord("女儿", "nǚ'ér")?.map((s) => s.pinyin)).toEqual(["nǚ", "ér"]);
    expect(splitWord("小孩儿", "xiǎoháir")?.map((s) => [s.hanzi, s.pinyin, s.tone])).toEqual([
      ["小", "xiǎo", 3],
      ["孩儿", "háir", 2],
    ]);
    expect(splitWord("谁", "shéi/shuí")?.map((s) => s.pinyin)).toEqual(["shéi"]);
    expect(splitWord("了", "le")?.map((s) => s.tone)).toEqual([5]);
    expect(splitWord("ABC", "abc")).toBeNull();
  });

  it.each([
    ["hsk3", "3.0"],
    ["hsk2", "2.0"],
  ])("keeps almost every word of the %s lists (HSK 1-3)", (folder) => {
    const words = listWords(folder, [1, 2, 3]);
    const kept = words.filter((w) => splitWord(w.hanzi, w.pinyin));
    const lost = words.filter((w) => !splitWord(w.hanzi, w.pinyin));
    expect(kept.length / words.length, `${lost.length} perdus : ${lost.slice(0, 40).map((w) => `${w.hanzi} ${w.pinyin}`).join(", ")}`).toBeGreaterThan(0.995);
  });
});

describe("dictation words", () => {
  it("keeps out characters a voice would read another way", () => {
    const w = (hanzi: string, pinyin: string) => toToneWord({ id: 1, hanzi, pinyin, translation: "" })!;
    expect(w("学习", "xuéxí").audioSafe).toBe(true);
    expect(w("爸爸", "bàba").audioSafe).toBe(true);
    expect(w("一点儿", "yìdiǎnr").audioSafe).toBe(true);
    expect(w("长", "zhǎng").audioSafe).toBe(false);
    expect(w("还", "huán").audioSafe).toBe(false);
  });
});

describe("sandhi notes", () => {
  const word = (hanzi: string, pinyin: string) => toToneWord({ id: 1, hanzi, pinyin, translation: "" })!;

  it("explains 3rd + 3rd, 一 and 不", () => {
    expect(sandhiNotes(word("你好", "nǐhǎo"))[0]).toContain("on entend « ní hǎo »");
    expect(sandhiNotes(word("一起", "yìqǐ"))[0]).toContain("一 change de ton");
    expect(sandhiNotes(word("不是", "búshì"))[0]).toContain("不 se prononce bú");
    expect(sandhiNotes(word("学习", "xuéxí"))).toEqual([]);
  });
});
