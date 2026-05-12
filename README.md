# Chinese HSK App

Application web d'entrainement HSK (niveaux 1, 2 et 3) construite avec Streamlit.

## Stack actuel

- App web: Streamlit (multipage)
- Backend: Python
- ORM: SQLAlchemy
- Base de donnees:
  - Production: PostgreSQL (Neon)
  - Fallback local: SQLite
- Authentification: hash PBKDF2 (hashlib)
- Donnees initiales: CSV HSK1/HSK2/HSK3
- Algorithme de revision: FSRS (Free Spaced Repetition Scheduler)
- Correction d'expression ecrite: Anthropic Claude (Haiku 4.5 par defaut)

## Fonctionnalites

- Quiz comprehension (QCM, saisie texte, auto-evaluation 4 boutons Faux/Difficile/Juste/Je connais)
- Selection des mots a reviser pilotee par FSRS (next_review_at, stability, difficulty)
- Gestion pinyin (avec/sans tons)
- Comptes utilisateur (inscription/connexion)
- Dashboard de maitrise + historique des revisions
- Page Expression ecrite avec correction IA structuree :
  - Pool de sujets curates par niveau HSK (HSK1/2/3, 12 sujets chacun)
  - Generation de nouveaux sujets via Claude (a la demande)
  - Correction au format JSON : erreurs typees, version corrigee, pinyin, traduction, score, conseils
  - Auto-injection des erreurs de vocabulaire dans la file SRS

## Installation locale

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration des secrets

Copier `.streamlit/secrets.toml.example` en `.streamlit/secrets.toml` et renseigner :

```toml
HSK_DATABASE_URL = "postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require"
ANTHROPIC_API_KEY = "sk-ant-..."
# HSK_CLAUDE_MODEL = "claude-haiku-4-5-20251001"  # optionnel
```

Vous pouvez aussi exporter ces valeurs en variables d'environnement (`ANTHROPIC_API_KEY`, `HSK_DATABASE_URL`, `HSK_CLAUDE_MODEL`).

### Cle API Anthropic

L'abonnement Claude Pro/Max ne donne **pas** acces a l'API. Creez un compte separe sur [console.anthropic.com](https://console.anthropic.com/), ajoutez quelques dollars de credits, puis generez une cle. Haiku 4.5 coute environ 0,003 $ par correction grace au prompt caching applique cote app.

Quota cote app : 20 corrections par jour par utilisateur (modifiable dans `pages/02_Expression.py`).

## Lancer en local

```powershell
streamlit run Main.py
```

URL locale par defaut: http://localhost:8501

## Deploiement Streamlit Cloud

1. Push le depot sur GitHub
2. Creer l'app sur Streamlit Community Cloud
   - Repository: ce depot
   - Branch: main
   - Main file path: Main.py
3. Configurer les secrets (`HSK_DATABASE_URL` et `ANTHROPIC_API_KEY`)
4. Sauvegarder: l'app redeploie automatiquement

## Neon (gratuit, usage perso)

- Créer un projet Neon Free
- Garder Neon Auth desactive
- Copier la connection string Postgres
- Ajouter cette URL dans Streamlit Secrets (cle HSK_DATABASE_URL)

## Reset base locale (optionnel)

```powershell
python -m scripts.reset_db
```

## Fichiers importants

- Main.py
- pages/01_Comprehension.py
- pages/02_Expression.py
- pages/Account.py
- db.py
- models.py
- repo.py
- seed.py
- srs.py (FSRS scheduling wrapper)
- llm.py (Anthropic client + prompt caching)
- data/expression_subjects.json
