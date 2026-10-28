#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TIC MASTER — envoi du dépôt vers GitHub (#by_Myazirzk)
# Usage :
#   bash tools/push_github.sh <utilisateur_github> <nom_du_depot> [jeton]
#
# Sans jeton : utilise les identifiants stockés par Git / votre agent SSH.
# Avec jeton  : pousse en HTTPS sans le stocker sur le disque.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."

USERNAME="${1:-}"
REPO="${2:-ticmaster}"
TOKEN="${3:-}"

if [ -z "$USERNAME" ]; then
  echo "Usage : bash tools/push_github.sh <utilisateur_github> [nom_du_depot] [jeton]"
  exit 1
fi

if [ ! -d .git ]; then
  echo "→ Initialisation du dépôt local"
  git init
  git add -A
  git commit -m "TIC MASTER — plateforme éducative TIC (#by_Myazirzk)"
fi

git branch -M main
REMOTE="https://github.com/${USERNAME}/${REPO}.git"

if [ -n "$TOKEN" ]; then
  REMOTE="https://${USERNAME}:${TOKEN}@github.com/${USERNAME}/${REPO}.git"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE"
else
  git remote add origin "$REMOTE"
fi

echo "→ Envoi vers ${USERNAME}/${REPO}"
git push -u origin main

if [ -n "$TOKEN" ]; then
  git remote set-url origin "https://github.com/${USERNAME}/${REPO}.git"   # ne pas laisser le jeton
fi

echo
echo "✔ Dépôt disponible : https://github.com/${USERNAME}/${REPO}"
echo "Étape suivante (Render) : https://render.com → New → Blueprint → sélectionner le dépôt"
