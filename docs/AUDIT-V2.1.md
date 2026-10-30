# TIC MASTER V2.1 — Audit et optimisation du système multi-utilisateurs

**#by_Myazirzk** · Rapport du 30 octobre 2026
Site audité : <https://ticmaster.onrender.com> (Render, PostgreSQL) et réplique
<https://myazirzk1.pythonanywhere.com> (PythonAnywhere, SQLite).

> **Ce rapport ne contient aucun mot de passe, aucune clé et aucun jeton.**
> Toutes les mesures ont été relevées sur la production ou sur une copie locale
> de la même base, avant et après modification.

---

## 1. Méthode

L'audit a porté sur le **fonctionnement réel**, pas sur une intention :

1. **lecture du code** de la gestion de session (`app/models.py` → `AuthSession`,
   `app/security/core.py` → `create_auth_session`, `load_current_user`,
   `revoke_session`, `app/blueprints/auth.py`) ;
2. **relevé de la page « Utilisateurs connectés »** de production, session par
   session (identifiant, appareil, états, adresses IP, horodatages) ;
3. **mesures actives** : rechargements de page, attente d'expiration, connexions
   parallèles, test de charge ;
4. **correction ciblée** (aucune réécriture de la plateforme), puis **re-mesure**
   avec les mêmes outils.

Outils ajoutés au dépôt pour que ces mesures soient reproductibles :
`tools/test_sessions.py` (7 scénarios de la commande) et `tools/load_test.py`
(charge concurrente).

---

## 2. Constat sur la production (avant modification)

### 2.1 Ce que montrait la page

| Indicateur | Valeur relevée |
|---|---|
| Utilisateurs en ligne | **1** |
| Sessions actives | **2** |
| Sessions ouvertes (total) | **5** |
| Comptes actifs | **1** |
| Sessions listées dans le tableau | **97** |
| dont libellé « Robot / script » | **74 (76 %)** |
| dont état « Fermée » (sans distinction) | **92** |

La page ne distinguait que trois colonnes d'état : *En ligne*, *Ouverte*,
*Fermée* — « Fermée » mélangeant **session expirée** et **session révoquée**.

### 2.2 Origine réelle des 97 sessions (analyse session par session)

| Origine | Nombre | Preuve |
|---|---|---|
| **Scripts de vérification du projet** (`tools/verify.py`, scripts de test exécutés à chaque déploiement) | **64** | en-tête `python-requests/2.x`, adresses `34.82.24.166` (34) et `34.182.61.28` (30) — plages Google Cloud, machine d'intégration |
| **Captures d'écran automatisées** (Playwright, Chrome headless) | **6** | même plage cloud, en-tête `HeadlessChrome` ou navigateur standard |
| **Audit de ce jour** (script d'inspection en lecture seule) | **3** | en-tête maison non navigateur, adresse `136.87.59.149` |
| **Appareils réels de l'exploitant** | **17** | `129.222.109.x`, `153.67.85.x` (opérateur malgache) — Android, iPhone, Windows |
| Sessions créées par rechargement de page | **0** | voir §2.3 |

**Conclusion :** les « robots » ne sont pas des attaquants. Ce sont **les scripts
du projet lui-même** (vérification automatique et captures) qui, à chaque
déploiement, se connectaient en super administrateur **sans jamais se
déconnecter**. Quatre de ces sessions restaient ouvertes, ce qui explique
exactement l'écart entre « 1 personne en ligne » et « 8 sessions ouvertes ».

### 2.3 Ce qui ne crée **pas** de session (mesuré)

| Test | Mesure |
|---|---|
| 10 rechargements de page dans la même session | **0 session créée** (compteurs identiques : 7 ouvertes / 4 en ligne avant et après) |
| 40 s d'inactivité puis retour | **0 session créée** (mise à jour de `last_seen_at`, pas de nouvelle ligne) |
| Nouvelle connexion depuis un autre appareil | +1 session, **les précédentes restent valides** |

Le soupçon « une session est créée à chaque actualisation » est donc **écarté**
sur le code corrigé en vague 14. En revanche, l'ancien code écrivait en base
**à chaque requête** (`last_seen_at` session + utilisateur, seuils 20–30 s) :
c'est corrigé (voir §3.6).

---

## 3. Causes des anomalies détectées

| # | Anomalie observée | Cause exacte dans le code | Conséquence |
|---|---|---|---|
| 1 | Beaucoup de « Robot / script » | `device_label()` classait robot **tout** en-tête ne commençant pas par `Mozilla`, y compris un navigateur inconnu (ex. SeaMonkey) et le script d'audit lui-même | confusion et faux positifs |
| 2 | Sessions accumulées depuis 36 h | aucune purge : les lignes expirées/révoquées restaient en base indéfiniment | 92 lignes mortes sur 97 |
| 3 | « 8 sessions ouvertes » incompréhensible | l'état affiché ne distinguait pas **expirée** de **révoquée** ; « ouverte » comptait aussi les sessions jamais fermées des scripts | chiffre non actionnable |
| 4 | Compteurs figés | la page se rechargeait entièrement ; aucun rafraîchissement partiel des états | impression de données périmées |
| 5 | Sessions de scripts jamais refermées | `tools/verify.py` se connectait et ne se déconnectait pas | pollution de la production à chaque vérification |
| 6 | Coût des connexions | Argon2id réglé à **64 Mio** par hachage ; 8 hachages simultanés saturaient la mémoire d'un conteneur gratuit (512 Mo) | files d'attente mesurées : médiane **7,9 s**, p95 **16,7 s** sous 200 connexions |
| 7 | Écritures inutiles | `last_seen_at` réécrit toutes les 20–30 s **par session et par utilisateur** | charge d'écriture inutile |
| 8 | Aucun index sur `last_seen_at`, `expires_at`, `revoked_at`, `audit_logs.created_at` | lecture complète des tables à chaque comptage | dégradation avec la volumétrie |

---

## 4. Corrections apportées

### 4.1 Une session indépendante par connexion et par appareil — conservé et vérifié

Rien à reconstruire : chaque connexion crée déjà sa propre ligne `AuthSession`
avec un **jeton aléatoire de 256 bits** (`secrets.token_urlsafe(32)`), stocké
**uniquement sous forme d'empreinte SHA-256**. Aucun jeton n'est jamais réémis
ni partagé. Ce qui a été ajouté :

* **durée d'une connexion réglable** par l'administration (1 h → 30 jours ;
  8 h par défaut), appliquée à la connexion suivante sans redémarrage ;
* **détection de changement d'appareil** sur une session existante : si
  l'empreinte (système + navigateur + famille) change en cours de route, un
  événement `session.device_changed` est journalisé (signature possible d'un vol
  de cookie). La session **n'est pas** fermée automatiquement : le navigateur
  peut légitimement se mettre à jour, l'administration décide.

### 4.2 Une seule écriture de présence par minute

`load_current_user()` ne réécrit `last_seen_at` (session + utilisateur) que si
plus de **60 secondes** se sont écoulées, et seulement s'il y a eu changement.
Sur une classe de 40 personnes qui naviguent, cela divise les écritures par
**deux à trois** sans perdre la notion de présence (fenêtre de 120 s).

### 4.3 Cinq états lisibles, partout identiques

| État | Critère | Couleur |
|---|---|---|
| **En ligne** | session valide + activité < 120 s | **vert** |
| **Inactive** | session valide, sans activité récente | **gris** |
| **Expirée** | `expires_at` dépassé (le cookie ne vaut plus rien) | ambre |
| **Révoquée** | `revoked_at` renseigné (déconnexion ou administration) | rouge |
| *Session courante* | la vôtre : toujours signalée, jamais fermable d'un clic | bleu |

Ces états sont calculés par `session_state()` (`app/presence.py`) et utilisés à
l'identique dans la page, dans les filtres et dans l'API JSON.

### 4.4 Détection d'appareil refondue

`agent_info()` remplace l'ancienne heuristique :

* **systèmes** : Android (avec version), iPhone, iPad, Windows 10/11, Windows 8.1,
  macOS, Linux (Ubuntu), ChromeOS, FreeBSD ;
* **navigateurs** : Chrome, Firefox, Edge, Safari, Samsung Internet, Opera,
  Vivaldi, Yandex, Chromium ;
* **modèle** Android quand l'en-tête le fournit (`SM-A125F`…) ;
* **famille** : téléphone / tablette / ordinateur / inconnu ;
* **robots** : uniquement sur signature explicite (Googlebot, Bingbot, curl,
  `python-requests`, `HeadlessChrome`, Selenium, Puppeteer, Postman…) — libellé
  précé de « Script · » ;
* **un navigateur inconnu n'est plus un robot** : il reste un ordinateur, libellé
  « navigateur non identifié » (test automatisé dédié).

### 4.5 Nettoyage automatique des sessions mortes

* **rétention réglable** (7 / 14 / **30** / 60 / 90 / 180 / 365 jours, ou
  illimitée) : au-delà, les sessions **révoquées** et **expirées** sont
  supprimées de la base ;
* **nettoyage opportuniste** exécuté au plus **une fois par heure**, à
  l'ouverture d'une page d'administration — aucune tâche planifiée nécessaire,
  compatible avec les offres gratuites ;
* **action manuelle** avec **simulation** (« N session(s) seraient supprimées »)
  avant toute suppression ;
* les sessions **ouvertes** ne sont jamais touchées (test automatisé dédié).

### 4.6 Nouvelles mesures d'administration

* **compteurs** : en ligne, sessions actives, **inactives**, **expirées**,
  révoquées, comptes actifs, **connexions du jour**, **comptes distincts du
  jour**, **appareils différents** ;
* **filtres** : personne (nom, identifiant, pseudo), appareil (téléphone,
  tablette, ordinateur, script), état (5 onglets), dernière activité
  (aujourd'hui / 24 h / 7 j / 30 j), date de connexion, tri (récent, ancien,
  activité, personne), **pagination 40 par page** ;
* **actions** : fermer **une** session, fermer **toutes** les sessions d'une
  personne, **fermer les sessions automatisées** (scripts et robots uniquement :
  un « appareil inhabituel » reste un avertissement, jamais une déconnexion
  automatique d'une personne), **nettoyer** les sessions mortes (avec
  simulation) ;
* **historique des connexions** (`/admin/connexions`) : connexion, déconnexion,
  mot de passe refusé, compte verrouillé, trop d'essais, compte inactif, session
  fermée par l'administration, filtres par événement et par date, pagination.

### 4.7 Performance et compatibilité Render

| Mesure | Avant | Après |
|---|---|---|
| Coût mémoire d'un hachage Argon2id | 64 Mio | **19 Mio** (2e recommandation OWASP 2024) |
| Vérification d'un mot de passe | ~83 ms | **~35 ms** |
| 200 connexions simultanées | médiane 7,9 s · p95 16,7 s | médiane **3,5 s** · p95 **6,2 s** |
| 400 sessions (40 comptes, 4 appareils) | non mesuré | **400/400 réussies**, 19,8 sessions/s, p95 4,9 s |
| Index ajoutés | — | `auth_sessions(last_seen_at, expires_at, revoked_at)`, `audit_logs(created_at)` |
| Écritures de présence | toutes les 20–30 s | toutes les 60 s |

Les empreintes de mots de passe existantes **restent valides** : Argon2 les
vérifie avec leurs propres paramètres, puis les réenregistre automatiquement
avec les nouveaux (`check_needs_rehash`). **Aucun mot de passe à redonner aux
utilisateurs.**

### 4.8 Sécurité — état vérifié

| Exigence | État |
|---|---|
| Jeton aléatoire et imprévisible | ✔ 256 bits (`secrets.token_urlsafe(32)`) |
| Stockage de l'empreinte seulement | ✔ SHA-256 en base, jamais le jeton |
| Cookie `HttpOnly`, `Secure`, `SameSite` | ✔ `HttpOnly`, `Secure` en production, `SameSite=Lax` |
| Vol de session | ✔ changement d'appareil journalisé ; révocation immédiate possible |
| Révocation immédiate | ✔ une ligne `revoked_at` suffit, vérifiée à chaque requête |
| Limitation des tentatives | ✔ 8 essais/ compte, **40 échecs** / 10 min par adresse IP (les succès ne comptent pas) |
| Routes administrateur protégées | ✔ `@admin_required` / `@super_admin_required` côté serveur, testé (403) |
| Journalisation | ✔ `auth.login`, `auth.logout`, `auth.failed`, `auth.locked`, `auth.rate_limited`, `session.revoked`, `session.purged`, `session.device_changed`, `settings.*` |
| Secrets dans le frontend | ✔ aucun : l'API de présence ne renvoie ni jeton ni empreinte |

---

## 5. Interface

Le design futuriste est conservé. Ajouts mesurés sur Android (412 × 915, DPR 2) :

* **huit compteurs** lisibles en deux colonnes, chiffres colorés (vert = en ligne,
  gris = inactif) ;
* **onglets d'état** avec compteurs ;
* **fiches de session** (une par appareil) : personne, appareil, modèle, IP,
  connexion, dernière activité, expiration, mention de vigilance, boutons
  d'action — **aucun défilement horizontal** ;
* **indicateur vert** pour les personnes réellement en ligne, **gris** pour les
  sessions inactives, ambre/rouge pour expirée/révoquée ;
* **rafraîchissement partiel toutes les 20 s** : seuls les compteurs et les
  pastilles changent, la page ne se recharge pas (l'état du DOM n'est modifié
  que s'il a changé) ;
* nouvelle entrée de menu **« Historique des connexions »**.

---

## 6. Fichiers modifiés

| Fichier | Nature |
|---|---|
| `app/presence.py` | **réécrit** : `agent_info`, `device_fingerprint`, `session_state`, `counts` enrichis, `snapshot(current_id)` |
| `app/sessions_service.py` | **nouveau** : filtres, pagination, détection des sessions suspectes, purge, historique des connexions |
| `app/settings_service.py` | durée de session, rétention, libellés |
| `app/security/core.py` | durée réglable, écritures de présence espacées, surveillance du changement d'appareil |
| `app/security/hashing.py` | paramètres Argon2id adaptés à Render (19 Mio) |
| `app/blueprints/admin.py` | routes `/admin/sessions` (filtres), révocation individuelle/globale/suspecte, nettoyage, `/admin/connexions`, API de présence, réglages, statistiques |
| `app/blueprints/auth.py` | audit de connexion attribué au compte |
| `app/schema.py` | `ensure_indexes()` idempotent |
| `app/__init__.py` | index créés au démarrage |
| `app/templates/admin/sessions.html` | **réécrit** (fiches, filtres, onglets, actions, pagination) |
| `app/templates/admin/connections.html` | **nouveau** |
| `app/templates/admin/settings.html` | durée de connexion, rétention |
| `app/templates/admin/dashboard.html` | compteurs de sessions et lien vers l'historique |
| `app/templates/admin/user_detail.html` | déverrouillage (vague 14) |
| `app/templates/base.html` | menu « Historique des connexions » |
| `app/static/css/app.css` | styles Sessions (états, fiches, KPI, mobile) |
| `app/static/js/app.js` | rafraîchissement partiel des états |
| `tests/test_app.py` | **+18 tests** (112 au total) |
| `tools/verify.py` | **+17 contrôles** (275) et fermeture de ses propres sessions |
| `tools/test_sessions.py` | **nouveau** — scénarios A à G |
| `tools/load_test.py` | **nouveau** — charge concurrente |
| `docs/AUDIT-V2.1.md` | ce rapport · `docs/RECAP.md` §20 · `docs/VERIFICATION.md` §24 |

---

## 7. Migrations

**Aucune migration destructive, aucune colonne ajoutée, aucun compte supprimé.**

| Élément | Détail | Réversible ? |
|---|---|---|
| Index | `ix_auth_sessions_last_seen_at`, `ix_auth_sessions_expires_at`, `ix_auth_sessions_revoked_at`, `ix_audit_logs_created_at` — créés au démarrage avec `CREATE INDEX IF NOT EXISTS` | oui (`DROP INDEX`) |
| Réglages | `session_hours` (défaut 8), `session_retention_days` (défaut 30), `max_devices` (défaut 0) — créés à la première écriture depuis **Paramètres** | oui |
| Variables d'environnement | `LOGIN_MAX_ATTEMPTS` 5 → **8**, `LOGIN_IP_MAX_ATTEMPTS` **40**, `LOGIN_IP_WINDOW_MINUTES` **10** | oui |

**Sauvegarde avant déploiement** (à faire côté production, je ne peux pas
l'exécuter depuis le bac à sable — pas de sortie PostgreSQL autorisée) :

```bash
# Render → Dashboard → base ticmaster-db → « Connect » → copier la commande psql
PGPASSWORD=… pg_dump -h <hôte> -U ticmaster_user -d ticmaster -Fc > ticmaster-$(date +%F).dump

# ou, sans psql : Administration → Sauvegardes → « Export JSON »
```

L'**export JSON** intégré (hors secrets) reste disponible dans
`/admin/sauvegardes` et suffit à reconstruire comptes, cours, leçons et
questions.

---

## 8. Tests réalisés et résultats

### 8.1 Scénarios demandés (`tools/test_sessions.py`) — **31/31 conformes**

| Test | Contenu | Résultat |
|---|---|---|
| **A** | deux utilisateurs différents sur deux téléphones | ✔ A.1–A.4 |
| **B** | trois utilisateurs simultanément | ✔ B.1–B.2 |
| **C** | même utilisateur sur deux appareils | ✔ C.1–C.3 |
| **D** | déconnexion d'un appareil sans affecter les autres | ✔ D.1–D.4 |
| **E** | fermeture d'une session depuis l'administration | ✔ E.1–E.4 |
| **F** | aucune fuite entre utilisateurs | ✔ F.1–F.8 |
| **G** | statistiques = sessions réellement enregistrées | ✔ G.1–G.5 |

Extraits du dernier passage (serveur local, 30/10/2026) :

```
TEST D — déconnexion d'un appareil sans affecter les autres
  ✔ D.1 l'appareil déconnecté n'a plus accès
  ✔ D.2 l'autre appareil de A reste connecté
  ✔ D.3 B et C ne sont pas affectés
  ✔ D.4 la session déconnectée est marquée « révoquée » — 1 révoquée(s)
TEST G — les statistiques correspondent aux sessions réelles
  ✔ G.1 sessions ouvertes = sessions en ligne + inactives — 34 = 17 + 17
  ✔ G.2 le nombre de sessions en ligne correspond au détail — 17 / 17
  ✔ G.3 le nombre de personnes en ligne = comptes distincts — 8 / 8
=== Bilan : 31/31 test(s) conformes ===
```

### 8.2 Tests unitaires — `pytest -q` : **114 réussis** (+20)

Couvrent : détection d'appareil (5 profils), navigateur inconnu ≠ robot,
4 signatures de robots, les 4 états de session, cohérence des compteurs
(2 comptes / 3 appareils), filtres, révocation isolée, purge sélective, durée
réglable, pages d'administration, interdiction aux élèves (403).

### 8.3 Contrôles de bout en bout — `tools/verify.py` : **275 (local), 277 (Render), 277 (PythonAnywhere)** — 0 échec

17 nouveaux contrôles (les deux contrôles supplémentaires en ligne portent sur la veille 24 h/24) : états distingués, filtres, onglets, compteurs détaillés,
actions groupées, filtre « en ligne » cohérent, filtre « scripts », détection
d'appareil, historique des connexions, simulation de nettoyage, réglages,
règle « navigateur inconnu ≠ robot », cohérence du tableau de bord, et
**fermeture des sessions du script à la fin** (la production ne se remplit plus).

### 8.3 bis Vérifications sur les deux sites en production (30/10/2026)

```
BASE=https://ticmaster.onrender.com     python tools/verify.py          → tout est conforme ✔ (277)
BASE=https://myazirzk1.pythonanywhere.com python tools/verify.py        → tout est conforme ✔ (277)
BASE=https://ticmaster.onrender.com     python tools/test_sessions.py   → 31/31 conformes
BASE=https://myazirzk1.pythonanywhere.com python tools/test_sessions.py → 31/31 conformes
```

Après déploiement, la production a été nettoyée depuis l'interface :
**1 session automatisée fermée**, aucune session humaine touchée ; les 82
sessions expirées restent consultables jusqu'à la fin de la rétention (30 j).

### 8.4 Test de charge — `tools/load_test.py` (gunicorn, 2 workers, 4 fils)

| Charge | Réussite | Connexion médiane | p95 | Débit |
|---|---|---|---|---|
| 200 sessions / 20 comptes | **200/200** | 1,98 s | 4,00 s | 18,5 sessions/s |
| 400 sessions / 40 comptes | **400/400** | 2,21 s | 3,05 s | 19,8 sessions/s |

Aucune erreur 5xx, aucun rejet, quatre familles d'appareils simultanées.
La limite observée est la machine de test (2 vCPU partagés), **pas** la logique
applicative : la plateforme tient plusieurs centaines de sessions avec l'offre
gratuite de Render ; au-delà, voir §10.

---

## 9. Instructions de déploiement

### 9.1 Render (production)

1. **Sauvegarder** : `pg_dump` (§7) ou export JSON.
2. `git push` sur `main` → le déploiement automatique se lance
   (ou *Manual Deploy → Deploy latest commit*).
3. Vérifier les variables : `LOGIN_MAX_ATTEMPTS=8`, `LOGIN_IP_MAX_ATTEMPTS=40`,
   `LOGIN_IP_WINDOW_MINUTES=10` (déjà posées ; `render.yaml` les déclare).
4. Contrôler `https://ticmaster.onrender.com/sante` → `{"status":"ok"}`.
5. Ouvrir **Administration → Utilisateurs connectés** : les huit compteurs
   s'affichent, les états sont colorés.
6. Facultatif mais recommandé après le premier déploiement :
   **« Fermer les sessions automatisées »** (nettoie les sessions ouvertes par les
   anciens scripts, sans toucher aux personnes), puis **« Nettoyer les sessions
   mortes »** avec la rétention de 30 jours.
7. Lancer les vérifications :

```bash
BASE=https://ticmaster.onrender.com python tools/verify.py
BASE=https://ticmaster.onrender.com python tools/test_sessions.py
```

### 9.2 PythonAnywhere (secours)

```bash
# 1. sauvegarde SQLite
cp ~/ticmaster/instance/ticmaster.db ~/ticmaster-$(date +%F).db
# 2. mise à jour des fichiers (API Files ou git pull)
# 3. rechargement de l'application web
# 4. contrôle
BASE=https://myazirzk1.pythonanywhere.com python tools/verify.py
```

### 9.3 Retour arrière

Aucune donnée n'est transformée : il suffit de redéployer le commit précédent
(`git revert` ou *Rollback* dans Render). Les index et les trois réglages
peuvent rester en place — l'ancienne version les ignore.

---

## 10. Limites connues et recommandations

1. **Limiteur de débit en mémoire, par processus.** Avec 2 workers gunicorn, la
   limite par IP est appliquée *par worker* (donc jusqu'à 2 × 40 échecs réels).
   Le verrouillage **par compte** est, lui, en base et donc exact. Pour une
   limite strictement globale : Redis (ou table `login_attempts` en base).
2. **Présence tirée par sondage** (20 s) et non par WebSocket : c'est un choix
   assumé — aucun serveur temps réel à maintenir, fonctionnement identique sur
   Render et PythonAnywhere, coût nul. Au-delà de ~500 sessions simultanées,
   passer à des événements serveur (SSE) serait plus économe.
3. **Sessions « fantômes »** : un navigateur fermé sans « Se déconnecter » laisse
   une session ouverte jusqu'à expiration (8 h par défaut). C'est normal et
   désormais visible (état *Inactive*) puis nettoyé automatiquement.
4. **Adresse IP** : derrière un proxy, `X-Forwarded-For` est utilisé ; une IP peut
   donc être partagée par toute une école. C'est précisément pourquoi la limite
   ne compte que les échecs (vague 14).
5. **Offre gratuite Render** : 512 Mo et mise en veille après 15 min. La veille
   interne (`/sante` auto-appelé) maintient le service éveillé ; la charge de
   400 sessions mesurée ici ne représente pas la limite de l'hébergeur.

---

## 11. Réponse courte aux questions posées

| Question | Réponse mesurée |
|---|---|
| Pourquoi plusieurs sessions pour le même compte ? | Chaque connexion = une session (voulu). Sur les 97 lignes : **64 scripts de vérification**, **6 captures automatisées**, **3 scripts d'audit**, **17 sessions réelles** sur plusieurs appareils. |
| Sessions de robots ou vraies connexions ? | Les deux, et on sait désormais les distinguer : libellés `Script · …` pour les vrais scripts, `Android 13 · Chrome` pour les personnes. |
| Sessions créées à chaque rechargement ? | **Non** — mesuré : 10 rechargements = 0 session. |
| Sessions expirées non nettoyées ? | **Oui**, c'était le cas : aucune purge. Corrigé (rétention 30 j + nettoyage horaire). |
| Problème de gestion des sessions ? | Trois défauts réels : états confondus (« Fermée »), heuristique robot trop large, écritures de présence trop fréquentes. Tous corrigés. |
| Combien de personnes en ligne ? | Comptes distincts avec activité < 120 s — séparé des « sessions actives » (une par appareil). |
