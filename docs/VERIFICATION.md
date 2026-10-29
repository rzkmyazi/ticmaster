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

## 11. Mise à jour du 29/10/2026 — Battles validées & réseau social du profil

### Nouvelles fonctionnalités vérifiées

| Fonction | Contrôle | Résultat |
|---|---|---|
| Demande de battle | élève → `POST /api/battle/create` ⇒ statut **`pending`** (aucun démarrage possible) | ✔ |
| | démarrage avant validation → **403** « doit d'abord être acceptée » | ✔ |
| | la battle n'apparaît pas dans les groupes ouverts tant qu'elle n'est pas validée | ✔ |
| Validation (`/admin/battles`) | ADMIN et SUPER ADMIN : accepter (`pending` → `lobby`) / refuser (`pending` → `refused`) | ✔ |
| | apprenant → **403** sur la page et sur les deux actions | ✔ |
| | refusée : message explicite dans la salle, impossible de démarrer | ✔ |
| Fil d'actualité (`/mon-profil`) | publication de texte, de photo ou des deux | ✔ |
| | photo : signature binaire vérifiée (un `.php` renommé `.png` → **400**), service protégé par authentification | ✔ |
| Réactions emoji | ❤️ J'aime, 😂 Rire, 👊 Bravo, 😠 Colère, 😢 Triste | ✔ |
| | une seule réaction par personne et par publication (contrainte `uq_reaction_post_user`), changement et retrait possibles | ✔ |
| | réaction inconnue → **400** | ✔ |
| Commentaires | ajout, affichage, compteur ; commentaire vide → **400** | ✔ |
| Suppression | l'auteur ou l'administration uniquement | ✔ |
| Conservation des données | champ « 0 = illimitée » ; valeurs `0`, vide, `illimite` ⇒ stockage `0` | ✔ |
| Notes individuelles /20 | tableau « Notes individuelles (sur 20) » sur le tableau de bord du super administrateur | ✔ |
| Édition des cours | super administrateur : modification d'un module et d'une leçon → **302** + données enregistrées | ✔ |
| | apprenant → **403** | ✔ |

### Déploiement

| Cible | État |
|---|---|
| GitHub `rzkmyazi/ticmaster` | commit `c00dbcd` poussé sur `main` |
| Render (principale) | déploiement `live` sur <https://ticmaster.onrender.com> — 82 contrôles conformes |
| PythonAnywhere | 21 fichiers synchronisés + rechargement (`200 OK`), `/sante` ok |

### Résultats des tests

- `pytest -q` → **32 tests réussis** (10 nouveaux : fil social, photos falsifiées, réactions, commentaires,
  suppression, médias protégés, battle en attente, acceptation/refus, conservation illimitée, notes individuelles).
- Schéma : `create_all()` idempotent au démarrage → les tables `posts`, `post_reactions` et `post_comments`
  sont créées automatiquement sur les bases déjà en service (Render et PythonAnywhere).

### Points d'attention

- Les photos sont stockées dans `instance/uploads` et servies par `/media/<fichier>` (authentification obligatoire).
- Sur l'offre gratuite de Render, le disque est **éphémère** : les photos publiées disparaissent au redéploiement.
  Pour une conservation durable, ajouter un disque persistant (`/var/data`) et pointer `UPLOAD_FOLDER` dessus.
- La validation des battles ne concerne que les demandes **des élèves** : le personnel ouvre directement un salon.

---

## 12. Mise à jour du 29/10/2026 — Rôles simplifiés & dossier scolaire de l'élève

### Nouvelles fonctionnalités vérifiées

| Fonction | Contrôle | Résultat |
|---|---|---|
| Trois rôles seulement | formulaire : `Élève`, `Admin`, `Super Admin` — aucun autre choix | ✔ |
| | libellé « Élève » partout (badges, filtres, répartition des rôles) | ✔ |
| Inscription d'un élève | nom, prénom, pseudo, nom d'utilisateur du site | ✔ |
| | numéro en classe (1-999) et niveau d'étude (liste + saisie libre) | ✔ |
| | sexe : Garçon / Fille | ✔ |
| | groupe 1, 2 ou 3 — **modifiable** depuis la fiche et le formulaire | ✔ |
| | nom complet composé automatiquement « Nom Prénom » si laissé vide | ✔ |
| Contrôles serveur | groupe 4 ou sexe inconnu ou numéro > 999 ⇒ refus, aucun compte créé | ✔ |
| Liste des utilisateurs | colonnes n°, classe, sexe ; filtres niveau et groupe ; tri par numéro | ✔ |
| Fiche élève | bloc « Dossier scolaire » + modification rapide du groupe | ✔ |
| Export CSV | colonnes nom, prénom, pseudo, numéro, niveau, sexe, groupe | ✔ |
| Profil de l'élève | carte « Ma scolarité » en lecture seule | ✔ |
| Permissions | un élève n'accède ni à la fiche d'administration ni à la route de mise à jour (403) | ✔ |
| Schéma | `ensure_schema()` ajoute les colonnes manquantes sur les bases déjà en service | ✔ |

### Résultats des tests

- `pytest -q` → **40 tests réussis** (8 nouveaux : rôles, dossier scolaire, validations, groupe modifiable,
  filtres, export CSV, profil, migration de schéma).
- `tools/verify.py` → **127 contrôles conformes** en local et en production après déploiement.

### Déploiement

| Cible | État |
|---|---|
| GitHub `rzkmyazi/ticmaster` | commit `1399259` poussé sur `main` |
| Render (principale) | déploiement `live` — 127 contrôles conformes, 0 échec |
| PythonAnywhere | 29 fichiers synchronisés + rechargement (`200 OK`), `/sante` ok |

### Points d'attention

- Les colonnes sont ajoutées **automatiquement au démarrage** (`ALTER TABLE users ADD COLUMN …`), sans perte
  de données et sans intervention manuelle sur Render ou PythonAnywhere.
- Le rôle reste stocké en base sous la valeur `user` (compatibilité) : seul le libellé affiché est « Élève ».
---

## 13. Mise à jour du 29/10/2026 — Connexion épurée, photo de profil, Bulletins, groupe (vague 4)

**Commit déployé :** `a8d78ec` · **instances :** Render, PythonAnywhere, local.

### Les quatre demandes

| Demande | Contrôle | Résultat |
|---|---|---|
| Connexion sans détail du programme | `/auth/connexion` : plus d'`auth-aside`, carte centrée (`auth-wrap--center`), lien « Programme » absent du menu public sur cet écran | ✔ |
| Photo de profil depuis la galerie | envoi réel d'un PNG via `POST /mon-profil/photo` ⇒ 302, `avatar-img` affiché, `GET /avatar/<fichier>` = 200 | ✔ |
| | photo protégée : sans session ⇒ redirection vers la connexion ; fichier inconnu ⇒ **404** | ✔ |
| | faux fichier (`<?php` renommé `.png`) refusé, photo précédente conservée | ✔ |
| | bouton « Retirer » ⇒ retour aux initiales, ancienne URL en **404** | ✔ |
| Onglet Bulletins | `/admin/bulletins` : une fiche par élève, note /20, mention, rang, modules, trimestres | ✔ |
| | lien présent dans le menu *Scolarité* du super administrateur uniquement | ✔ |
| | **403** pour un administrateur et pour un élève (page et entrée de menu) | ✔ |
| Groupe du dossier scolaire | sélecteur de groupe visible et actif pour le super administrateur | ✔ |
| | `POST /admin/utilisateurs/<id>/classe` par un **administrateur** ⇒ groupe **inchangé** (contrôle serveur) | ✔ |
| | fiche affichée en **lecture seule** (`readonly`) pour un administrateur | ✔ |
| | changement par le super administrateur ⇒ groupe mis à jour | ✔ |

### Robustesse corrigée au passage

| Sujet | Correction | Résultat |
|---|---|---|
| Suppression de compte sur SQLite | `PRAGMA foreign_keys=ON` : les `ON DELETE CASCADE` s'appliquent comme sur PostgreSQL (plus de lignes orphelines) | ✔ |
| Battle | une battle terminée/expirée ne bloque plus la création d'une nouvelle battle | ✔ |
| CSS | anciennes règles `.auth-aside` / `.auth-split` retirées (plus de styles morts) | ✔ |

### Résultats des tests

- `pytest -q` → **46 tests réussis** (4 nouveaux : connexion épurée, photo de profil, onglet Bulletins, notes réelles dans les bulletins).
- `tools/verify.py` → **150 contrôles conformes** en local, **151** sur Render et **151** sur PythonAnywhere (0 échec).

### Déploiement

| Cible | État |
|---|---|
| GitHub `rzkmyazi/ticmaster` | commit `a8d78ec` poussé sur `main` |
| Render (principale) | déploiement `live` sur `a8d78ec` — **151 contrôles conformes** |
| PythonAnywhere | **18 fichiers** synchronisés + rechargement (`200 OK`) — **151 contrôles conformes** |
---

## 14. Mise à jour du 29/10/2026 — Questions des battles & groupes libres (vague 5)

**Commit déployé :** `31fe36b` · **instances :** Render, PythonAnywhere, local.

### 14.1 Questions des battles par l'administration

| Contrôle | Résultat |
|---|---|
| Lien « Questions » présent sur chaque battle en attente pour l'administration | ✔ |
| Écran `/admin/battles/<id>/questions` accessible (admin et super admin) | ✔ |
| Formulaire « Créer une question » présent | ✔ |
| Banque de questions proposée (toutes les questions à 2 propositions et plus) | ✔ |
| Sélection de questions enregistrée et conservée au rechargement | ✔ |
| Question créée depuis l'écran **ajoutée immédiatement** à la battle | ✔ |
| Question enregistrée dans la banque « Banque de questions Battle » (brouillon, invisible des élèves) | ✔ |
| Composition interdite à un élève (**403**) | ✔ |
| Composition bloquée après le démarrage de la battle | ✔ |
| Les questions composées sont bien celles posées pendant la battle (vérifié en mode **groupe**) | ✔ |
| Nettoyage : la question de contrôle est supprimée après la vérification | ✔ |

### 14.2 Groupes libres (1 → 99)

| Contrôle | Résultat |
|---|---|
| Groupe **9** accepté par le super administrateur et affiché (« Groupe 9 ») | ✔ |
| Groupes **0**, **100** et texte refusés, groupe précédent conservé | ✔ |
| Champ de saisie numérique (`max="99"`, suggestions 1-2-3 + groupes existants) | ✔ |
| Liste de classe, filtres et export CSV suivent le groupe personnalisé | ✔ |
| Un **administrateur** ne peut toujours pas changer le groupe (lecture seule + contrôle serveur) | ✔ |

### Résultats des tests

- `pytest -q` → **48 tests réussis** (2 nouveaux : groupes libres, composition des questions).
- `tools/verify.py` → **159 contrôles conformes** en local, **160** sur Render et **160** sur PythonAnywhere (0 échec).

### Déploiement

| Cible | État |
|---|---|
| GitHub `rzkmyazi/ticmaster` | commit `31fe36b` poussé sur `main` |
| Render (principale) | déploiement `live` sur `31fe36b` — **160 contrôles conformes** |
| PythonAnywhere | **9 fichiers** synchronisés + rechargement (`200 OK`) — **160 contrôles conformes** |
---

## 15. Mise à jour du 29/10/2026 — Vue Android & connexion stable (vague 6)

**Commit déployé :** `acce003` · **instances :** Render, PythonAnywhere, local.

### 15.1 Navigation mobile

| Contrôle | Résultat |
|---|---|
| Barre d'onglets fixe présente sur les pages connectées | ✔ |
| Onglets de l'élève : Accueil, Cours, Exercices, Battle, Messages, Profil | ✔ |
| Onglet de la page courante surligné (`is-active`) | ✔ |
| Onglets propres au super administrateur (Élèves, Notes) | ✔ |
| Un administrateur n'obtient pas l'onglet « Notes » réservé au super administrateur | ✔ |
| Aucune barre d'onglets sur la page de connexion (page publique isolée) | ✔ |
| CSS : marges de sécurité, champs 16 px, `[hidden]` prioritaire, débordement maîtrisé | ✔ |

### 15.2 Mesures réelles dans un navigateur mobile (Chromium, 390 × 844, Android)

| Page | Débordement horizontal | Barre d'onglets | Onglet actif |
|---|---|---|---|
| `/auth/connexion` | 0 px | absente (normal) | — |
| `/` (accueil public) | 0 px | absente (normal) | — |
| `/espace` | 0 px | visible | Accueil |
| `/cours` | 0 px | visible | Cours |
| `/battle` | 0 px | visible | Battle |
| `/mon-profil` | 0 px | visible | Profil |
| `/admin/` | 0 px | visible | Accueil |
| `/admin/notes` | 0 px | visible | Notes |
| `/admin/bulletins` | 0 px | visible | Notes (page rattachée) |
| `/admin/utilisateurs` | 0 px | visible | Élèves |

Même mesure sur 360 × 800 (petit téléphone) et 768 × 1024 (tablette) : **0 px de débordement**.

### 15.3 Page de connexion

| Contrôle | Résultat |
|---|---|
| Clavier virtuel non imposé sur tactile (`data-autofocus` + `pointer: coarse`) | ✔ |
| Clavier « suivant » puis « go » (`enterkeyhint`) | ✔ |
| Bouton « Se connecter » du menu public masqué sur la page de connexion | ✔ |
| Logo animé visible et dimensionné (46 × 46, il était en 0 × 0) | ✔ |
| Titre et sous-titre sur une ligne, texte jamais coupé | ✔ |
| Service worker v2 : mise à jour du design dès la deuxième visite | ✔ |

### Résultats des tests

- `pytest -q` → **50 tests réussis** (2 nouveaux : barre d'onglets mobile, confort de connexion).
- `tools/verify.py` → **169 contrôles conformes** en local, **170** sur Render et **170** sur PythonAnywhere (0 échec).

### Déploiement

| Cible | État |
|---|---|
| GitHub `rzkmyazi/ticmaster` | commits `acce003` puis documentation, poussés sur `main` |
| Render (principale) | déploiement `live` — **170 contrôles conformes** |
| PythonAnywhere | **10 fichiers** synchronisés + rechargement (`200 OK`) — **170 contrôles conformes** |

---

*Rapport généré automatiquement à partir des sorties de `pytest` et `tools/verify.py`.*
