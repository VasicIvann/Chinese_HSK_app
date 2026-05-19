# Project Report

`report.tex` — a technical report on the HSK Trainer project (architecture,
engineering decisions, deployment).

## Compiling

The report **must** be compiled with **XeLaTeX** (it uses `fontspec` + `xeCJK`
to render Chinese characters — it will fail with pdfLaTeX). All fonts are
bundled with TeX Live / MiKTeX / Overleaf — no system font install is required.

The engine is selected **automatically** by two mechanisms already in the repo,
so you normally don't have to configure anything:

- `% !TEX program = xelatex` magic comment on line 1 of `report.tex`
  (read by VS Code LaTeX Workshop, TeXShop, TeXworks…)
- `latexmkrc` (`$pdf_mode = 5`) — read by `latexmk` locally **and on Overleaf**

### Overleaf

Upload the whole `report/` folder (so `latexmkrc` is included). It builds with
XeLaTeX automatically. If you ever see a pdfLaTeX error, also set
Menu → Settings → **Compiler: XeLaTeX** as a fallback.

### Local — VS Code (LaTeX Workshop)

Just open `report.tex` and build. The magic comment + `latexmkrc` route it to
XeLaTeX. If a previous pdfLaTeX attempt left the build stuck, clean once:

```bash
cd report
latexmk -C        # remove stale aux files from the failed pdflatex run
latexmk           # rebuilds with XeLaTeX via latexmkrc
```

### Local — command line

```bash
cd report
latexmk report.tex          # uses latexmkrc → XeLaTeX, handles the 2 passes
# or, manually:
xelatex report.tex && xelatex report.tex
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
