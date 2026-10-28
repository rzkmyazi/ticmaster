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

*Rapport généré automatiquement à partir des sorties de `pytest` et `tools/verify.py`.*
