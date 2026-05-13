# Déploiement — HSK Trainer

Cible : backend FastAPI sur **Render free tier**, frontend Next.js sur **Vercel Hobby**, DB **Neon Postgres**, keep-warm via **cron-job.org**. Coût total : **0 €** (hors crédits API Anthropic).

## Prérequis

- Repo Github à jour (`git push origin main`)
- Compte Neon (DB déjà créée pour l'app Streamlit, on réutilise)
- Compte Anthropic Console avec une clé API valide et quelques crédits
- Comptes (gratuits) : [Render](https://render.com), [Vercel](https://vercel.com), [cron-job.org](https://cron-job.org)

---

## 1. Backend — Render

### 1.1 Créer le service

1. Dashboard Render → **New** → **Blueprint**
2. Connecte ton repo GitHub `VasicIvann/Chinese_HSK_app`, branche `main`
3. Render détecte `render.yaml` à la racine et propose `hsk-api`
4. Clique **Apply** → le service est créé mais pas encore démarré (env vars manquantes)

### 1.2 Configurer les secrets

Dans le service `hsk-api` → onglet **Environment** → ajoute :

| Clé | Valeur |
|---|---|
| `HSK_DATABASE_URL` | URL Neon Postgres (la même que `.streamlit/secrets.toml`) |
| `JWT_SECRET_KEY` | 64 caractères aléatoires : `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ANTHROPIC_API_KEY` | Clé API Anthropic (la nouvelle clé que tu as régénérée) |
| `CORS_ORIGINS` | `https://hsk-trainer.vercel.app` (mets l'URL Vercel exacte une fois le frontend déployé) |
| `ALLOWED_REGISTRATION_EMAILS` | `ivannvasic05@gmail.com` (pour empêcher d'autres inscriptions et économiser tes tokens) |

Save changes → Render relance le build.

### 1.3 Migration DB

Première fois sur Neon, depuis ton terminal local (Python avec psycopg installé) :

```powershell
cd backend
$env:HSK_DATABASE_URL = "postgresql+psycopg://...neon..."
..\.venv\Scripts\python.exe -m alembic stamp head
```

`stamp head` dit à Alembic que ton schéma Neon est déjà au niveau de `0001_baseline` (les tables existent déjà depuis Streamlit). Les futures migrations partiront de là.

### 1.4 Vérifier

Une fois le build vert, ouvre `https://hsk-api.onrender.com/healthz` → `{"status":"ok"}`.

Et `https://hsk-api.onrender.com/docs` → Swagger UI complète.

### 1.5 Keep-warm (cron-job.org)

Le free tier de Render endort le service après 15 min sans requête. Pour le garder éveillé 24/7 :

1. Crée un compte sur [cron-job.org](https://cron-job.org) (gratuit, sans carte)
2. **Create cronjob** :
   - Title: `HSK API keep-warm`
   - URL: `https://hsk-api.onrender.com/healthz`
   - Schedule: every 10 minutes
   - Method: GET
3. Save. Le service ne dormira plus.

---

## 2. Frontend — Vercel

### 2.1 Importer le projet

1. Dashboard Vercel → **Add New** → **Project**
2. Sélectionne le repo `Chinese_HSK_app`
3. Vercel détecte Next.js automatiquement
4. **Root directory** : `frontend`
5. Build settings : laisser auto (Next.js preset)

### 2.2 Variables d'environnement

Avant de déployer, dans **Environment Variables** :

| Clé | Valeur |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://hsk-api.onrender.com` (URL Render exacte) |

### 2.3 Déployer

Clique **Deploy**. Au bout de 1-2 min, ton frontend est en ligne sur `https://hsk-trainer.vercel.app` (le slug dépend du nom de ton projet).

### 2.4 Mise à jour CORS

Reviens sur Render → service `hsk-api` → Environment → mets à jour `CORS_ORIGINS` avec l'URL Vercel exacte. Save → Render relance.

---

## 3. Tester en prod

1. Ouvre l'URL Vercel
2. Connecte-toi avec ton compte Neon existant
3. Lance une session HSK1 → tu retrouves tes données SRS
4. Va sur Account → tu vois ton dashboard avec les graphes
5. Sur ton téléphone, ouvre la même URL → "Ajouter à l'écran d'accueil" via Safari/Chrome
   → l'app s'ouvre en plein écran grâce au manifest PWA

---

## 4. Déploiements suivants

Push sur `main` → **les deux** plateformes redéploient automatiquement :
- Vercel : ~1 min, ZDT
- Render : ~3 min, downtime de ~30s pendant le swap

GitHub Actions exécute aussi les tests à chaque push/PR (voir `.github/workflows/tests.yml`).

---

## 5. Coûts mensuels attendus

| Service | Coût |
|---|---|
| Render free | 0 € (750 h/mois, keep-warm OK) |
| Vercel Hobby | 0 € (100 GB bandwidth/mois) |
| Neon free | 0 € (0.5 GB storage, auto-suspend OK) |
| cron-job.org | 0 € (5 jobs gratuits) |
| Anthropic Haiku 4.5 | ~0.003 $ / correction (≈ 90 ¢ / mois si 1 correction/jour) |

**Total : moins de 1 $/mois si tu utilises l'expression écrite quotidiennement.**

---

## 6. Migration depuis Streamlit Cloud

Quand tu es confiant que la nouvelle app fonctionne :

1. Sur `hskapp.streamlit.app` → Settings → Delete app (ou Pause)
2. Garde la branche Streamlit du repo intacte si tu veux y revenir
3. Mets à jour les bookmarks de tes navigateurs vers l'URL Vercel

Tes données Neon (compte, FSRS, expression attempts) sont partagées entre les deux apps tant qu'elles tournent en parallèle. Aucun risque de perte.
