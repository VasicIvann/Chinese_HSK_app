/**
 * Tones of HSK words, one syllable per character.
 *
 * The expected answer is the pinyin of the HSK list (the one shown everywhere in the app).
 * pinyin-pro only tells where each character's syllable starts in that pinyin; words whose
 * pinyin cannot be split that way (儿 suffix, alternatives like "shéi/shuí") are left out.
 */

import { pinyin } from "pinyin-pro";

export type Tone = 1 | 2 | 3 | 4 | 5; // 5 = neutral tone (no mark)
export const TONES: Tone[] = [1, 2, 3, 4, 5];

export type Syllable = {
  hanzi: string;
  /** As in the HSK list, with its tone mark: "xué". */
  pinyin: string;
  /** Without tone mark, ü kept: "xue", "lü". */
  plain: string;
  tone: Tone;
};

export type ToneWord = {
  id: number;
  hanzi: string;
  pinyin: string;
  translation: string;
  syllables: Syllable[];
  /**
   * The usual reading of the characters is the one of the list, so a speech voice reads the
   * word as expected (长 zhǎng, 还 huán, 得 děi would be read cháng, hái, de: kept out of dictation).
   */
  audioSafe: boolean;
};

// Combining marks of the four tones (NFD): macron, acute, caron, grave.
const MARKS: Record<string, Tone> = { "̄": 1, "́": 2, "̌": 3, "̀": 4 };
const MARK_OF: Record<number, string> = { 1: "̄", 2: "́", 3: "̌", 4: "̀" };
const HAN = /^[㐀-鿿]+$/;

export function toneOf(syllable: string): Tone {
  for (const ch of syllable.normalize("NFD")) if (MARKS[ch]) return MARKS[ch];
  return 5;
}

/** "xué" → "xue", "lǜ" → "lü". */
export function stripTone(syllable: string): string {
  return [...syllable.normalize("NFD")]
    .filter((ch) => !MARKS[ch])
    .join("")
    .normalize("NFC");
}

/** Put the tone mark where pinyin puts it: on a / e, on the o of "ou", else on the last vowel. */
export function markTone(plain: string, tone: Tone): string {
  if (tone === 5) return plain;
  const lower = plain.toLowerCase();
  let at = lower.search(/[ae]/);
  if (at < 0) at = lower.indexOf("ou");
  if (at < 0) {
    const vowels = [...lower.matchAll(/[iouü]/g)];
    at = vowels.length ? vowels[vowels.length - 1].index! : -1;
  }
  if (at < 0) return plain;
  return (plain.slice(0, at + 1) + MARK_OF[tone] + plain.slice(at + 1)).normalize("NFC");
}

/** Split the list's pinyin into one syllable per character, or null if it cannot be done safely. */
export function splitWord(hanzi: string, listPinyin: string): Syllable[] | null {
  if (!HAN.test(hanzi)) return null;
  // "shéi/shuí": the first form, as the list shows it first.
  const target = listPinyin.split("/")[0].normalize("NFC").toLowerCase().replace(/[\s'’·-]/g, "");
  if (!target || /[^a-zāáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜ]/.test(target)) return null;
  // One character: its syllable is the whole pinyin of the list (了 le, 得 děi, 长 zhǎng).
  if (hanzi.length === 1) return [{ hanzi, pinyin: target, plain: stripTone(target), tone: toneOf(target) }];
  const split = alignByCharacters(hanzi, target);
  if (split) return split;
  // 儿 suffix (一点儿 yìdiǎnr): 儿 is the final -r of the syllable before it.
  if (hanzi.endsWith("儿") && target.endsWith("r")) {
    const base = splitWord(hanzi.slice(0, -1), target.slice(0, -1));
    if (!base) return null;
    const last = base[base.length - 1];
    return [...base.slice(0, -1), { hanzi: `${last.hanzi}儿`, pinyin: `${last.pinyin}r`, plain: `${last.plain}r`, tone: last.tone }];
  }
  return null;
}

function alignByCharacters(hanzi: string, target: string): Syllable[] | null {
  const guess = pinyin(hanzi, { type: "array", toneSandhi: false }) as string[];
  if (guess.length !== hanzi.length) return null;
  // Same letters once the tones are removed: cut the list's pinyin at the same places.
  if (guess.map(stripTone).join("") !== stripTone(target)) return null;
  const syllables: Syllable[] = [];
  let pos = 0;
  const chars = [...target];
  for (let i = 0; i < hanzi.length; i++) {
    const len = [...stripTone(guess[i])].length;
    const part = chars.slice(pos, pos + len).join("");
    pos += len;
    syllables.push({ hanzi: hanzi[i], pinyin: part, plain: stripTone(part), tone: toneOf(part) });
  }
  return syllables;
}

export function toToneWord(entry: { id: number; hanzi: string; pinyin: string; translation: string }): ToneWord | null {
  const hanzi = entry.hanzi.trim();
  const syllables = splitWord(hanzi, entry.pinyin);
  if (!syllables) return null;
  return { id: entry.id, hanzi, pinyin: entry.pinyin, translation: entry.translation, syllables, audioSafe: readsAsListed(hanzi, syllables) };
}

function readsAsListed(hanzi: string, syllables: Syllable[]): boolean {
  const merged = (s: Syllable) => s.hanzi.length > 1 && s.hanzi.endsWith("儿"); // 点儿 diǎnr
  const base = syllables.some(merged) ? hanzi.slice(0, -1) : hanzi;
  const usual = (pinyin(base, { type: "array", toneSandhi: false }) as string[]).map((p) => p.normalize("NFC"));
  return syllables.every((s, i) => {
    const u = usual[i];
    if (!u) return false;
    const plain = merged(s) ? s.plain.slice(0, -1) : s.plain;
    // Neutral tones (爸爸 bàba) and 一 / 不 (read with their tone change) are fine.
    return stripTone(u) === plain && (toneOf(u) === s.tone || s.tone === 5 || s.hanzi === "一" || s.hanzi === "不");
  });
}

/**
 * What changes when the word is spoken, to explain why the audio may not match the
 * tones of the list: 3rd + 3rd → 2nd + 3rd, and 一 / 不 before another syllable.
 */
export function sandhiNotes(word: ToneWord): string[] {
  const s = word.syllables;
  const notes: string[] = [];
  const thirds = s.some((syl, i) => i + 1 < s.length && syl.tone === 3 && s[i + 1].tone === 3);
  if (thirds) {
    const spoken = s.map((syl, i) => (syl.tone === 3 && i + 1 < s.length && s[i + 1].tone === 3 ? markTone(syl.plain, 2) : syl.pinyin));
    notes.push(
      `À l'oral, un 3e ton suivi d'un autre 3e ton se prononce comme un 2e ton : on entend « ${spoken.join(" ")} », on écrit « ${s.map((x) => x.pinyin).join(" ")} ».`
    );
  }
  s.forEach((syl, i) => {
    const nextTone = s[i + 1]?.tone;
    if (!nextTone) return;
    if (syl.hanzi === "一") {
      notes.push(
        `一 change de ton selon la syllabe qui suit : yí devant un 4e ton (一个 yí gè), yì devant les autres (一些 yì xiē). La liste HSK écrit ici « ${syl.pinyin} ».`
      );
    } else if (syl.hanzi === "不" && nextTone === 4) {
      notes.push(`不 se prononce bú devant un 4e ton (不是 bú shì). La liste HSK écrit ici « ${syl.pinyin} ».`);
    }
  });
  return notes;
}

/** The learner's syllable, compared without tone: "lv", "lu:" and "lü" are the same. */
export function normalizePlain(text: string): string {
  return stripTone(text.trim().toLowerCase())
    .replace(/[1-5]$/, "")
    .replace(/u:|v/g, "ü");
}

/** A tone typed with the letters ("xue2", "xué"), if any. */
export function typedTone(text: string): Tone | null {
  const t = text.trim();
  const digit = /([1-5])$/.exec(t);
  if (digit) return Number(digit[1]) as Tone;
  const mark = toneOf(t);
  return mark === 5 ? null : mark;
}

/** Same letters? The list writes ü only after l / n (lü, nü); after j q x y it is written u. */
export function samePlain(answer: string, expected: string): boolean {
  const a = normalizePlain(answer);
  const e = normalizePlain(expected);
  if (a === e) return true;
  return /^[jqxy]/.test(e) && a.replace(/ü/g, "u") === e.replace(/ü/g, "u");
}

export const TONE_LABEL: Record<Tone, string> = { 1: "1er ton", 2: "2e ton", 3: "3e ton", 4: "4e ton", 5: "ton neutre" };
export const TONE_SIGN: Record<Tone, string> = { 1: "ˉ", 2: "ˊ", 3: "ˇ", 4: "ˋ", 5: "·" };
