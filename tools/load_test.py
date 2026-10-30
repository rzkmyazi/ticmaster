#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIC MASTER — test de charge « plusieurs centaines de connexions ».

Simule une salle de classe entière : plusieurs dizaines de comptes, chacun
ouvrant une ou plusieurs sessions en parallèle, puis naviguant.

    python tools/load_test.py --base http://127.0.0.1:5056 --comptes 20 --sessions 200

Le script crée ses propres comptes ``charge.N`` puis les supprime. Il affiche
un bilan honnête : succès, latences (médiane, p95, maximum) et codes d'erreur.
Aucun compte existant n'est modifié.
"""
from __future__ import annotations

import argparse
import random
import re
import statistics
import string
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

AGENTS = [
    ("Mozilla/5.0 (Linux; Android 13; SM-A125F) AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/120.0 Mobile Safari/537.36", "Android"),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
     "(KHTML, like Gecko) Version/17.0 Mobile Safari/604.1", "iPhone"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/121.0 Safari/537.36", "Windows"),
    ("Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0", "Linux"),
]


def csrf(html: str) -> str:
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)


def admin(base: str, ident: str, mot: str) -> requests.Session:
    s = requests.Session()
    page = s.get(base + "/auth/connexion", timeout=60)
    s.post(base + "/auth/connexion",
           data={"csrf_token": csrf(page.text), "identifier": ident, "password": mot},
           allow_redirects=True, timeout=60)
    return s


def creer_comptes(sa: requests.Session, base: str, nombre: int, mot: str) -> list[str]:
    pseudo = "".join(random.choice(string.ascii_lowercase) for _ in range(4))
    crees = []
    for i in range(1, nombre + 1):
        nom = f"charge.{pseudo}.{i:03d}"
        page = sa.get(base + "/admin/utilisateurs/nouveau", timeout=60).text
        sa.post(base + "/admin/utilisateurs/nouveau",
                data={"csrf_token": csrf(page), "full_name": f"Charge {i:03d}",
                      "username": nom, "email": "", "role": "user", "status": "active",
                      "password": mot, "must_change": "0"}, allow_redirects=True, timeout=60)
        crees.append(nom)
    return crees


def supprimer_compte(sa: requests.Session, base: str, nom: str) -> None:
    listing = sa.get(base + "/admin/utilisateurs?q=" + nom, timeout=60).text
    for uid in sorted({int(i) for i in re.findall(r'/admin/utilisateurs/(\d+)"', listing)}):
        detail = sa.get(base + f"/admin/utilisateurs/{uid}", timeout=60).text
        if f"@{nom}" in detail:
            sa.post(base + f"/admin/utilisateurs/{uid}/supprimer",
                    data={"csrf_token": csrf(detail), "confirm": nom}, timeout=60)


def scenario(base: str, compte: str, mot: str, index: int) -> dict:
    """Une connexion + deux pages, comme un élève qui arrive en cours."""
    agent, famille = AGENTS[index % len(AGENTS)]
    s = requests.Session()
    s.headers["User-Agent"] = agent
    debut = time.time()
    try:
        page = s.get(base + "/auth/connexion", timeout=60)
        reponse = s.post(base + "/auth/connexion",
                         data={"csrf_token": csrf(page.text), "identifier": compte,
                               "password": mot},
                         allow_redirects=True, timeout=60)
        connecte = "/espace" in reponse.url
        fin_connexion = time.time()
        espace = s.get(base + "/espace", timeout=60)
        cours = s.get(base + "/cours", timeout=60)
        fin_pages = time.time()
        s.get(base + "/auth/deconnexion", timeout=30)   # on referme proprement
        return {"ok": connecte and espace.status_code == 200 and cours.status_code == 200,
                "duree": fin_pages - debut, "connexion": fin_connexion - debut,
                "pages": fin_pages - fin_connexion,
                "famille": famille, "code": cours.status_code}
    except Exception as exc:                            # réseau, délai…
        return {"ok": False, "duree": time.time() - debut,
                "famille": famille, "code": type(exc).__name__}


def main() -> int:
    parseur = argparse.ArgumentParser()
    parseur.add_argument("--base", default="http://127.0.0.1:5056")
    parseur.add_argument("--comptes", type=int, default=20)
    parseur.add_argument("--sessions", type=int, default=200)
    parseur.add_argument("--super-user", default="Myazirzk")
    parseur.add_argument("--super-password", default="Fiaram131213!!")
    options = parseur.parse_args()
    base = options.base.rstrip("/")
    mot = "Charge2026!"
    random.seed(7)

    sa = admin(base, options.super_user, options.super_password)
    if sa.get(base + "/admin/", allow_redirects=False).status_code != 200:
        print("Connexion administrateur impossible — arrêt.")
        return 2

    print(f"Création de {options.comptes} comptes d'essai…")
    comptes = creer_comptes(sa, base, options.comptes, mot)

    try:
        print(f"{options.sessions} sessions simultanées sur {options.comptes} comptes "
              f"({len(AGENTS)} types d'appareils)…")
        debut = time.time()
        with ThreadPoolExecutor(max_workers=min(options.sessions, 100)) as pool:
            resultats = list(pool.map(
                lambda paire: scenario(base, comptes[paire[0] % len(comptes)], mot, paire[0]),
                list(enumerate(range(options.sessions)))))
        total = time.time() - debut

        reussis = sum(1 for r in resultats if r["ok"])
        latences = sorted(r["duree"] for r in resultats)
        mediane = statistics.median(latences)
        p95 = latences[int(len(latences) * 0.95) - 1]
        codes = {}
        for r in resultats:
            codes[r["code"]] = codes.get(r["code"], 0) + 1

        print("\n=== Bilan de charge ===")
        print(f"  sessions réussies : {reussis}/{len(resultats)} "
              f"({100 * reussis / max(1, len(resultats)):.1f} %)")
        print(f"  durée totale     : {total:.1f} s "
              f"({len(resultats) / max(total, 0.001):.1f} sessions/s)")
        connexions = sorted(r.get("connexion", 0) for r in resultats)
        pages = sorted(r.get("pages", 0) for r in resultats)
        print(f"  connexion médiane: {statistics.median(connexions) * 1000:.0f} ms "
              f"(p95 {connexions[int(len(connexions) * 0.95) - 1] * 1000:.0f} ms)")
        print(f"  2 pages médiane  : {statistics.median(pages) * 1000:.0f} ms "
              f"(p95 {pages[int(len(pages) * 0.95) - 1] * 1000:.0f} ms)")
        print(f"  latence médiane  : {mediane * 1000:.0f} ms")
        print(f"  latence p95      : {p95 * 1000:.0f} ms")
        print(f"  latence maximale : {latences[-1] * 1000:.0f} ms")
        print(f"  codes rencontrés : {codes}")
        print(f"  appareils        : "
              f"{ {a: sum(1 for r in resultats if r['famille'] == a) for _, a in AGENTS} }")
        return 0 if reussis == len(resultats) else 1
    finally:
        print("\nSuppression des comptes d'essai…")
        for compte in comptes:
            supprimer_compte(sa, base, compte)
        print("  terminé.")


if __name__ == "__main__":
    sys.exit(main())
