# Project Report

`report.tex` — a technical report on the HSK Trainer project (architecture,
engineering decisions, deployment).

## Compiling

The report **must** be compiled with **XeLaTeX** (it uses `fontspec` + `xeCJK`
to render Chinese characters). All fonts are bundled with TeX Live full and
Overleaf — no system font installation is required.

### Overleaf (easiest)

1. Upload `report.tex`.
2. Menu → Settings → **Compiler: XeLaTeX**.
3. Recompile (run twice so the table of contents resolves).

### Local

```bash
cd report
xelatex report.tex
xelatex report.tex   # second pass for the table of contents
```

Output: `report.pdf`.

## Fonts

- Body: TeX Gyre Pagella
- Headings / UI: TeX Gyre Heros
- Mono: Latin Modern Mono
- Chinese: Fandol Song (`FandolSong-Regular.otf`)

To use a different Chinese font, edit the `\setCJKmainfont` line near the top of
`report.tex` (e.g. `Noto Serif CJK SC`, `SimSun` on Windows, `Songti SC` on
macOS).

## Hosting on a portfolio

Compile to PDF and link the PDF, or embed it in a `<iframe>` / PDF viewer on
your portfolio site. The PDF is self-contained (vector TikZ diagrams, no
external images).
