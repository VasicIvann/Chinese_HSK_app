# Chinese HSK App

Application web d'entrainement au HSK (niveaux 1 et 2) construite avec Streamlit.

## 1) Stack technique

- Frontend + app: Streamlit (multipages)
- Backend applicatif: Python
- Base de donnees: SQLite
- ORM: SQLAlchemy
- Donnees initiales: CSV (`data/hsk1.csv`, `data/hsk2.csv`)
- Authentification: hash de mot de passe PBKDF2 (implementation maison via `hashlib`)

## 2) Fonctionnalites principales

- Page d'accueil moderne avec navigation custom
- Quiz de comprehension ecrite (QCM + saisie libre)
- Gestion de variantes pinyin (avec ou sans tons)
- Score en temps reel + recap final
- Espace compte:
  - creation de compte
  - connexion/deconnexion
  - sauvegarde des preferences utilisateur
- Seed automatique de la base au premier lancement

## 3) Arborescence utile

- `Main.py`: point d'entree Streamlit
- `pages/01_Comprehension.py`: quiz principal
- `pages/02_Expression.py`: page expression (placeholder)
- `pages/Account.py`: espace compte
- `db.py`: moteur SQLAlchemy + session
- `models.py`: modeles ORM
- `repo.py`: acces donnees (quizzes, users, settings)
- `seed.py`: chargement initial CSV -> SQLite
- `scripts/reset_db.py`: reset + reseed de la base

## 4) Prerequis

- Python 3.10+
- pip

## 5) Installation locale

Depuis la racine du projet:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install streamlit sqlalchemy
```

## 6) Lancer une version test en local

```powershell
streamlit run Main.py
```

L'app sera accessible par defaut sur:
- http://localhost:8501

## 7) Reset de la base (optionnel)

Pour repartir d'une base propre puis reseeder depuis les CSV:

```powershell
python -m scripts.reset_db
```

## 8) Commandes de deploiement

### Option A: deploiement sur un service type Render / Railway / VM

1. Installer les dependances au build:

```bash
pip install --upgrade pip
pip install streamlit sqlalchemy
```

2. Commande de demarrage (Start Command):

```bash
streamlit run Main.py --server.address 0.0.0.0 --server.port $PORT
```

Notes:
- La variable `PORT` est generalement fournie par la plateforme.
- Cette commande est celle a renseigner dans le service web deploye.

### Option B: Streamlit Community Cloud

- Pousser le depot sur GitHub
- Verifier que le depot contient bien un `requirements.txt` a la racine
- Aller sur https://share.streamlit.io/ ou Streamlit Community Cloud
- Creer une nouvelle app en selectionnant:
  - Repository: ce depot
  - Branch: la branche principale (souvent `main`)
  - Main file path: `Main.py`
- Cliquer sur `Deploy`
- Streamlit Cloud installera automatiquement les dependances puis lancera l'app

Notes importantes:
- `Main.py` doit rester le point d'entree.
- Comme la base utilise SQLite locale, les donnees utilisateur peuvent etre reinitialisees si l'environnement Cloud est recrée. Pour une persistence longue duree, il faudra plus tard migrer vers une base distante.

## 9) Modele de commande locale equivalent au deploiement

Pour simuler localement un environnement de plateforme:

```powershell
$env:PORT=8501
streamlit run Main.py --server.address 0.0.0.0 --server.port $env:PORT
```

## 10) Dependances minimales

Le projet utilise actuellement ces dependances Python externes:
- `streamlit`
- `sqlalchemy`

Vous pouvez figer les versions si besoin:

```powershell
pip freeze > requirements.txt
```
