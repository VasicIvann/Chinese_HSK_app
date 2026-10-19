# HSK 2.0 vocabulary (levels 1–5)

The previous HSK format (2012 official Hanban word lists), still used for the
exam sessions held before the HSK 3.0 switch (13 December 2026).

| Level | New words | Cumulative |
|---|---|---|
| HSK 1 | 150 | 150 |
| HSK 2 | 151 | 301 |
| HSK 3 | 297 | 598 |
| HSK 4 | 598 | 1,196 |
| HSK 5 | 1,300 | 2,496 |

The official lists name 150 / 150 / 300 / 600 / 1,300 words; the small
differences come from a few words the lists repeat at a higher level with
another use (过, 还, 长, 得, 等), which are kept once, at their first level.

- Source of the word lists: "HSK Official With Definitions 2012 L1–L5" from
  [hskhsk.com](https://github.com/glxxyz/hskhsk.com) (checked against the app's
  previous HSK 1–3 lists in `../legacy-hsk2.0`).
- French translations: reused from the HSK 3.0 lists (`../hsk3`) or the previous
  lists when the word is there; the 376 remaining words were translated for this
  app.
- Columns: `hanzi, pinyin, translation, alt_translations`. When a character has
  several readings, `pinyin` keeps the first one.

Migration `0007_hsk_versions` loads these files. A word present in both versions
is one single entry in the database, so its progress is shared.
