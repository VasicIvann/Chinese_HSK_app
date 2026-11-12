# HSK 3.0 vocabulary, levels 1–5

Source: **HSK 考试大纲** (HSK Examination Syllabus), published November 2025 by the
Center for Language Education and Cooperation (中外语言交流合作中心), in force since
July 2026 — the word list of the new HSK exam. Official PDF linked from
<https://www.chinesetest.cn/> ("Examination Syllabus").

| File | New words at this level | Cumulative |
|---|---|---|
| `hsk1.csv` | 300 | 300 |
| `hsk2.csv` | 200 | 500 |
| `hsk3.csv` | 500 | 1,000 |
| `hsk4.csv` | 1,000 | 2,000 |
| `hsk5.csv` | 1,600 | 3,600 |

Columns: `hanzi`, `pinyin`, `translation` (French), `alt_translations`,
`part_of_speech` (as printed in the syllabus), `homograph` (sense number when the
syllabus lists the same word twice), `source_page` (page of the PDF).

Hanzi, pinyin, part of speech, level and page come from the machine-readable
extraction <https://github.com/uranbekanarbaev/hsk-3.0-vocabulary-dataset>, whose
per-level counts reproduce the syllabus totals exactly. It was cross-checked
against two independent extractions of the same PDF
(<https://github.com/Punpuf/hsk-syllabus-vocabulary-parser>,
<https://github.com/harukicoder/hsk30>): every pinyin difference is a legitimate
second reading of a polyphonic character.

French translations: reused from the previous HSK 2.0 lists when the same word and
reading existed (and corrected where the old wording did not match the syllabus
sense), otherwise written for this project, guided by the part of speech.

The database is synced from these files by Alembic migration
`0005_hsk3_vocabulary` (idempotent).
