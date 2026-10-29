# Architecture — TIC MASTER

## 1. Vue d'ensemble

Application **monolithe modulaire Flask** (pattern application factory + blueprints), volontairement
simple à déployer et à maintenir par un développeur débutant, sans sacrifier la sécurité.

```
┌──────────────────────────────────────────────────────────────────┐
│                         Navigateur (mobile / desktop)            │
│  HTML sémantique · CSS design system · JS vanilla (aucune dep.)  │
└───────────────┬──────────────────────────────────────────────────┘
                │ HTTPS · cookie de session HttpOnly + Secure
┌───────────────▼──────────────────────────────────────────────────┐
│                            Flask                                 │
│  before_request : chargement utilisateur · CSRF · garde examen   │
│  after_request  : CSP · X-Frame-Options · HSTS · Cache-Control   │
│                                                                  │
│  Blueprints                                                     │
│   auth · public · user · learning · exam · social · admin        │
│                                                                  │
│  Couche sécurité (app/security)                                 │
│   hashing Argon2id · sessions serveur · rate limiting · audit    │
└───────────────┬──────────────────────────────┬───────────────────┘
                │ SQLAlchemy ORM               │ fichiers
        ┌───────▼────────┐             ┌───────▼──────────────┐
        │ SQLite /       │             │ instance/uploads      │
        │ PostgreSQL     │             │ (noms aléatoires,     │
        │ 20 tables      │             │ accès authentifié)    │
        └────────────────┘             └───────────────────────┘
```

## 2. Choix technologiques

| Choix | Justification |
|---|---|
| **Flask 3** | Courbe d'apprentissage douce, écosystème mature, déploiement économique |
| **SQLAlchemy 2 + Flask-SQLAlchemy** | ORM ⇒ requêtes paramétrées par défaut (anti-injection SQL), migration SQLite → PostgreSQL sans changement de code |
| **SQLite (dev) / PostgreSQL (prod)** | Prototype immédiat, production robuste et sauvegardable |
| **Jinja2** | Échappement automatique HTML (anti-XSS), héritage de templates |
| **JS vanilla** | Zéro dépendance CDN : chargement rapide, aucune surface d'attaque tierce, compatible CSP stricte |
| **Gunicorn** | Serveur WSGI de production, compatible Render / PythonAnywhere |
| **Argon2id** | Recommandation OWASP pour le stockage des mots de passe (repli scrypt si indisponible) |

## 3. Organisation du code

```
requête HTTP
   │
   ├─ before_request  (app/__init__.py)
   │    1. génération du nonce CSP
   │    2. chargement de l'utilisateur depuis le cookie serveur
   │    3. validation CSRF (toute méthode mutante)
   │    4. redirection si changement de mot de passe obligatoire
   │
   ├─ before_app_request (blueprints/exam.py) : garde anti-fraude
   │    — uniquement si un examen est « in_progress »
   │
   ├─ vue du blueprint
   │    ├─ décorateurs : @login_required, @admin_required, @super_admin_required
   │    ├─ validation des entrées (serveur)
   │    ├─ opérations ORM
   │    └─ log_audit() pour les actions sensibles
   │
   └─ after_request : en-têtes de sécurité + nonce
```

### Répartition des blueprints

| Blueprint | Préfixe | Contenu |
|---|---|---|
| `auth` | `/auth` | connexion, déconnexion, mot de passe oublié/reset, changement |
| `public` | `/` | **accueil avec connexion intégrée**, `/decouvrir`, **à propos (#by_Myazirzk)**, `/sante`, manifest, service worker |
| `user` | `/espace`… | tableau de bord apprenant, profil, historique, présence |
| `learning` | `/cours` `/exercices` | catalogue, leçons, progression, exercices, résultats, ressources |
| `exam` | `/examens` | examens trimestriels, heartbeat, violations, correction |
| `social` | `/messages` `/battle` | messagerie, battles solo/groupe |
| `admin` | `/admin` | utilisateurs, rôles, contenus, annonces, supervision, audit, paramètres |

## 4. Flux d'authentification

```
POST /            (formulaire de l'accueil)   ou   POST /auth/connexion
  └─ même fonction serveur `attempt_login()` (app/blueprints/auth.py)
  1. limitation par IP (compteur mémoire)  ──► 429 si dépassement
  2. recherche par identifiant OU e-mail
  3. si compte inconnu : vérification d'un hash factice (temps constant)
  4. si compte verrouillé : message temporisé
  5. vérification Argon2id ; échec ⇒ failed_attempts++
       ≥ 5 échecs ⇒ locked_until = now + 15 min
  6. succès ⇒ création d'une ligne auth_sessions :
       - jeton aléatoire 256 bits envoyé au client (cookie HttpOnly)
       - SHA-256 du jeton stocké en base (jamais le jeton en clair)
       - expires_at = now + AUTH_SESSION_HOURS (8 h)
         ou + AUTH_REMEMBER_HOURS (30 j) si « Se souvenir de moi » est coché
  7. régénération du jeton CSRF (anti-fixation de session)
  8. redirection : /admin (admin) ou /espace (utilisateur)
```

Chaque requête suivante : `load_current_user()` valide le cookie, la session (non révoquée, non
expirée) et le statut du compte, puis met à jour `last_seen_at` (présence).

**Révocation** : `revoke_all_sessions()` invalide toutes les sessions d'un utilisateur (suspension,
réinitialisation de mot de passe, changement de mot de passe, action admin).

## 5. Modèle de permissions

| Action | Super Admin | Admin | Utilisateur |
|---|:--:|:--:|:--:|
| Créer / modifier des cours | ✅ | ✅ | ❌ |
| Créer des exercices et examens | ✅ | ✅ | ❌ |
| Créer des comptes utilisateurs | ✅ | ✅ | ❌ |
| Créer / modifier des comptes ADMIN | ✅ | ❌ | ❌ |
| Attribuer le rôle SUPER ADMIN | ✅ | ❌ | ❌ |
| Supprimer un ADMIN | ✅ | ❌ | ❌ |
| Voir tous les messages | ✅ | ❌ | ❌ |
| Réaffecter un examen éliminé | ✅ | ❌ | ❌ |
| Journal d'audit / sessions / sauvegardes | ✅ | ❌ | ❌ |
| Cours, exercices, examens, battles | ✅ | ✅ | ✅ |

Application : décorateurs côté serveur **et** vérifications d'appartenance sur les ressources
(`_own_attempt`, `can_access_room`, `can_manage_user`). L'interface masque les entrées non
autorisées, mais **le serveur refuse toujours l'action** même si l'URL est saisie directement.

## 6. Anti-fraude des examens

Trois couches complémentaires :

1. **Client** (`static/js/exam.js`) : `visibilitychange`, `pagehide` (`sendBeacon`), sortie du
   plein écran, clic sur un lien, `popstate`, `beforeunload`, battement de cœur toutes les 15 s.
2. **Serveur — API** : `POST /api/exam/<id>/violation` et `POST /api/exam/<id>/heartbeat`
   incrémentent `attempt.tab_violations` ; au-delà de `exercise.max_tab_violations` ⇒
   `status = eliminated`.
3. **Serveur — navigation** : `before_app_request` détecte toute navigation HTML hors de
   `/examens` pendant une tentative active ⇒ violation. Les fichiers techniques (statiques,
   favicon, manifest, service worker, `/sante`) et les API sont explicitement exemptés pour éviter
   les faux positifs.

Une élimination ne concerne **que** la tentative de l'étudiant concerné. Seul le **super
administrateur** peut réaffecter : `status → in_progress`, compteurs remis à zéro, chronomètre
relancé, réponses supprimées, action journalisée.

## 7. Contenus pédagogiques

- `Module` → `Lesson` (contenu Markdown simplifié rendu **100 % échappé**) → `Resource`
  (fichier ou lien) et `Exercise` (`kind=exercise|exam`) → `Question` → `Option` (une correcte).
- La correction est **toujours** effectuée côté serveur ; les bonnes réponses ne sont jamais
  envoyées au navigateur avant validation.
- `LessonProgress` alimente la progression (leçon terminée / total publié) et les statistiques.
- `seed_content.py` contient 12 modules, 69 questions d'exercices, 3 examens trimestriels et 3 annonces.

## 8. Présence et messagerie

- `last_seen_at` mis à jour à chaque requête (throttle 20 s) ; « en ligne » = vu dans les 120 s.
- Messages stockés avec `room` : `general` ou `dm:<min>:<max>` ; l'accès à une conversation privée
  est validé par appartenance. Le super administrateur voit toutes les conversations dans
  `/admin/messages-utilisateurs`.
- Le client interroge `/api/messages` toutes les 4 s (polling simple, sans WebSocket).

## 9. Battle

- `BattleRoom` (mode solo/groupe, code à 6 caractères, questions tirées au hasard),
  `BattleMember` (score, index de question répondu).
- Avancement des questions **autoritaire côté serveur** : à chaque `/api/battle/state`, si le délai
  est écoulé, l'index est incrémenté. Impossible de accélérer ou de tricher côté client.
- Le nom d'un battle solo est forcément le nom de l'utilisateur ; seul un groupe peut être renommé.

## 10. Performance

- Aucune ressource externe (CSS/JS/polices) ⇒ pas de blocage réseau tiers.
- En-têtes `Cache-Control: no-store` sur le HTML, cache long sur les statiques (via proxy).
- Index SQL sur les colonnes filtrées (`username`, `role`, `status`, `created_at`, `room`…).
- Requêtes agrégées pour les statistiques du tableau de bord.
- Rendu serveur : première peinture rapide, pas de framework JS à télécharger.

## 11. Évolutions possibles

- Redis + `flask-limiter` pour un rate limiting multi-instances.
- WebSocket (Socket.IO) pour la messagerie et les battles en temps réel.
- Stockage objet (S3 / Cloudflare R2) pour les fichiers.
- 2FA TOTP pour les administrateurs.
- Migration Alembic pour les évolutions de schéma.
