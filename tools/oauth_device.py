#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIC MASTER — envoi du dépôt via le « Device Flow » GitHub.

Avantage : aucun copier-coller d'URL de retour. Le script affiche un code court
(ex. ABCD-1234) ; vous le saisissez sur https://github.com/login/device, puis le
script détecte l'autorisation et pousse le dépôt.

Prérequis (une seule fois) :
    GitHub → Settings → Developer settings → OAuth Apps → TIC MASTER
    → cocher « Enable Device Flow » → Update application

Usage :
    python tools/oauth_device.py --client-id Ov23li… [--repo ticmaster] [--private]

Le jeton n'est jamais écrit sur le disque : il ne vit que dans la mémoire du
processus et n'est utilisé que le temps du « git push ».
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_USER = "https://api.github.com/user"
API_REPOS = "https://api.github.com/user/repos"
SCOPE = "repo workflow"


def _post(url: str, payload: dict, token: str | None = None, method: str = "POST") -> dict:
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "ticmaster-oauth")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode() or "{}")


def _api_get(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ticmaster-oauth")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def run(cmd: list[str]) -> None:
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pousse TIC MASTER sur GitHub (device flow)")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--repo", default="ticmaster")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--no-create", action="store_true")
    args = parser.parse_args()

    start = _post(DEVICE_CODE_URL, {
        "client_id": args.client_id,
        "scope": SCOPE,
    })
    if "device_code" not in start:
        print("✘ Réponse inattendue de GitHub :", start)
        print("  → vérifiez que « Enable Device Flow » est coché sur l'application OAuth.")
        return 1

    print("\n──────────────────────────────────────────────")
    print(" 1) Ouvrez :", start["verification_uri"])
    print(" 2) Saisissez le code :", start["user_code"])
    print("──────────────────────────────────────────────\n")
    print("En attente de l'autorisation… (Ctrl+C pour abandonner)")

    interval = int(start.get("interval", 5))
    deadline = time.time() + int(start.get("expires_in", 900))
    token = None
    while time.time() < deadline:
        time.sleep(interval)
        result = _post(TOKEN_URL, {
            "client_id": args.client_id,
            "device_code": start["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        error = result.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error:
            print("✘", error, "-", result.get("error_description", ""))
            return 1
        token = result.get("access_token")
        break

    if not token:
        print("✘ Délai dépassé : aucun jeton obtenu.")
        return 1

    me = _api_get(API_USER, token)
    login = me.get("login", "")
    print(f"✔ Autorisation accordée pour @{login}")

    # Enregistre le jeton pour la session du terminal uniquement (jamais sur disque)
    os.environ["TIC_GITHUB_TOKEN"] = token

    if not args.no_create:
        payload = json.dumps({
            "name": args.repo,
            "description": "TIC MASTER — plateforme éducative TIC (#by_Myazirzk)",
            "private": bool(args.private),
            "has_issues": True,
            "has_wiki": False,
        }).encode()
        req = urllib.request.Request(API_REPOS, data=payload, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "ticmaster-oauth")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                info = json.loads(response.read().decode())
            print("✔ Dépôt créé :", info.get("html_url"))
        except urllib.error.HTTPError as exc:
            body = json.loads(exc.read().decode() or "{}")
            if exc.code == 422:
                print("• Dépôt déjà existant, on continue.")
            else:
                print("✘ Création impossible :", body.get("message"))
                return 1

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    clean = f"https://github.com/{login}/{args.repo}.git"
    auth = f"https://x-access-token:{token}@github.com/{login}/{args.repo}.git"

    if subprocess.run(["git", "remote", "get-url", "origin"],
                      capture_output=True).returncode == 0:
        run(["git", "remote", "set-url", "origin", auth])
    else:
        run(["git", "remote", "add", "origin", auth])
    run(["git", "branch", "-M", "main"])
    run(["git", "push", "-u", "origin", "main"])
    run(["git", "remote", "set-url", "origin", clean])   # le jeton n'est pas conservé

    print(f"\n✔ En ligne : https://github.com/{login}/{args.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
