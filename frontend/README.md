# HSK Trainer — Frontend

Next.js 16 + React 19 + TypeScript + Tailwind v4 + shadcn-style components.

## Stack

- **Next.js 16 (App Router)** — Turbopack, RSC + Client Components
- **Tailwind v4** — CSS-first config (theme tokens in `app/globals.css`)
- **shadcn-style components** — primitives copied into `components/ui/` (Button, Input, Label, Card, Skeleton)
- **TanStack Query** — server-state cache, optimistic UI
- **react-hook-form + zod** — typed forms with schema validation
- **next-themes** — dark / light / system pref
- **framer-motion** — page transitions + quiz card animations
- **sonner** — toasts
- **Vitest** — unit tests

## Setup

```powershell
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

Open http://localhost:3000.

Make sure the **backend** is running at the URL set in `NEXT_PUBLIC_API_URL`:

```powershell
# In a separate terminal
cd ..\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## Tests

```powershell
npm test              # one-shot
npm run test:watch
```

## Scripts

- `npm run dev` — dev server with Turbopack
- `npm run build` — production build
- `npm run start` — production server
- `npm run lint` — ESLint
- `npm run test` — Vitest one-shot
- `npm run gen:api` — regenerate TypeScript types from a live backend's `/openapi.json`

## Optimistic UI flow (Comprehension page)

1. Setup screen: user picks quiz + count + mode. Backend stats fetched via TanStack Query.
2. "Lancer la session" → `getDueEntries(quiz, count)` → array of `DueEntry`.
3. Quiz running: local state holds questions. On rating click:
   - `recordRating()` advances the index **immediately** (next question renders in <50 ms).
   - `postRate({ entry_id, rating })` fires in background via `useMutation` (retry × 2).
   - On success: snapshot is attached to the history item (so the summary shows the next review hint).
   - On error: toast notifies the user; the rating is silently retried.
4. End of session: summary screen with the table of answered words + next-review hints.

## Theme palette — Cinnabar / Ink / Paper

Cinnabar (印章 seal red) + ink + paper. Defined in `app/globals.css` via OKLCH for both light and dark modes:

- `primary`: cinnabar
- `background` / `card`: paper (light) / ink (dark)
- `foreground`: ink (light) / paper (dark)

The `.hanzi` utility class uses `Noto Sans SC` for Chinese characters with slightly increased letter-spacing.
