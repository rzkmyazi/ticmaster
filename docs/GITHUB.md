# Mise en ligne sur GitHub — TIC MASTER

Le dépôt Git est **déjà initialisé et validé en local** (branche `main`, 1 commit, 100 fichiers,
aucun secret ni base de données versionnés). Il ne reste que l'envoi vers votre compte GitHub.

---

## Option A — Vous poussez vous-même (recommandé, 2 minutes)

### A.1 Créer le dépôt vide

1. <https://github.com/new>
2. **Repository name** : `ticmaster`
3. Visibilité : **Public** (nécessaire pour le plan gratuit Render) ou Private
4. **Ne cochez rien** (pas de README, pas de .gitignore, pas de licence) → **Create repository**

### A.2 Envoyer le code

Depuis le dossier `ticmaster` :

```bash
bash tools/push_github.sh VOTRE_UTILISATEUR ticmaster
```

Ou manuellement :

```bash
git remote add origin https://github.com/VOTRE_UTILISATEUR/ticmaster.git
git branch -M main
git push -u origin main
```

Git vous demandera vos identifiants : en **mot de passe**, utilisez un **jeton d'accès personnel**
(*GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens*,
portée `Contents: Read and write` sur le dépôt concerné). Le mot de passe du compte ne fonctionne plus
pour Git.

### A.3 Vérifier

```bash
git remote -v
git log --oneline -1
```

Puis ouvrir `https://github.com/VOTRE_UTILISATEUR/ticmaster`.

---

## Option B — Envoi depuis une autre machine (archive Git)

Un *bundle* complet du dépôt est fourni : `ticmaster-main.bundle`.

```bash
git clone ticmaster-main.bundle ticmaster
cd ticmaster
git remote set-url origin https://github.com/VOTRE_UTILISATEUR/ticmaster.git
git push -u origin main --tags
```

---

## Ce qui est envoyé (et ce qui ne l'est pas)

| Envoyé | Exclu par `.gitignore` |
|---|---|
| Code de l'application (`app/`), tests, documentation | `.env` (secrets) |
| `requirements.txt`, `Procfile`, `render.yaml`, `runtime.txt` | `instance/*.db` (base locale) |
| `.env.example` (modèle **sans** secret) | `instance/uploads/*` (fichiers utilisateurs) |
| Icônes et visuels (`app/static/img/`) | `__pycache__/`, `.venv/`, `*.log` |

Vérification réalisée avant le commit :

```bash
git ls-files | grep -E "\.env$|\.db$" || echo "✔ aucun fichier sensible"
```

---

## Étapes suivantes après l'envoi

1. **Render** : <https://render.com> → *New* → *Blueprint* → sélectionner le dépôt.
   `render.yaml` crée le service web + PostgreSQL et le health check `/sante`.
2. Dans le **Shell Render** :
   ```bash
   python seed.py init
   python seed.py superadmin --username Myazirzk
   python seed.py seed
   python seed.py reset-demo        # au choix : retire les comptes de démonstration
   ```
3. **Cloudflare** : ajouter le domaine, proxy activé, SSL « Full (strict) », règle de cache
   `/static/*`, limitation de débit sur `/auth/connexion`.
4. Détails complets : [`docs/DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Bonnes pratiques Git

```bash
git checkout -b correctif/mon-ajout
git add -A && git commit -m "Description claire du changement"
git push -u origin correctif/mon-ajout     # puis Pull Request
```

- Ne jamais committer `.env` ni un jeton.
- Un commit = un changement cohérent.
- Tester avant de pousser : `pytest -q`.
