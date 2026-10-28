# Déployer TIC MASTER sur PythonAnywhere

> **À savoir avant de commencer**
> PythonAnywhere **gratuit** accepte très bien Flask, mais impose trois limites :
> 1. **Pas de PostgreSQL** (ni MySQL pour les comptes créés après le 15/01/2026) → l'application
>    utilisera **SQLite**, stocké dans `~/ticmaster/instance/ticmaster.db`.
>    Les données restent persistantes, mais l'instance PythonAnywhere est **séparée** de celle de
>    Render : les deux sites ont chacun leur propre base.
> 2. **Pas de connexion sortante** vers une base extérieure : impossible de brancher la base Render.
> 3. **Pas de domaine personnalisé** : l'adresse sera `https://VOTRE_NOM.pythonanywhere.com`.
>
> **Le site Render reste l'installation principale** : <https://ticmaster.onrender.com>.
> PythonAnywhere sert de **seconde copie / secours**.

---

## Étape 0 — Créer le compte (obligatoire, 2 minutes)

L'inscription comporte un **captcha** : elle doit être faite par vous.

1. Ouvrez <https://www.pythonanywhere.com/registration/register/beginner/>
2. Choisissez **« Beginner account » (gratuit)**.
3. Remplissez : nom d'utilisateur, mot de passe, e-mail → **Create account**.
4. Relevez votre adresse : elle ressemble à `https://monnom.pythonanywhere.com`.

Ensuite, transmettez-moi **l'identifiant et le mot de passe** : je termine toute la configuration
(copie du projet, environnement Python, base, super administrateur pose, redémarrage, tests).

---

## Ce qui sera fait une fois le compte créé

### 1. Récupérer le projet

Dans un **Bash console** (onglet *Consoles → Bash*) :

```bash
git clone https://github.com/rzkmyazi/ticmaster.git ~/ticmaster
cd ~/ticmaster
python3 -m venv ~/.virtualenvs/ticmaster
source ~/.virtualenvs/ticmaster/bin/activate
pip install -r requirements.txt
```

### 2. Créer le fichier de configuration

```bash
cd ~/ticmaster
python3 - <<'EOF'
import secrets, pathlib
cle = secrets.token_hex(32)
pathlib.Path(".env").write_text(
    "FLASK_ENV=production\n"
    "COOKIE_SECURE=1\n"
    "SITE_NAME=TIC MASTER\n"
    f"SECRET_KEY={cle}\n"
    "SUPER_ADMIN_USERNAME=Myazirzk\n"
    "SUPER_ADMIN_PASSWORD=Fiaram131213!!\n"
    "AUTH_SESSION_HOURS=8\n"
    "LOGIN_MAX_ATTEMPTS=5\n"
    "LOGIN_LOCK_MINUTES=15\n",
    encoding="utf-8",
)
print("fichier .env créé")
EOF
```

> Le fichier `.env` contient des secrets : il est exclu par `.gitignore`.

### 3. Installer le contenu pédagogique et le super administrateur

```bash
cd ~/ticmaster
source ~/.virtualenvs/ticmaster/bin/activate
python seed.py bootstrap
```

Sortie attendue :

```
==> Base de donnees prete
OK SUPER ADMIN « Myazirzk » cree.
OK 12 modules, 36 lecons, 69 questions
```

La commande est **idempotente** : la relancer ne détruit rien et ne change pas le mot de passe.

### 4. Déclarer l'application web

Onglet **Web** → **Add a new web app** → **Manual configuration** → **Python 3.12**
(ne pas choisir « Flask » : la configuration manuelle évite un projet d'exemple).

| Champ | Valeur |
|---|---|
| Source code | `/home/VOTRE_NOM/ticmaster` |
| Working directory | `/home/VOTRE_NOM/ticmaster` |
| Virtualenv | `/home/VOTRE_NOM/.virtualenvs/ticmaster` |

### 5. Fichier WSGI

Cliquer sur le lien **WSGI configuration file**, **effacer tout**, puis coller :

```python
import os, sys
path = os.path.expanduser("~/ticmaster")
if path not in sys.path:
    sys.path.insert(0, path)
os.chdir(path)
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("COOKIE_SECURE", "1")
from wsgi import app as application
```

*(copie prête à l'emploi : fichier `pythonanywhere_wsgi.py` du dépôt)*

### 6. Fichiers statiques

Toujours dans l'onglet **Web**, section **Static files** :

| URL | Directory |
|---|---|
| `/static/` | `/home/VOTRE_NOM/ticmaster/app/static/` |

### 7. Démarrer

Bouton vert **Reload**. Puis vérifier :

- `https://VOTRE_NOM.pythonanywhere.com/sante`
  → `{"app":"TIC MASTER","database":true,"status":"ok"}`
- `https://VOTRE_NOM.pythonanywhere.com/inscription` → **404** (aucune inscription publique)
- Connexion avec `Myazirzk` / `Fiaram131213!!`

> Sur un compte gratuit, le site doit être **réactivé par un clic toutes les 3 semaines**
> (bouton « Run until 3 months from today »). C'est la contrepartie de la gratuité.

### 8. Vérification automatique

```bash
cd ~/ticmaster
BASE=https://VOTRE_NOM.pythonanywhere.com SUPER_PASSWORD='Fiaram131213!!' python3 tools/verify.py
```

Attendu : `=== Bilan : tout est conforme ✔ ===` (54 contrôles).

---

## Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `Error running WSGI application ... ModuleNotFoundError: No module named 'flask'` | mauvais virtualenv | onglet Web → Virtualenv = `/home/NOM/.virtualenvs/ticmaster` |
| Page blanche / `DisallowedHost` | domaine non autorisé | déjà géré : l'application ne filtre pas l'hôte |
| `database: false` sur `/sante` | `seed.py bootstrap` non lancé | relancer l'étape 3 |
| Les styles ne s'affichent pas | mapping `/static/` absent | refaire l'étape 6 |
| Le site est désactivé | compte gratuit inactif | bouton « Run until 3 months from today » |
| Erreur de connexion SQLite | dossier `instance/` absent | `mkdir -p ~/ticmaster/instance` |

---

## Coût

| Formule | Prix | Ce que ça donne |
|---|---|---|
| Beginner (gratuit) | 0 € | 1 application, `nom.pythonanywhere.com`, SQLite, réactivation toutes les 3 semaines |
| Developer | ~5 $/mois | Pas de réactivation, MySQL, CPU illimité |
| Postgres | payant | Base PostgreSQL managée — inutile ici, Render le fait déjà |
