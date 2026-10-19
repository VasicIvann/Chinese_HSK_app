# HSK-format exercises (levels 1–3)

- `formats.json` — the parts of each paper, per version and level, in the order and
  with the number of questions of the real exam:
  - **HSK 3.0**: 《新版HSK（1-6级）考试结构与样题示例》 (汉考国际, published 2025-12,
    in force 2026-07).
  - **HSK 2.0**: the official 2012 sample papers (样卷).
  Pictures of the real papers are replaced by French descriptions of the scene.
  HSK 3.0 level 2, writing part 1 is listed but not reproduced: the sample shows
  only six picture options and its instruction is not published in text.
- `src/l1.yaml`, `src/l2.yaml`, `src/l3.yaml` — the question bank, written for this
  app (format of each item type: `app/services/exercise_schema.py`).
- `bank.json` — built from the sources by `python scripts/build_exercises.py`,
  which validates every item, checks that its Chinese only uses characters of the
  level's word lists (`../hsk2`, `../hsk3`), records which versions it fits, and
  shuffles the options (the right answer is written first in the sources).

Learners can also ask Claude for a brand-new series of any part ("Nouvelle série"):
generated items go through the same validation and are kept for that learner.
