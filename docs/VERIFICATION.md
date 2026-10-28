# Rapport de vérification — TIC MASTER

**Date :** 29 octobre 2026 · **Version :** commit `964d0c5` (branche `main`)
**Instance vérifiée :** locale `http://127.0.0.1:5000` (mode production, `DEBUG=off`)
**Dépôt :** <https://github.com/rzkmyazi/ticmaster>

---

## 1. Synthèse

| Contrôle | Résultat |
|---|---|
| Tests automatisés (`pytest`) | **19 / 19** |
| Vérification de bout en bout (`tools/verify.py`) | **54 / 54** |
| Pages apprenant | **15 / 15** en 200 |
| Pages administrateur | **18 / 18** en 200 |
| Permissions serveur | conformes (403 attendus) |
| Anti-fraude d'examen | conforme, sanction individuelle |
| CSRF, XSS, session, mots de passe | conformes |
| Dépôt GitHub | **105 fichiers**, aucun secret, local ↔ distant synchronisés |

Aucune régression. Aucun échec.

---

## 2. Application

### 2.1 Santé et pages publiques

| Route | Attendu | Obtenu |
|---|---|---|
| `/sante` | `{"status":"ok","database":true}` | ✔ |
| `/` | 200, aucune mention d'inscription | ✔ (0 occurrence de « s'inscrire » / « créer un compte ») |
| `/a-propos` | 200, super admin + administrateurs | ✔ |
| `/auth/connexion` | 200 | ✔ |
| `/auth/mot-de-passe-oublie` | 200 | ✔ |
| `/inscription`, `/register`, `/auth/inscription` | **404** | ✔ |

### 2.2 Espace apprenant (15 pages, HTTP 200)

`/espace` · `/cours` · `/cours/introduction-aux-tic` · `/cours/…/lecon/1` · `/exercices`
· `/exercices/1` · `/examens` · `/resultats` · `/ressources` · `/annonces` · `/historique`
· `/mon-profil` · `/utilisateurs-en-ligne` · `/messages` · `/battle`

### 2.3 Espace administrateur (18 pages, HTTP 200)

`/admin/` · `/admin/utilisateurs` · `/admin/utilisateurs/nouveau` · `/admin/utilisateurs/1`
· `/admin/modules` · `/admin/modules/1/modifier` · `/admin/lecons/1/modifier`
· `/admin/exercices` · `/admin/exercices/1/modifier` · `/admin/annonces` · `/admin/examens`
· `/admin/roles` · `/admin/journal` · `/admin/sessions` · `/admin/demandes`
· `/admin/parametres` · `/admin/sauvegardes` · `/admin/messages-utilisateurs`

---

## 3. Sécurité

| Contrôle | Attendu | Obtenu |
|---|---|---|
| Utilisateur → `/admin/` | 403 | ✔ 403 |
| Admin → `/admin/journal` | 403 | ✔ 403 |
| Admin → `/admin/messages-utilisateurs` | 403 | ✔ 403 |
| Admin → `/admin/sauvegardes` | 403 | ✔ 403 |
| Admin → modification d'un super admin | 403 | ✔ 403 |
| Admin → création d'un administrateur | refus explicite | ✔ « Seul le super administrateur… » |
| `POST` sans jeton CSRF | 400 | ✔ 400 |
| Annonce contenant `<script>` | texte échappé | ✔ `&lt;script&gt;`, brut absent |
| Déconnexion | 302 puis session invalide | ✔ `/espace` → 302 |
| Mot de passe temporaire | affiché une seule fois | ✔ |
| Changement imposé à la 1ʳᵉ connexion | redirection `/auth/changer-mot-de-passe` | ✔ |
| Mot de passe en base | Argon2id | ✔ `$argon2id$…` |
| En-têtes HTTP | CSP, `nosniff`, `SAMEORIGIN`, `Referrer-Policy`, `Permissions-Policy` | ✔ |

---

## 4. Fonctionnalités

| Domaine | Contrôle | Obtenu |
|---|---|---|
| Leçons | terminer une leçon | ✔ progression + leçon suivante |
| Exercices | correction calculée côté serveur | ✔ score et explications |
| Examens | démarrage, page surveillée, minuteur | ✔ |
| Anti-fraude | ressources techniques (CSS, favicon) | ✔ aucune pénalité (`in_progress`, 0) |
| Anti-fraude | sortie d'onglet | ✔ `eliminated`, 1 violation |
| Anti-fraude | portée de la sanction | ✔ un seul étudiant concerné |
| Réaffectation | administrateur | ✔ refusée (403) |
| Réaffectation | super administrateur | ✔ `in_progress`, violations remises à 0 |
| Messagerie | envoi / lecture / supervision | ✔ 201, 200, visible par le super admin |
| Messagerie | accès à un DM d'un tiers | ✔ 403 |
| Battle | création solo (nom = utilisateur) | ✔ |
| Battle | démarrage + question chronométrée | ✔ `running`, 19 s restantes |
| Battle | renommage d'une battle solo | ✔ 400 refusé |

---

## 5. Dépôt GitHub

| Élément | Valeur |
|---|---|
| URL | <https://github.com/rzkmyazi/ticmaster> |
| Visibilité | publique |
| Branche | `main` |
| Commits | 5 |
| Fichiers | 105 |
| Fichiers sensibles (`.env`, `*.db`, uploads) | **aucun** |
| Jetons dans l'historique | aucun (le remote est en URL propre) |
| Synchronisation | local = distant (`964d0c5`) |

---

## 6. Rejouer la vérification

```bash
# local
python tools/verify.py
pytest -q

# instance déployée (Render)
BASE=https://ticmaster.onrender.com SUPER_PASSWORD='…' python tools/verify.py
```

Le script crée un compte jetable pour les tests qui modifient l'état, puis n'altère aucun
compte de démonstration. Il retourne le nombre d'échecs (0 = conforme).

> Les comptes créés par la vérification (`verif.*`, `probe.*`, `temp.*`) ont été supprimés
> après le passage : la base ne contient plus que `Myazirzk`, `admin.demo` et `apprenant`.

---

## 7. Points d'attention relevés (sans échec)

1. **Rate limiting en mémoire** : par processus. À remplacer par Redis si plusieurs instances
   Render (documenté dans `docs/SECURITY.md` §11).
2. **Disque Render éphémère** : les fichiers téléversés sont perdus au redéploiement ; le
   contenu pédagogique, lui, reste en base. Disque persistant ou S3/R2 recommandé.
3. **Comptes de démonstration** : `python seed.py reset-demo` avant l'ouverture au public.
4. **Jeton OAuth** utilisé pour l'envoi : à révoquer sur
   <https://github.com/settings/applications> (le dépôt n'est pas affecté).

---

## 8. Vérification de l'instance de production

**URL :** <https://ticmaster.onrender.com> · **Service Render** `srv-dbh6u7jbc2fs73fohv20` (Francfort, free)
**Base :** PostgreSQL `ticmaster-db` (free) · **Déploiement :** `3fb6be4`, statut **live**

| Contrôle | Résultat |
|---|---|
| `/sante` | `{"app":"TIC MASTER","database":true,"status":"ok"}` ✔ |
| Pages publiques (`/`, `/a-propos`, `/auth/connexion`, `/auth/mot-de-passe-oublie`) | 200 ✔ |
| `/inscription`, `/register` | **404** ✔ |
| Accueil sans mention d'inscription | ✔ |
| Connexion `Myazirzk` | 302 → `/admin/` ✔ |
| 8 pages d'administration testées | 200 ✔ |
| Contenu installé automatiquement | **12 modules**, 12 exercices ✔ |
| Création de compte → mot de passe temporaire → changement imposé → accès | ✔ |
| `POST` sans jeton CSRF | 400 ✔ |
| Anonyme → `/admin/` | 302 (redirection connexion) ✔ |
| HSTS + CSP | présents ✔ |

**Incident corrigé pendant le déploiement :** SQLAlchemy 2.1 utilise par défaut le pilote
`psycopg` (v3), absent de `requirements.txt` → premier démarrage en échec
(`ModuleNotFoundError: No module named 'psycopg'`). Correctif : `config.py` force
`postgresql+psycopg2://` (pilote déjà épinglé), plus mise à jour de la variable `DATABASE_URL`.
Le déploiement suivant est passé **live** et l'amorçage a créé le super administrateur et les
12 modules dans PostgreSQL.

**État final de la base de production :** un seul compte, `Myazirzk` (super administrateur).
Les comptes de test créés par la vérification ont été supprimés.

---

## 9. Vérification de la seconde installation (PythonAnywhere)

**URL :** <https://myazirzk1.pythonanywhere.com> · compte `myazirzk1`, Python 3.12
**Base :** SQLite `~/ticmaster/instance/ticmaster.db` (indépendante de Render)

| Contrôle | Résultat |
|---|---|
| `/sante` | `{"app":"TIC MASTER","database":true,"status":"ok"}` ✔ |
| `/`, `/a-propos`, `/auth/connexion` | 200 ✔ |
| `/inscription` | **404** ✔ |
| Feuilles de style et scripts | `app.css` 76 982 o, `app.js` 14 597 o ✔ |
| Connexion `Myazirzk` | 302 → `/admin/` ✔ |
| Tableau de bord et 4 pages d'administration | 200 ✔ |
| Contenu installé | **12 modules** ✔ |
| HTTP → HTTPS | 302 vers `https://` ✔ |
| HSTS + CSP + X-Frame-Options | présents ✔ |

**Particularité :** aucun `pip install` n'a été nécessaire — Flask, Flask-SQLAlchemy,
argon2-cffi et python-dotenv sont préinstallés dans le Python 3.12 de PythonAnywhere.
Le fichier WSGI (`pythonanywhere_wsgi.py`) réalise l'amorçage au premier appel, puis
sert l'application ; il est idempotent grâce au marqueur `~/.tic_bootstrap_done`.

---

## 10. Mise à jour du 29/10/2026 — Scolarité & maintenance

### Nouvelles fonctionnalités vérifiées

| Fonction | Contrôle | Résultat |
|---|---|---|
| Mode « mise à jour du site » | interrupteur dans *Paramètres → onglet Mise à jour* ; visiteur et élève → **503** + page d'attente animée | ✔ |
| | super administrateur et administrateur → accès complet conservé | ✔ |
| | `/sante`, fichiers statiques et page de connexion toujours servis | ✔ |
| | en-tête `Retry-After: 300` + réactualisation automatique (45 s) | ✔ |
| | examen déjà commencé : l'apprenant peut terminer (aucune élimination injuste) | ✔ |
| Super administrateur = professeur | `/examens` → redirigé vers les notes des élèves | ✔ |
| | `/resultats` → redirigé vers les statistiques de la classe | ✔ |
| | démarrage d'examen refusé (**403**, contrôle serveur) | ✔ |
| Notes des élèves (`/admin/notes`) | relevé, rangs, mentions, export CSV | ✔ |
| Bulletin (`/admin/notes/<id>`) | résultats par module et par trimestre, historique | ✔ |
| Statistiques (`/admin/statistiques`) | moyenne, médiane, distribution sur 20, palmarès | ✔ |
| Permissions | utilisateur → **403**, administrateur → **403**, super administrateur → 200 | ✔ |

### Résultats des tests

- `pytest -q` → **22 tests réussis** (3 nouveaux : maintenance, réservation de la scolarité, absence d'examen du professeur).
- `tools/verify.py` contre **la production** → « tout est conforme ✔ » (66 contrôles), puis nettoyage automatique des comptes et annonces de test ; la base ne contient plus que `Myazirzk`.

### Points d'attention

- **PythonAnywhere** ne dispose pas de PostgreSQL : sa base SQLite est indépendante. Les deux instances
  ont reçu la mise à jour.
- La page d'attente est autonome (CSS et icônes intégrés) : elle s'affiche même si les feuilles de style
  ne sont pas encore rechargées.
- Un compte de démonstration n'est **pas** créé en production : les pages de notes restent vides tant
  qu'aucun élève n'est inscrit par l'administration.

---

*Rapport généré automatiquement à partir des sorties de `pytest` et `tools/verify.py`.*
