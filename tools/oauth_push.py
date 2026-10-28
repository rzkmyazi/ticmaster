#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIC MASTER — envoi du dépôt via le flux OAuth de GitHub.

Pourquoi ce script ?
    Le flux « github.com/login/oauth/authorize » nécessite une application OAuth
    (client_id + client_secret) : GitHub ne délivre pas de jeton sans application
    déclarée. Ce script déroule le flux en trois temps :
      1. il affiche l'URL d'autorisation à ouvrir dans votre navigateur ;
      2. vous approuvez, GitHub redirige vers l'URL de retour avec ?code=… ;
      3. vous collez ici l'URL complète (ou le code), le jeton est échangé,
         puis le dépôt est poussé — le jeton n'est jamais écrit sur le disque.

Création de l'application OAuth (une seule fois, 2 minutes) :
    GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
      • Application name        : TIC MASTER (local)
      • Homepage URL            : https://github.com
      • Authorization callback  : https://github.com
    puis « Generate a new client secret ».

Usage :
    python tools/oauth_push.py --client-id XXX --client-secret YYY \
        [--repo ticmaster] [--user VOTRE_COMPTE]
    # ou, sans interaction :
    python tools/oauth_push.py --client-id XXX --client-secret YYY --code LE_CODE
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import urllib.parse
import urllib.request

AUTHORIZE = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_USER = "https://api.github.com/user"
API_REPOS = "https://api.github.com/user/repos"
SCOPE = "repo"


def api(url: str, token: str, payload: dict | None = None, method: str = "GET") -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ticmaster-oauth")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read().decode()
    return json.loads(body) if body else {}


def exchange_code(client_id: str, client_secret: str, code: str) -> str:
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": "https://github.com",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "ticmaster-oauth")
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode())
    if "access_token" not in payload:
        raise SystemExit(f"✘ Échec de l'échange du code : {payload.get('error_description') or payload}")
    return payload["access_token"]


def extract_code(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("http"):
        query = urllib.parse.urlparse(raw).query
        params = urllib.parse.parse_qs(query)
        if "code" not in params:
            raise SystemExit("✘ Aucun paramètre « code » dans l'URL fournie.")
        return params["code"][0]
    return raw


def run(cmd: list[str], env: dict | None = None) -> None:
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pousse TIC MASTER sur GitHub via OAuth")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    parser.add_argument("--repo", default="ticmaster")
    parser.add_argument("--user", default="", help="compte GitHub (déduit du jeton sinon)")
    parser.add_argument("--code", default="", help="code OAuth déjà obtenu")
    parser.add_argument("--private", action="store_true", help="dépôt privé")
    parser.add_argument("--no-create", action="store_true", help="le dépôt existe déjà")
    args = parser.parse_args()

    state = secrets.token_hex(8)
    url = f"{AUTHORIZE}?client_id={args.client_id}&scope={SCOPE}&state={state}"
    url += "&redirect_uri=" + urllib.parse.quote("https://github.com", safe="")

    code = args.code
    if not code:
        print("\n1) Ouvrez cette adresse dans votre navigateur et autorisez l'application :\n")
        print("   " + url + "\n")
        print("2) GitHub affiche ensuite une page dont l'adresse contient « ?code=… »")
        print("   Collez l'URL complète (ou seulement le code) ci-dessous.\n")
        code = input("URL / code > ")

    token = exchange_code(args.client_id, args.client_secret, extract_code(code))

    me = api(API_USER, token)
    login = args.user or me.get("login", "")
    print(f"✔ Jeton obtenu pour @{login} (portées : {me.get('login') and SCOPE})")

    if not args.no_create:
        try:
            info = api(f"{API_REPOS}", token, {
                "name": args.repo,
                "description": "TIC MASTER — plateforme éducative TIC (#by_Myazirzk)",
                "private": bool(args.private),
                "has_issues": True,
                "has_wiki": False,
            }, method="POST")
            print(f"✔ Dépôt créé : {info.get('html_url')}")
        except urllib.error.HTTPError as exc:  # déjà existant
            if exc.code == 422:
                print("• Dépôt déjà existant, on continue.")
            else:
                raise

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    remote = f"https://github.com/{login}/{args.repo}.git"
    auth_remote = f"https://x-access-token:{token}@github.com/{login}/{args.repo}.git"

    if subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True).returncode == 0:
        run(["git", "remote", "set-url", "origin", auth_remote])
    else:
        run(["git", "remote", "add", "origin", auth_remote])

    run(["git", "branch", "-M", "main"])
    run(["git", "push", "-u", "origin", "main"])

    # On ne laisse jamais le jeton dans la configuration du dépôt
    run(["git", "remote", "set-url", "origin", remote])

    print(f"\n✔ En ligne : https://github.com/{login}/{args.repo}")
    print("  Pensez à révoquer l'application OAuth après usage :")
    print("  https://github.com/settings/applications")
    return 0


if __name__ == "__main__":
    sys.exit(main())
