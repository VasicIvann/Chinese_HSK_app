/**
 * Forgiving pinyin comparison used in the pinyin-input quiz mode.
 *
 * - Strips tone marks (`ā á ǎ à` → `a`)
 * - Lowercases everything
 * - Removes all whitespace and punctuation
 *
 * Tones are intentionally ignored: typing the correct syllables is enough
 * for HSK1-3 self-assessment, requiring exact tone marks on a phone keyboard
 * would tank the UX. The user can self-rate as "Difficile" if they got the
 * syllables right but were unsure of the tone.
 */

const TONE_MAP: Record<string, string> = {
  ā: "a", á: "a", ǎ: "a", à: "a",
  ē: "e", é: "e", ě: "e", è: "e",
  ī: "i", í: "i", ǐ: "i", ì: "i",
  ō: "o", ó: "o", ǒ: "o", ò: "o",
  ū: "u", ú: "u", ǔ: "u", ù: "u",
  ǖ: "v", ǘ: "v", ǚ: "v", ǜ: "v",
  ü: "v",
  ń: "n", ň: "n", ǹ: "n",
};

export function normalizePinyin(value: string): string {
  if (!value) return "";
  let out = "";
  for (const ch of value.toLowerCase()) {
    if (TONE_MAP[ch]) {
      out += TONE_MAP[ch];
    } else if (/[a-z]/.test(ch)) {
      out += ch;
    } else if (/[0-9]/.test(ch)) {
      // Drop tone numbers — they're not required.
      continue;
    }
  }
  return out;
}

export function pinyinMatches(userInput: string, expected: string): boolean {
  const left = normalizePinyin(userInput);
  const right = normalizePinyin(expected);
  return left.length > 0 && left === right;
}
