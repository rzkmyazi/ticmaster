# Guide de test — TIC MASTER

Deux niveaux : **tests automatisés** (`pytest`) et **recette fonctionnelle et sécurité** à dérouler
manuellement avant mise en production.

---

## 1. Tests automatisés

```bash
pip install -r requirements-dev.txt
pytest -q
```

Base SQLite en mémoire, aucune donnée réelle touchée. Couverture actuelle (19 tests) :

| Domaine | Test |
|---|---|
| Démarrage | l'application expose plus de 80 routes, tous les blueprints sont chargés |
| Inscription publique | `/inscription`, `/register`, `/auth/inscription`… renvoient **404** ; la page d'accueil ne contient ni « S'inscrire » ni « Créer un compte » |
| Santé | `/sante` renvoie `{"status": "ok"}` |
| Connexion | succès → redirection `/espace` ; échec → message **générique** ; compte inconnu → message identique ; compte suspendu → refus |
| CSRF | `POST` sans jeton → **400** |
| Déconnexion | la session est révoquée (`/espace` → 302) |
| Permissions | utilisateur → `/admin/` = **403** ; admin → journal, messages, sessions, sauvegardes = **403** ; admin → édition d'un super admin = **403** |
| Mots de passe | empreinte Argon2id, jamais en clair ; politique de robustesse appliquée |
| Force brute | limiteur : blocage au-delà du seuil |
| XSS | `<script>` échappé par le rendu de contenu ; Markdown contrôlé |
| Anti-fraude | violation ⇒ tentative `eliminated`, **aucun autre étudiant affecté** |
| Isolation | un utilisateur ne voit aucune tentative d'un autre |

Ajouter `-v` pour le détail, `--maxfail=1` pour s'arrêter au premier échec.

---

## 2. Recette fonctionnelle

Prérequis : base initialisée (`python seed.py init`, `superadmin`, `seed`, `demo`), serveur lancé.

### 2.1 Accès et authentification

| # | Action | Attendu |
|---|---|---|
| 1 | Ouvrir `/` | Page publique, **aucun bouton « S'inscrire »**, lien bleu `#by_Myazirzk` |
| 2 | Cliquer sur `#by_Myazirzk` | Page « À propos » : super admin + administrateurs |
| 3 | `/auth/connexion` | Champ identifiant/e-mail, mot de passe avec œil, indicateur de chargement, lien « Mot de passe oublié ? » |
| 4 | Mauvais mot de passe | « Identifiant ou mot de passe incorrect. » (aucun indice) |
| 5 | 5 échecs consécutifs | Verrouillage temporaire du compte (message dédié) |
| 6 | Connexion `Myazirzk` | Redirection `/admin/` |
| 7 | Connexion `apprenant` | Redirection `/espace` |
| 8 | Accès direct `/admin/` en tant qu'apprenant | **403** |
| 9 | Déconnexion | Retour à l'accueil, `/espace` inaccessible |

### 2.2 Administration des comptes (super admin)

| # | Action | Attendu |
|---|---|---|
| 10 | `/admin/utilisateurs/nouveau` | Création, mot de passe temporaire affiché **une seule fois** |
| 11 | Se connecter avec ce compte | Redirection forcée vers le changement de mot de passe |
| 12 | Changer le mot de passe | Accès à `/espace` |
| 13 | `/admin/utilisateurs` | Recherche, filtres rôle/statut, tri, pagination |
| 14 | Suspendre un compte | La connexion échoue avec le message générique |
| 15 | Réinitialiser un mot de passe | Nouveau mot de passe temporaire + sessions révoquées |
| 16 | Supprimer un compte (confirmation) | Disparition de la liste, entrée dans le journal d'audit |
| 17 | Admin simple → `/admin/journal` | **403** |
| 18 | Admin simple → création d'un admin | Refus : « Seul le super administrateur… » |

### 2.3 Contenus et apprentissage

| # | Action | Attendu |
|---|---|---|
| 19 | `/cours` | 12 modules, filtres par catégorie, recherche |
| 20 | Ouvrir un module | Leçons listées, progression 0 % |
| 21 | Terminer une leçon | Progression mise à jour, leçon suivante proposée |
| 22 | `/exercices/1` → commencer | QCM affiché ; correction **calculée côté serveur** |
| 23 | Répondre juste | Score 100 %, explications affichées |
| 24 | `/resultats` | Historique des tentatives, moyenne |
| 25 | `/mon-profil` | Informations personnelles, changement de mot de passe |
| 26 | `/annonces` | Annonces publiées par l'administration |
| 27 | `/ressources` | Téléchargements (accès authentifié) |

### 2.4 Examen trimestriel et anti-fraude

| # | Action | Attendu |
|---|---|---|
| 28 | `/examens` → commencer | Bandeau « Examen surveillé », minuteur, plein écran demandé |
| 29 | Changer d'onglet puis revenir | Message d'élimination, tentative `eliminated` |
| 30 | `/examens/resultat/<id>` | Motif d'élimination affiché, aucune note attribuée |
| 31 | `/admin/examens?status=eliminated` | Tentative visible ; bouton « Réaffecter » (super admin uniquement) |
| 32 | Réaffecter | Statut `in_progress`, violations remises à 0 |
| 33 | Vérifier un autre étudiant | Sa tentative est **intacte** |

### 2.5 Messagerie, présence, battle

| # | Action | Attendu |
|---|---|---|
| 34 | `/messages` | Salon général + conversations privées |
| 35 | Envoyer un message | Affiché immédiatement (polling), persisté |
| 36 | Accéder à un DM d'un tiers via l'API | **403** |
| 37 | `/admin/messages-utilisateurs` (super admin) | Tous les messages, icône rose à contour |
| 38 | `/utilisateurs-en-ligne` | Contour **vert** si en ligne, **rouge** sinon |
| 39 | `/battle` → créer une battle solo | Code à 6 caractères, nom = nom de l'utilisateur |
| 40 | Renommer une battle solo | Refus 400 |
| 41 | Créer une battle en groupe | Nom modifiable, participation multiple, classement |

### 2.6 Apparence

| # | Action | Attendu |
|---|---|---|
| 42 | Bouton thème | Bascule sombre ⇄ clair, mémorisée après rechargement |
| 43 | Téléphone Android / iPhone | Menu latéral, tableaux défilants, aucune barre horizontale |
| 44 | Tablette et desktop | Grilles adaptatives, sidebar fixe |
| 45 | `prefers-reduced-motion` | Animations désactivées |

---

## 3. Recette de sécurité

| # | Test | Méthode | Attendu |
|---|---|---|---|
| S1 | CSRF | `curl -X POST https://…/admin/annonces -d "title=x"` | **400** |
| S2 | XSS stocké | Annonce contenant `<script>alert(1)</script>` | Affiché en texte, jamais exécuté |
| S3 | XSS réfléchi | `/cours?q=<script>` | Échappé |
| S4 | Injection SQL | `/cours?q=' OR 1=1 --` | Aucune erreur, résultats normaux |
| S5 | Élévation de privilèges | POST sur `/admin/utilisateurs/<id>/modifier` avec `role=super_admin` en tant qu'admin | **403** |
| S6 | Modification de son rôle | Champ `role` absent du profil utilisateur | Aucun effet |
| S7 | IDOR | `/resultats/<id_d_un_autre>` | **404/403** |
| S8 | Session | Vol de cookie sans `HttpOnly` | Impossible : cookie `HttpOnly` |
| S9 | Révocation | Déconnexion puis réutilisation de l'ancien cookie | **401/302** |
| S10 | Force brute | 13 connexions échouées depuis la même IP | **429** |
| S11 | En-têtes | `curl -I https://…` | CSP, `X-Content-Type-Options`, `X-Frame-Options`, HSTS |
| S12 | Debug | Page d'erreur volontaire | Aucune trace Python exposée |
| S13 | Fichiers | `/fichiers/<nom_aléatoire>` sans session | Redirection vers la connexion |
| S14 | Mot de passe en base | `sqlite3 instance/ticmaster.db "select password_hash from users"` | `$argon2id$…` |
| S15 | Journal d'audit | Actions précédentes | `auth.login`, `auth.failed`, `user.created`, `exam.violation`, `security.forbidden` |

---

## 4. Journal des essais réalisés

| Date | Périmètre | Résultat |
|---|---|---|
| 28/10/2026 | 19 tests automatisés | **19/19** |
| 28/10/2026 | 21 pages `user/*` + 18 pages `admin/*` | **200 OK** |
| 28/10/2026 | Permissions (utilisateur, admin, super admin) | 403 conformes |
| 28/10/2026 | Exercice corrigé, examen + fraude, réaffectation | conformes |
| 28/10/2026 | Création de compte → mot de passe forcé → accès | conforme |
| 28/10/2026 | CSRF, XSS, DM interdit, renommage battle solo | conformes |

---

## 5. Scénario de bout en bout (script)

```bash
BASE=http://127.0.0.1:5000
# 1. Page publique
curl -s $BASE/ | grep -c "S'inscrire"        # → 0
# 2. En-têtes de sécurité
curl -sI $BASE/ | grep -i "content-security-policy"
# 3. Inscription publique impossible
curl -s -o /dev/null -w "%{http_code}\n" $BASE/inscription   # → 404
# 4. Santé
curl -s $BASE/sante
```
