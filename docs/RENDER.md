# Déployer sur Render — pas à pas (mobile ou ordinateur)

> ## ✅ Déploiement effectué le 29/10/2026
>
> | Élément | Valeur |
> |---|---|
> | URL publique | **<https://ticmaster.onrender.com>** |
> | Santé | `{"app":"TIC MASTER","database":true,"status":"ok"}` |
> | Service Render | `srv-dbh6u7jbc2fs73fohv20` (Francfort, plan Free) |
> | Base PostgreSQL | `ticmaster-db` (plan Free) |
> | Contenu installé | 12 modules · 36 leçons · 69 questions · 3 examens |
> | Super administrateur | `Myazirzk` |
>
> Les sections ci-dessous restent la procédure de référence (nouveau déploiement,
> autre compte, ou redéploiement après suppression).


Le dépôt est prêt : <https://github.com/rzkmyazi/ticmaster>
Tout l'amorçage (tables, super administrateur, 12 modules, 69 questions) est **automatique**.
Vous n'aurez aucune commande à taper, ni Shell, ni SQL.

> **Ce que je ne peux pas faire à votre place :** créer le compte Render lui-même. Render exige une
> adresse e-mail vérifiée et une autorisation GitHub qui vous appartiennent (aucun robot ne peut
> la donner à votre place). En revanche, tout le reste est déjà configuré : le bouton ci-dessous
> déploie l'application en 3 écrans.

---

## 1. Le bouton de déploiement

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/rzkmyazi/ticmaster)

Lien direct : <https://render.com/deploy?repo=https://github.com/rzkmyazi/ticmaster>

---

## 2. Les 3 écrans (≈ 2 minutes)

### Écran 1 — Connexion

- **Continue with GitHub** (le compte qui possède le dépôt : `rzkmyazi`).
- **Authorize Render** quand GitHub le demande. Render lit alors `render.yaml`.

### Écran 2 — Récapitulatif du Blueprint

Render affiche :

| Élément | Valeur |
|---|---|
| Service | `ticmaster` (Python, plan Free, Francfort) |
| Base de données | `ticmaster-db` (PostgreSQL Free) |
| Variable demandée | **SUPER_ADMIN_PASSWORD** |

Dans le champ **SUPER_ADMIN_PASSWORD**, saisissez le mot de passe du super administrateur
(`Fiaram131213!!` si vous gardez celui choisi au départ, ou un autre mot de passe fort :
10 caractères minimum, une majuscule, une minuscule, un chiffre, un caractère spécial).

> Si vous laissez le champ vide, l'application génère un mot de passe aléatoire et l'affiche
> **une seule fois** dans les journaux : *Logs → chercher « MOT DE PASSE INITIAL »*.
> Vous pourrez le changer ensuite dans « Mon profil ».

Puis **Apply** / **Deploy Blueprint**.

### Écran 3 — Attente du build

Le service passe par : `Build in progress` → `Deploying` → **`Live`** (3 à 6 minutes la première fois).

L'URL publique apparaît en haut : `https://ticmaster.onrender.com`
(ou `https://ticmaster-xxxx.onrender.com` si le nom est déjà pris — Render ajoute alors un suffixe).

---

## 3. Vérifier en 30 secondes

Ouvrez dans cet ordre :

| Adresse | Attendu |
|---|---|
| `https://VOTRE-URL.onrender.com/sante` | `{"app":"TIC MASTER","database":true,"status":"ok"}` |
| `https://VOTRE-URL.onrender.com/` | page d'accueil, **aucun bouton « S'inscrire »** |
| `https://VOTRE-URL.onrender.com/auth/connexion` | formulaire de connexion |

Connectez-vous avec **`Myazirzk`** et le mot de passe saisi à l'écran 2.
Vous arrivez sur `/admin/` avec les 12 modules déjà installés.

---

## 4. Ce que fait `python seed.py bootstrap` (automatique)

Au démarrage de chaque conteneur, la commande de start exécute :

```
python seed.py bootstrap && gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
```

`bootstrap` est **idempotent** :

1. attend que PostgreSQL réponde (12 tentatives, 5 s d'intervalle) ;
2. crée les tables manquantes (`create_all`) ;
3. crée les paramètres par défaut ;
4. crée le **super administrateur `Myazirzk`** s'il n'existe pas — **ne touche jamais** à un mot de
   passe existant ;
5. charge les **12 modules, 36 leçons, 69 questions, 3 examens, 3 annonces** (uniquement les
   éléments absents) ;
6. n'ajoute les comptes de démonstration que si `TIC_DEMO=1`.

Conséquence : un redéploiement, un redémarrage ou un passage en veille ne réinitialise **jamais**
les données.

---

## 5. Journaux à connaître

Dans **Render → ticmaster → Logs**, vous devez lire au premier déploiement :

```
OK SUPER ADMIN « Myazirzk » cree.
✔ Contenu pédagogique : 12 module(s) créé(s), 69 question(s).
OK Amorçage termine.
[INFO] Listening at: http://0.0.0.0:10000
```

Aux démarrages suivants :

```
OK SUPER ADMIN « Myazirzk » deja present - mot de passe inchange.
✔ Contenu pédagogique : 0 module(s) créé(s), 0 question(s).
```

---

## 6. Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `Database unavailable` puis nouveau démarrage | base PostgreSQL encore en cours de création | attendre 2 minutes, Render relance automatiquement |
| Page blanche / 502 la première fois | service en veille (plan Free : 15 min d'inactivité) | patienter 30–60 s et recharger |
| Connexion refusée alors que le mot de passe est correct | `SUPER_ADMIN_PASSWORD` vide → mot de passe aléatoire | Logs → « MOT DE PASSE INITIAL », puis changement dans le profil |
| Cookies non transmis | `COOKIE_SECURE=1` impose HTTPS | toujours utiliser l'URL `https://…onrender.com` |
| Base supprimée au bout de 30 jours | PostgreSQL **Free** expiré (politique Render) | passer la base en plan payant (≈ 6 $/mois) ou exporter avant échéance |
| Fichiers téléversés perdus au redéploiement | disque éphémère sur le plan Free | contenu pédagogique en base = conservé ; pour les fichiers : disque persistant ou S3/R2 |

---

## 7. Après la mise en ligne

1. **Retirer les comptes de démonstration** (facultatif) : ils ne sont créés que si `TIC_DEMO=1`,
   donc par défaut ils n'existent pas. Rien à faire.
2. **Changer le mot de passe** du super administrateur : `/auth/changer-mot-de-passe`.
3. **Créer les comptes réels** : `/admin/utilisateurs/nouveau` (aucune inscription publique).
4. **Domaine personnalisé + Cloudflare** : voir [`DEPLOYMENT.md`](DEPLOYMENT.md) §3.
5. **Sauvegardes** : `/admin/sauvegardes` (export JSON/CSV) et sauvegardes automatiques Render
   (plans payants).

---

## 8. Coût

| Élément | Plan Free | Recommandé pour une classe |
|---|---|---|
| Service web | 0 € (veille après 15 min) | Starter ≈ 7 $/mois (aucune veille) |
| PostgreSQL | 0 € (expire à 30 jours) | Basic ≈ 6 $/mois (persistant) |
| **Total** | **0 €** | **≈ 13 $/mois** |

---

*Besoin d'aide à une étape ? Dites-moi l'écran affiché et le message exact, je vous guide pas à pas.*
