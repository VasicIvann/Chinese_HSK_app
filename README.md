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

## Fonctionnalites

- Quiz comprehension (QCM, saisie texte, auto-evaluation)
- Gestion pinyin (avec/sans tons)
- Comptes utilisateur (inscription/connexion)
- Suivi de maitrise des mots
- Priorisation des mots a revoir

## Installation locale

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## Lancer en local

```powershell
streamlit run Main.py
```

URL locale par defaut: http://localhost:8501

## Deploiement Streamlit Cloud (recommande)

1. Push le depot sur GitHub
2. Creer l'app sur Streamlit Community Cloud
   - Repository: ce depot
   - Branch: main
   - Main file path: Main.py
3. Configurer Neon dans les secrets Streamlit:

```toml
HSK_DATABASE_URL = "postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require"
```

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
- pages/Account.py
- db.py
- models.py
- repo.py
- seed.py
