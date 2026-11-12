# Classificateurs (量词) — HSK 1 à 3

`classifiers.json` est généré par `python scripts/build_classifiers.py` à partir de `src/l1.yaml`,
`src/l2.yaml`, `src/l3.yaml` (un fichier par niveau HSK 3.0). Ne pas éditer le JSON à la main.

## Quels classificateurs, à quel niveau

- **Choix** : les classificateurs nominaux (名量词) et verbaux (动量词). Les unités de mesure et de
  temps (元, 公斤, 米, 分钟, 年, 岁…) sont laissées de côté.
- **HSK 3.0** : le plus bas des deux niveaux officiels, celui de la liste de vocabulaire (mot marqué
  量) et celui du 语法等级大纲 (points 8, 58, 59, 138, 139 : 杯、本、个、家、间、口、块、页 au
  niveau 1 ; 层、封、件、条、位 / 遍、次、场、回、下 au niveau 2 ; 把、行、架、群、束、双、台、
  张、支、只、种 / 顿、口、眼 au niveau 3).
- **HSK 2.0** : le niveau du caractère dans la liste 2.0, ou celui du nom dont le classificateur
  vient directement (杯子 → 杯, 房间 → 间, 句子 → 句, 声音 → 声). `null` = au-delà du niveau 3.

## Format d'une fiche

```yaml
- hanzi: 本
  pinyin: běn
  kind: nominal            # nominal | verbal | both
  level: {"3.0": 1, "2.0": 1}
  usage: "Une ligne : à quoi il sert."     # utilisé par le quiz des usages
  explanation: >-
    Quelques phrases en français.
  nouns: ["书|livre", "椅子|chaise|张"]   # nom|français|autres classificateurs aussi corrects
  examples:
    - ["这本书很有意思。", "Ce livre est très intéressant."]
  traps: >-
    Pièges et confusions fréquentes (facultatif).
  sentences:
    - "我买了三{本}书。 | 张 条 件 杯 只 | J'ai acheté trois livres."
```

Une phrase = `phrase avec {réponse} | distracteurs | traduction`, plus en option `| lv=3` (niveau
minimum) et `| extra=mot,mot` (mots hors liste acceptés). Les **distracteurs** (3 à 6, le quiz en
tire 3) doivent être **faux sans ambiguïté** : ne pas y mettre un classificateur qui serait aussi
correct (个 pour les personnes, 只/条 pour un chien, 次/遍/下 entre eux, 看了一张… avec un nom
sous-entendu).

## Vérifications du script

Pour chaque phrase et chaque version, le script cherche le plus bas niveau (≥ celui du
classificateur) dont les listes de mots couvrent la phrase (même contrôle que la banque
d'exercices) et où au moins trois distracteurs sont connus. Une phrase sans niveau possible dans
une version n'y est pas proposée.
