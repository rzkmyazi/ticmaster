# Guide de déploiement — TIC MASTER

Trois cibles sont documentées : **Render** (recommandé, gratuit pour démarrer), **Cloudflare**
(domaine, sécurité, performance) et **PythonAnywhere** (alternative française/européenne).
Le dépôt **GitHub** est le point de départ commun.

> ⚠️ Ce guide décrit les étapes à exécuter avec **vos** comptes. Aucun identifiant n'est fourni
> avec le projet : les secrets sont générés par les plateformes ou par vous.

---

## 1. Préparer le dépôt GitHub

```bash
cd ticmaster
git init
git add .
git commit -m "TIC MASTER — plateforme éducative TIC (#by_Myazirzk)"
git branch -M main
git remote add origin https://github.com/VOTRE_COMPTE/ticmaster.git
git push -u origin main
```

Vérifications avant le premier push :

- `.env` **absent** du dépôt (`git status` ne doit pas l'afficher) ;
- `instance/ticmaster.db` absent (base locale) ;
- `.gitignore` présent (secrets, `__pycache__`, `instance/*.db`, `instance/uploads/*`).

Créer ensuite l'URL publique du dépôt et, si besoin, un jeton d'accès personnel GitHub
(*Settings → Developer settings → Personal access tokens*) pour les push automatiques.

---

## 2. Render (hébergement principal)

### 2.1 Déploiement « Blueprint » (le plus simple)

Le fichier `render.yaml` décrit l'ensemble de l'infrastructure :

- 1 service web Python (plan gratuit, région Francfort) ;
- 1 base PostgreSQL managée (plan gratuit) ;
- `SECRET_KEY` générée automatiquement ;
- `DATABASE_URL` injectée depuis la base ;
- `healthCheckPath: /sante`.

Étapes :

1. Créer un compte sur [render.com](https://render.com) et connecter GitHub.
2. **New → Blueprint** → sélectionner le dépôt `ticmaster`.
3. Render détecte `render.yaml` et propose le service + la base : valider.
4. Attendre la fin du build (`pip install -r requirements.txt`).
5. Ouvrir le **Shell** du service et créer le premier super administrateur :

```bash
python seed.py init
python seed.py superadmin --username Myazirzk
python seed.py seed
# (facultatif, pour découvrir) :
python seed.py demo
```

> Le Shell Render est interactif : le mot de passe se saisit sans écho.
> Si l'interactivité pose problème, utiliser une variable d'environnement ponctuelle :
> `SUPER_ADMIN_PASSWORD='…' python seed.py superadmin --username Myazirzk`
> puis **supprimer la variable** de l'environnement Render.

6. Ouvrir l'URL `https://ticmaster.onrender.com` → page d'accueil, puis `/auth/connexion`.

### 2.2 Déploiement « manuel »

| Réglage | Valeur |
|---|---|
| Environment | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120` |
| Health Check Path | `/sante` |
| Region | Frankfurt |
| Plan | Free |

Variables d'environnement à définir :

```
FLASK_ENV=production
SECRET_KEY=<généré>            # Render peut le générer
DATABASE_URL=<Internal Database URL>
COOKIE_SECURE=1
AUTH_SESSION_HOURS=8
LOGIN_MAX_ATTEMPTS=5
LOGIN_LOCK_MINUTES=15
PRESENCE_ONLINE_SECONDS=120
MAX_CONTENT_MB=30
SITE_NAME=TIC MASTER
PYTHON_VERSION=3.12.6
```

### 2.3 Points d'attention sur l'offre gratuite

- Le service **se met en veille** après 15 min d'inactivité : la première requête prend ~30 s.
  Pour un usage réel en classe, passer au plan Starter.
- Le **disque est éphémère** : les fichiers téléversés (`instance/uploads`) sont perdus à chaque
  redéploiement. Solutions : disque persistant (plan payant) ou stockage objet (S3 / Cloudflare R2).
  Les **contenus pédagogiques sont en base**, donc conservés.
- La base gratuite PostgreSQL expire après 30 jours : passer en plan payant pour un usage durable,
  ou prévoir un export régulier (`/admin/sauvegardes` + `pg_dump`).
- Les sauvegardes : *Dashboard Render → base → Backups* (plans payants) ou tâche planifiée
  `pg_dump` depuis un runner.

---

## 3. Cloudflare (domaine, sécurité, performance)

Cloudflare ne fait pas tourner l'application : il se place **devant** Render.

1. **Ajouter le domaine** : *Add site* → `votre-domaine.mg` → choisir le plan gratuit.
2. **Changer les serveurs de noms** chez le registrar vers ceux fournis par Cloudflare.
3. **DNS** :

| Type | Nom | Contenu | Proxy |
|---|---|---|---|
| CNAME | `@` (ou `www`) | `ticmaster.onrender.com` | 🟠 Proxied |

4. **SSL/TLS → Overview** : mode **Full (strict)**.
   - Render fournit un certificat valide pour `*.onrender.com` ; pour un domaine personnalisé,
     l'ajouter dans *Render → Settings → Custom Domain*, Render émet alors un certificat
     Let's Encrypt.
5. **SSL/TLS → Edge Certificates** : activer *Always Use HTTPS*, *Automatic HTTPS Rewrites*,
   HSTS (max-age 12 mois).
6. **Règles de cache** (Cache → Cache Rules) :

```
Si (URI Path commence par /static/) → Cache éligible, Edge TTL 1 mois, Browser TTL 1 jour
Si (URI Path ne commence pas par /static/) → Bypass cache
```

   Les pages HTML sont déjà envoyées avec `Cache-Control: no-store` : aucun risque de fuite de
   contenu privé entre utilisateurs.
7. **Sécurité** (Security → WAF) :
   - *Bot Fight Mode* : activé ;
   - règle de rate limiting sur `/auth/connexion` : 10 requêtes / minute / IP → *Block* ;
   - *Security Level* : Medium ; *Challenge* sur les pays non concernés si nécessaire.
8. **Optimisations** : Brotli activé, Early Hints, HTTP/2 et HTTP/3 activés, Rocket Loader **désactivé**
   (inutile : aucun script tiers).
9. **Accessibilité mobile** : rien à configurer ; l'application est déjà responsive et PWA
   (manifest + service worker servis par Flask).

---

## 4. PythonAnywhere (alternative)

1. Créer un compte (offre « Beginner » gratuite).
2. Console Bash :

```bash
git clone https://github.com/VOTRE_COMPTE/ticmaster.git
cd ticmaster
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # éditer : SECRET_KEY, COOKIE_SECURE=1, DATABASE_URL si MySQL/PG
python seed.py init
python seed.py superadmin --username Myazirzk
python seed.py seed
```

3. Onglet **Web → Add a new web app → Manual configuration → Python 3.12**.
4. **Virtualenv** : `/home/VOTRE_NOM/ticmaster/.venv`.
5. **Code** : *WSGI configuration file* → remplacer le contenu par :

```python
import sys, os
path = "/home/VOTRE_NOM/ticmaster"
if path not in sys.path:
    sys.path.insert(0, path)
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("COOKIE_SECURE", "1")
from wsgi import app as application
```

6. **Static files** :

| URL | Directory |
|---|---|
| `/static/` | `/home/VOTRE_NOM/ticmaster/app/static` |

7. **Reload** puis ouvrir `https://VOTRE_NOM.pythonanywhere.com`.

**Base de données** : SQLite fonctionne mais n'est pas recommandée pour un usage concurrent.
Utiliser MySQL (`mysqlclient`) ou PostgreSQL (`psycopg2-binary`) et renseigner `DATABASE_URL`
(`mysql+pymysql://…` ou `postgresql://…`).

**Tâches planifiées** (onglet Tasks) — sauvegarde quotidienne :

```bash
cd /home/VOTRE_NOM/ticmaster && sqlite3 instance/ticmaster.db ".backup backups/$(date +%F).db" \
  && tar czf backups/uploads-$(date +%F).tar.gz instance/uploads
```

---

## 5. Après le déploiement : recette rapide

| Étape | Vérification |
|---|---|
| 1 | `/sante` renvoie `{"status":"ok","database":true}` |
| 2 | `/` affiche la page publique, **aucun bouton « S'inscrire »** |
| 3 | `/auth/connexion` : connexion du super administrateur → redirection `/admin/` |
| 4 | `/admin/utilisateurs/nouveau` : création d'un apprenant, mot de passe affiché une seule fois |
| 5 | Connexion du nouvel apprenant : changement de mot de passe imposé |
| 6 | Leçon terminée, exercice corrigé, résultat visible |
| 7 | Examen : tentative de sortie d'onglet → élimination ; réaffectation par le super admin |
| 8 | Messages + battle entre deux comptes |
| 9 | `/admin/journal` : les actions ci-dessus apparaissent |
| 10 | `python seed.py reset-demo` : plus aucun compte de démonstration |

---

## 6. Mise à jour de l'application

```bash
git add .
git commit -m "Correctif"
git push origin main
```

Avec `autoDeploy: true` (render.yaml), Render redéploie automatiquement.
En cas de migration de schéma, exécuter les commandes Alembic depuis le Shell Render, puis
redémarrer le service.

---

## 7. Coûts indicatifs

| Poste | Gratuit | Recommandé |
|---|---|---|
| Render Web | 0 € (veille 15 min) | Starter ~7 $/mois |
| PostgreSQL | 0 € (30 jours) | ~7 $/mois |
| Cloudflare | 0 € (plan Free) | Pro 20 $/mois (WAF avancé) |
| Domaine `.mg` | — | 15 000–40 000 Ar/an selon registrar |
| **Total minimal** | **0 €** | **~15 $/mois** |
