import { describe, expect, it } from "vitest";

import { normalizePinyin, pinyinMatches } from "@/lib/pinyin";

describe("normalizePinyin", () => {
  it("strips tone marks", () => {
    expect(normalizePinyin("nǐ hǎo")).toBe("nihao");
    expect(normalizePinyin("Běijīng")).toBe("beijing");
  });

  it("handles ü and v interchangeably", () => {
    expect(normalizePinyin("nǚ")).toBe("nv");
    expect(normalizePinyin("nü")).toBe("nv");
    expect(normalizePinyin("nv")).toBe("nv");
  });

  it("drops tone numbers and spaces", () => {
    expect(normalizePinyin("ni3 hao3")).toBe("nihao");
    expect(normalizePinyin("  Ni Hao  ")).toBe("nihao");
  });

  it("returns empty string for empty input", () => {
    expect(normalizePinyin("")).toBe("");
  });
});

describe("pinyinMatches", () => {
  it("accepts equivalent pinyin spellings", () => {
    expect(pinyinMatches("ni hao", "nǐ hǎo")).toBe(true);
    expect(pinyinMatches("ni3 hao3", "nǐ hǎo")).toBe(true);
    expect(pinyinMatches("NIHAO", "nǐ hǎo")).toBe(true);
  });

  it("rejects mismatched syllables", () => {
    expect(pinyinMatches("ni hao ma", "nǐ hǎo")).toBe(false);
    expect(pinyinMatches("ne hao", "nǐ hǎo")).toBe(false);
  });

  it("rejects empty input", () => {
    expect(pinyinMatches("", "nǐ hǎo")).toBe(false);
    expect(pinyinMatches("   ", "nǐ hǎo")).toBe(false);
  });
});
