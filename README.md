# TIC MASTER — Plateforme éducative TIC

**#by_Myazirzk**

> 🌐 **Application en ligne : <https://ticmaster.onrender.com>**
> 🇲🇬 Seconde adresse (secours) : <https://myazirzk1.pythonanywhere.com>
> Dépôt : <https://github.com/rzkmyazi/ticmaster>


Application web **réellement fonctionnelle** (pas une maquette) de formation aux Technologies de
l'Information et de la Communication : cours, exercices corrigés, examens trimestriels surveillés,
battles de connaissances et messagerie interne, avec une administration complète.

> **Aucune inscription publique.** Les comptes sont créés exclusivement par l'administration.
> Le premier super administrateur est créé par une procédure d'installation en ligne de commande.

---

## 1. Fonctionnalités

| Domaine | Détail |
|---|---|
| **Authentification** | Connexion par identifiant ou e-mail, mot de passe haché **Argon2id**, sessions serveur révocables, verrouillage anti-force brute (compte + IP), messages neutres, changement de mot de passe forcé à la première connexion, mot de passe oublié validé par le super administrateur |
| **Rôles** | Trois rôles seulement : **Super Admin**, **Admin**, **Élève** — permissions vérifiées **côté serveur** à chaque requête |
| **Espace professeur** | Le super administrateur est **professeur** : il ne suit ni cours ni exercice d'élève (`/cours`, `/exercices`, `/examens`, `/resultats`, `/espace` le renvoient vers son espace). Il gère ceux des élèves : *Mes cours*, *Mes exercices*, *Ressources*, *Notes*, *Statistiques* |
| **Photo de profil** | Envoi depuis la galerie du téléphone ; l'image est **conservée dans la base** en plus du fichier — elle survit aux redéploiements et, si elle manque, les **initiales** sont dessinées à la place (jamais d'image cassée) |
| **Dossier scolaire** | À l'inscription d'un élève : **nom, prénom, pseudo, nom d'utilisateur du site, numéro en classe, niveau d'étude, sexe (garçon/fille), groupe 1 à 3 modifiable**. Filtres par niveau et par groupe, tri par numéro, export CSV, fiche de suivi |
| **Administration** | CRUD utilisateurs (identifiant unique, mot de passe temporaire affiché une seule fois, rôle, activation/suspension/désactivation, dates de création et de dernière connexion, recherche/filtres/tri, suppression avec confirmation, révocation de sessions), export CSV, journal d'audit, statistiques et graphiques |
| **Contenus** | 12 modules, 36 leçons (Markdown sécurisé, images, documents, vidéos), 6 catégories, ressources téléchargeables, exercices et examens à choix unique avec correction et explication |
| **Examens** | 3 examens trimestriels (T1, T2, T3) ; sortie d'onglet, perte de focus, sortie du plein écran, navigation hors examen ou coupure de battement de cœur ⇒ **élimination enregistrée** ; réaffectation réservée au **super administrateur**, sanction strictement individuelle |
| **Battle** | Battle **solo** (nom = nom de l'utilisateur) et **en groupe** (nom modifiable), code de salle, questions chronométrées, classement en direct, correction commentée. **La question suivante part dès que tout le monde a répondu** (20 s maximum). **Chaque demande déposée par un élève reste en attente** : seuls l'**ADMIN** et le **SUPER ADMIN** peuvent l'accepter ou la refuser (`/admin/battles`) — l'élève est prévenu aussitôt. |
| **Réseau social** | Fil d'actualité dans *Mon profil* : publication de texte et de photos (PNG, JPG, GIF, WEBP), **5 réactions emoji** (❤️ J'aime, 😂 Rire, 👊 Bravo, 😠 Colère, 😢 Triste — une seule par personne, modifiable), commentaires, suppression de ses propres publications (modération possible par l'administration) |
| **Conservation** | Durée paramétrable dans *Paramètres* : **illimitée par défaut** (`0`), aucune suppression automatique |
| **Messages transférés** | Sous chaque message, « Transférer » l'envoie vers le salon général, une classe (professeur) ou une conversation privée ; l'**auteur d'origine** reste affiché. États d'un message privé : **Envoyé → Reçu → Lu**. |
| **Messagerie** | Salon général, **messages de classe** (toute la classe, un niveau ou un groupe d'un coup, avec **accusés de lecture**) et conversations privées ; l'élève lit les messages de classe et répond en privé au professeur ; supervision intégrale par le **super administrateur** dans l'onglet « Messages des Utilisateurs » (icône rose à contour) |
| **Notifications** | Cloche en temps réel, panneau déroulant, bannière discrète, historique **filtrable par type** (messages, battles, annonces, notes, compte, système) |
| **Présence** | Utilisateurs en ligne (contour vert) / inactifs (contour rouge) dans l'onglet dédié |
| **Expérience** | Design premium bleu nuit / bleu électrique / cyan, mode sombre **et** clair, animations légères, responsive Android / iPhone / tablette / desktop, PWA installable, accessibilité (focus visibles, `prefers-reduced-motion`) |

---

## 2. Architecture

```
Navigateur (HTML/CSS/JS, aucune dépendance externe)
        │  HTTPS · cookies HttpOnly / Secure / SameSite
        ▼
Flask (application monolithe modulaire, blueprints)
   ├── Sécurité transverse : CSRF, CSP, rate limiting, sessions serveur, audit
   ├── SQLAlchemy ORM  ───────────►  SQLite (local) / PostgreSQL (production)
   └── Stockage fichiers (instance/uploads, noms aléatoires, accès authentifié)
```

Documentation complète : [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/DATABASE.md`](docs/DATABASE.md)
· [`docs/SECURITY.md`](docs/SECURITY.md) · [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) · [`docs/TESTING.md`](docs/TESTING.md).

### Arborescence

```
ticmaster/
├── app/
│   ├── __init__.py            # fabrique d'application, hooks, erreurs, CSP
│   ├── extensions.py          # SQLAlchemy
│   ├── models.py              # 20 modèles de données
│   ├── seed_content.py        # programme pédagogique (12 modules, 69 questions)
│   ├── utils.py               # slug, rendu Markdown sécurisé, uploads, pagination
│   ├── mailer.py              # envoi SMTP facultatif
│   ├── security/
│   │   ├── core.py            # sessions, CSRF, rate limiting, décorateurs de rôle
│   │   └── hashing.py         # Argon2id (repli scrypt)
│   ├── blueprints/
│   │   ├── auth.py            # connexion, déconnexion, mots de passe
│   │   ├── public.py          # accueil, à propos, /sante, PWA
│   │   ├── user.py            # espace apprenant, profil, présence, historique
│   │   ├── learning.py        # cours, leçons, exercices, résultats, fichiers
│   │   ├── exam.py            # examens surveillés (anti-fraude)
│   │   ├── social.py          # messagerie + battles
│   │   └── admin.py           # administration complète
│   ├── templates/             # base, base_public, base_exam, macros, public, auth,
│   │                          # user (20), admin (18), errors (6)
│   └── static/
│       ├── css/app.css        # design system complet
│       ├── js/app.js          # thème, menu, toasts, formulaires
│       ├── js/exam.js         # surveillance d'examen + minuteur
│       ├── js/chat.js         # messagerie (polling)
│       ├── js/battle.js       # logique des battles
│       └── img/               # logo SVG + icônes PWA (192/512/apple)
├── docs/                      # architecture, base de données, sécurité, déploiement, tests
├── tests/test_app.py          # tests automatisés (pytest)
├── config.py                  # configuration par variables d'environnement
├── seed.py                    # installation : base, super admin, contenu, démo
├── run.py / wsgi.py           # développement / production
├── requirements.txt · requirements-dev.txt
├── Procfile · render.yaml · runtime.txt
├── .env.example
└── README.md
```

---

## 3. Installation locale

**Prérequis :** Python 3.11+ (3.12 recommandé), Git.

```bash
git clone https://github.com/VOTRE_COMPTE/ticmaster.git
cd ticmaster

python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(48))"   # coller dans .env
# En local (http://) : COOKIE_SECURE=0

python seed.py init                 # tables + paramètres
python seed.py superadmin --username Myazirzk   # 1er SUPER ADMIN (mot de passe demandé en aveugle)
python seed.py seed                 # 12 modules, exercices, examens, annonces
python seed.py demo                 # (facultatif) comptes de démonstration

python run.py                       # http://127.0.0.1:5000
```

Le serveur écoute sur `0.0.0.0` : depuis un téléphone Android connecté au même Wi-Fi,
ouvrir `http://IP_DU_PC:5000`.

### Commandes

| Commande | Rôle |
|---|---|
| `python run.py` | Serveur de développement |
| `gunicorn wsgi:app -b 0.0.0.0:8000 -w 2 --threads 4` | Serveur de production local |
| `python seed.py bootstrap` | Tout-en-un idempotent (production/Render) : tables, super admin, contenu |
| `python seed.py seed` | (Re)charge le contenu pédagogique — idempotent |
| `python seed.py demo` / `reset-demo` | Crée / supprime les comptes de démonstration |
| `pytest -q` | Tests automatisés |
| `flask --app wsgi init-db` | Crée les tables via la CLI Flask |

---

## 4. Procédure de création du premier SUPER ADMIN

Aucune inscription publique n'existe. Le premier compte privilégié est créé **hors ligne** :

```bash
python seed.py superadmin --username Myazirzk --full-name "Myazirzk" --email "vous@exemple.mg"
```

- mot de passe demandé via `getpass` (aucun écho, aucun historique shell) ;
- ou fourni ponctuellement :
  ```bash
  SUPER_ADMIN_PASSWORD='MotDePasseFort!2026' python seed.py superadmin --username Myazirzk
  ```
- politique : 10 caractères minimum, majuscule, minuscule, chiffre, caractère spécial ;
- si le compte existe déjà, la commande met à jour son mot de passe et son rôle (procédure de secours).

**Aucun mot de passe n'est présent dans le code source.** `.env` n'est jamais versionné
(voir `.gitignore`) et `SUPER_ADMIN_PASSWORD` ne sert qu'à l'installation.

> Comptes de démonstration (`python seed.py demo`) : `admin.demo / AdminDemo2026!` et
> `apprenant / Apprenant2026!` — à supprimer (`reset-demo`) avant toute production.

---

## 5. Configuration (`.env`)

| Variable | Description | Défaut |
|---|---|---|
| `SECRET_KEY` | Signature des sessions Flask (**obligatoire**) | valeur de dev |
| `DATABASE_URL` | `postgresql://…` (prod) ou vide ⇒ SQLite locale | SQLite |
| `COOKIE_SECURE` | `1` en HTTPS, `0` en local | `1` en prod |
| `AUTH_SESSION_HOURS` | Durée de session | `8` |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCK_MINUTES` | Verrouillage par compte | `5` / `15` |
| `LOGIN_IP_MAX_ATTEMPTS` / `LOGIN_IP_WINDOW_MINUTES` | Limitation par IP | `12` / `10` |
| `MAX_CONTENT_MB` | Taille maximale d'un fichier | `30` |
| `PRESENCE_ONLINE_SECONDS` | Fenêtre « en ligne » | `120` |
| `MAIL_*` | SMTP facultatif (notifications) | désactivé |

Aucun secret n'est stocké en base ni dans le code.

---

## 6. Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Le guide de recette (fonctionnel + sécurité, cas attendus) est dans [`docs/TESTING.md`](docs/TESTING.md) :
contrôle d'accès, CSRF, force brute, XSS, injection, élévation de privilèges, anti-fraude d'examen,
révocation de session.

---

### Espace « chef d'établissement » (super administrateur)

Le super administrateur est **professeur de TIC**, pas apprenant : il ne passe aucun examen
et n'a pas de statistiques personnelles. À la place, il dirige la scolarité :

| Page | Contenu |
|---|---|
| **Notes des élèves** (`/admin/notes`) | Relevé complet : rang, progression, moyenne exercices/examens, note sur 20, mention, export CSV |
| **Bulletin individuel** (`/admin/notes/<id>`) | Note générale, mention, rang, résultats par module et par trimestre, historique des tentatives |
| **Statistiques de la classe** (`/admin/statistiques`) | Moyenne et médiane, distribution sur 20, mentions, résultats par module, épreuves les plus difficiles, activité sur 14 jours, palmarès et élèves à soutenir |

Ces trois pages sont protégées côté serveur : un simple administrateur ou un utilisateur reçoit un **403**.

### Messagerie de classe

*Messages → Messages de classe.* Le professeur choisit le destinataire : **toute la classe**,
un **niveau** (ex. 1ère), un **groupe** (1 à 99) ou un niveau + groupe. Un seul envoi, tous les
élèves concernés sont prévenus en temps réel.

* L'élève **ne peut pas écrire dans le salon** : il lit, et répond en **privé** au professeur
  (bouton « Répondre au professeur en privé »).
* Chaque message affiche son état : « Envoyé », « Lu », puis « **Lu par N / N** » — le nombre de
  lecteurs est rafraîchi automatiquement toutes les 12 secondes.
* Un élève d'une autre classe reçoit un **403** : l'appartenance est vérifiée côté serveur.

### Mode « mise à jour du site »

*Administration → Paramètres → onglet « Mise à jour du site »*. Un interrupteur ferme la plateforme :
les visiteurs et les élèves voient une page d'attente animée (HTTP 503, réactualisation automatique),
tandis que les administrateurs conservent l'accès. Un examen déjà commencé peut toujours être terminé.

## 7. Déploiement

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/rzkmyazi/ticmaster)

**Mise en ligne en 3 écrans, sans aucune commande** : guide illustré → [`docs/RENDER.md`](docs/RENDER.md)
Procédure détaillée (GitHub, Render, Cloudflare, PythonAnywhere) → [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
Seconde installation, gratuite, sur PythonAnywhere → [`docs/PYTHONANYWHERE.md`](docs/PYTHONANYWHERE.md)

1. **GitHub** — dépôt : <https://github.com/rzkmyazi/ticmaster>
2. **Render** — cliquer sur le bouton ci-dessus, se connecter avec GitHub, saisir
   `SUPER_ADMIN_PASSWORD` puis *Apply*. `render.yaml` crée le service web et le PostgreSQL,
   et `python seed.py bootstrap` installe automatiquement tables, super administrateur,
   12 modules et 69 questions (opération idempotente). Health check : `/sante`.
3. **Cloudflare** — domaine, proxy DNS, SSL « Full (strict) », cache `/static/*`, limitation de
   débit sur `/auth/connexion`.
4. **PythonAnywhere** — alternative documentée (WSGI + MySQL/PostgreSQL).

## 8. Limites connues et recommandations

- **Rate limiting en mémoire** : par processus. En production multi-instances, brancher Redis
  (`flask-limiter`) — voir `docs/SECURITY.md`.
- **Fichiers téléversés** : disque local. Sur Render (disque éphémère), monter un disque persistant
  ou externaliser vers S3 / Cloudflare R2.
- **Notifications e-mail** : facultatives (`MAIL_ENABLED=1`) ; sans SMTP, la récupération de mot de
  passe passe par le super administrateur (procédure intégrée).
- **Sauvegardes** : politique 3-2-1 et commandes `pg_dump` / `pg_restore` documentées dans l'espace
  admin « Sauvegardes » et dans `docs/DEPLOYMENT.md`.

---

© 2026 **TIC MASTER** — *by_Myazirzk*. Tous droits réservés.
