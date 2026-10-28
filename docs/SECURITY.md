# Sécurité — TIC MASTER

Ce document décrit les mesures réellement implémentées, leur emplacement dans le code, et les
points de vigilance pour l'exploitation.

## 1. Synthèse

| Risque (OWASP) | Mesure en place | Emplacement |
|---|---|---|
| A01 — Contrôle d'accès défaillant | Décorateurs `@login_required`, `@admin_required`, `@super_admin_required` ; vérifications d'appartenance ; rôles contrôlés **côté serveur** | `app/security/core.py`, chaque blueprint |
| A02 — Défaillances cryptographiques | Argon2id (64 MiB, t=3, p=4) ; SHA-256 des jetons de session ; cookies `HttpOnly` + `SameSite=Lax` + `Secure` en production ; HSTS | `security/hashing.py`, `security/core.py`, `app/__init__.py` |
| A03 — Injection | ORM SQLAlchemy (requêtes paramétrées) ; aucun SQL concaténé ; échappement Jinja automatique ; rendu Markdown 100 % échappé | `models.py`, `utils.render_content` |
| A04 — Conception non sécurisée | Aucune inscription publique ; création de comptes uniquement par un admin ; changement de mot de passe forcé ; séparation des rôles | `auth.py`, `admin.py` |
| A05 — Mauvaise configuration | Secrets en variables d'environnement ; `DEBUG` désactivé en production ; en-têtes de sécurité ; CSP avec nonce ; pas de compte par défaut avec mot de passe codé | `config.py`, `app/__init__.py` |
| A06 — Composants vulnérables | Dépendances épinglées ; aucune bibliothèque front externe (pas de CDN) | `requirements.txt` |
| A07 — Défaillances d'identification | Verrouillage par compte et par IP ; messages neutres ; comparaison à temps constant ; révocation de sessions | `auth.py`, `security/core.py` |
| A08 — Intégrité | CSRF sur toute requête mutante ; signatures de session ; journal d'audit | `app/__init__.py`, `security/core.py` |
| A09 — Journalisation | `audit_logs` (connexions, échecs, accès refusés, actions admin, examens, violations) | `log_audit()` |
| A10 — SSRF | Aucun appel serveur vers des URL fournies par l'utilisateur | — |

## 2. Mots de passe

- **Algorithme** : Argon2id (`argon2-cffi`), paramètres `time_cost=3`, `memory_cost=65536` (64 MiB),
  `parallelism=4`, `hash_len=32`, `salt_len=16`.
- **Repli** : si `argon2-cffi` est indisponible, `werkzeug.security` en mode **scrypt** — jamais de
  texte clair, jamais de MD5/SHA1.
- **Politique** : 10 caractères minimum, majuscule, minuscule, chiffre, caractère spécial
  (`password_errors()`), appliquée côté serveur pour la création, la réinitialisation et le changement.
- **Rotation** : `must_change_password = True` pour tout compte créé par un administrateur ;
  impossible de naviguer ailleurs que dans `/auth/` tant que le mot de passe n'est pas changé.

## 3. Sessions

| Élément | Choix |
|---|---|
| Cookie d'authentification | `tic_auth` (nom configurable `AUTH_COOKIE_NAME`), `HttpOnly`, `SameSite=Lax`, `Secure` si `COOKIE_SECURE=1`, durée 8 h |
| Stockage serveur | Table `auth_sessions` : **SHA-256** du jeton uniquement |
| Révocation | Déconnexion, suspension, réinitialisation de mot de passe, changement de mot de passe, action admin, bouton « Révoquer » |
| Cookie de session Flask | `tic_session` signé (`SECRET_KEY`) — contient uniquement le jeton CSRF |
| Fixation | `session.clear()` + nouveau jeton CSRF à chaque connexion réussie |

**Pourquoi deux cookies ?** La session Flask (signée, non chiffrée) ne doit jamais transporter de
jeton d'authentification : le jeton vit dans un cookie séparé, opaque, validé en base.

## 4. CSRF

- Jeton aléatoire de 32 octets stocké dans la session signée ; exposé aux templates (`csrf_token()`).
- Vérifié dans `before_request` pour **toute** méthode non sûre (POST, PUT, PATCH, DELETE).
- Accepté depuis le champ `csrf_token` (formulaires) **ou** l'en-tête `X-CSRF-Token` (fetch/JSON).
- Absence ou invalide ⇒ `400` (HTML) ou JSON `400`.
- Les tests automatisés désactivent la vérification via `TESTING=True` uniquement.

## 5. En-têtes de sécurité

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-…'; style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob: https:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=31536000; includeSubDomains   (si HTTPS)
Cache-Control: no-store                                         (pages HTML)
```

Les scripts inline (thème initial, jeton CSRF) portent un **nonce** unique par requête : aucun
`unsafe-inline` pour les scripts.

## 6. Anti-force brute

| Portée | Limite | Fenêtre | Effet |
|---|---|---|---|
| Compte | 5 échecs | — | verrouillage 15 min (`locked_until`) |
| IP (connexion) | 12 tentatives | 10 min | `429` + journal |
| IP (mot de passe oublié) | 8 demandes | 1 h | réponse neutre |
| Messagerie | 20 messages | 1 min | `429` |
| Évaluation | 1 tentative active | — | reprise de la tentative existante |

Implémentation : `RateLimiter` en mémoire (thread-safe) + colonnes `failed_attempts` /
`locked_until` en base. **En production multi-instances**, remplacer par Redis (`flask-limiter`) :
voir §11.

## 7. Énumération de comptes

- Connexion : message unique « Identifiant ou mot de passe incorrect. » ; un hash factice est vérifié
  lorsque le compte n'existe pas (temps de réponse constant).
- Mot de passe oublié : réponse identique que le compte existe ou non ; aucune information divulguée.

## 8. XSS et contenus riches

- Jinja échappe par défaut (`autoescape`).
- Les contenus pédagogiques (Markdown simplifié) sont **échappés avant** d'être enrichis
  (`escape()` puis substitutions contrôlées) ; les liens sont limités à `http(s)`.
- Aucun `|safe` sur une donnée utilisateur.
- Test automatisé : une annonce contenant `<script>` est affichée sous forme de texte.

## 9. Injection SQL

- 100 % ORM, aucun `text()` concaténé avec des entrées utilisateur (seul `SELECT 1` est utilisé pour
  le health check).
- Les filtres `LIKE` utilisent des paramètres liés ; les colonnes de tri sont choisies dans une
  **liste blanche** (`sort`), jamais interpolées.

## 10. Contrôle d'accès et élévation de privilèges

- Un `UTILISATEUR` ne peut ni accéder à `/admin/*` (403), ni modifier son rôle : le champ
  `role` du profil public n'existe pas.
- Un `ADMIN` ne peut pas créer/modifier un `ADMIN` ni un `SUPER ADMIN`, ni consulter les messages,
  le journal d'audit, les sessions, les sauvegardes ou les paramètres (403).
- Les actions sont refusées **même si l'URL est appelée directement** (vérifié par test).
- Toute tentative refusée est journalisée (`access.denied`).

## 11. Limites connues et durcissement recommandé

| Sujet | Limite actuelle | Recommandation |
|---|---|---|
| Rate limiting | mémoire, par processus | Redis + `flask-limiter` (multi-instances) |
| 2FA | non implémentée | TOTP pour les administrateurs (`pyotp`) |
| Upload | vérification de l'extension uniquement | analyse antivirus (ClamAV), stockage objet, URL signées |
| Chiffrement au repos | dépend de l'hébergeur | chiffrement disque / base managée |
| CSP | `style-src 'unsafe-inline'` (styles inline) | migrer vers des classes + nonce CSS |
| Mots de passe compromis | non vérifiés | API « Pwned Passwords » (k-anonymity) |
| Journalisation | base de données | export vers un SIEM / stockage immuable |

## 12. Réponse à incident

1. **Compte compromis** : se connecter en super admin → fiche utilisateur → « Réinitialiser le mot de
   passe » (révoque toutes les sessions) → vérifier le journal d'audit (`auth.login`, `auth.failed`).
2. **Fuite de `SECRET_KEY`** : générer une nouvelle clé, redémarrer (toutes les sessions Flask
   deviennent invalides), forcer la réinitialisation des mots de passe administrateurs.
3. **Fuite de base** : les mots de passe (Argon2id) et les jetons (SHA-256) ne sont pas réutilisables
   directement ; révoquer toutes les sessions (`/admin/sessions`), changer les secrets, informer les
   utilisateurs.
4. **Attaque par force brute** : consulter `audit_logs` (`auth.locked`, `auth.rate_limited`), bloquer
   l'IP au niveau Cloudflare, réduire `LOGIN_IP_MAX_ATTEMPTS`.
5. **Fraude à un examen** : la tentative est éliminée automatiquement et tracée
   (`exam.violation`) ; la réaffectation est réservée au super administrateur et journalisée
   (`exam.reassigned`).

## 13. Checklist avant mise en production

- [ ] `SECRET_KEY` aléatoire de 64 caractères, différente de celle de développement
- [ ] `COOKIE_SECURE=1` et HTTPS actif (Cloudflare « Full (strict) »)
- [ ] `DATABASE_URL` PostgreSQL, sauvegardes automatiques activées
- [ ] Comptes de démonstration supprimés (`python seed.py reset-demo`)
- [ ] Mot de passe du super administrateur changé et stocké dans un gestionnaire de secrets
- [ ] `DEBUG` désactivé (vérifier `/sante` et l'absence de traceback)
- [ ] Journal d'audit consulté : aucun `access.denied` anormal
- [ ] En-têtes de sécurité vérifiés (`curl -I https://votre-domaine`)
- [ ] Test de restauration de sauvegarde effectué
- [ ] Politique de conservation des données renseignée (`/admin/parametres`)
