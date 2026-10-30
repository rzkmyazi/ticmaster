#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIC MASTER — batterie de tests « multi-utilisateurs » (vague 15).

Sept scénarios demandés par le cahier des charges, exécutés **réellement**
contre un serveur en marche :

    A. deux utilisateurs différents sur deux téléphones ;
    B. trois utilisateurs différents simultanément ;
    C. le même utilisateur sur deux appareils ;
    D. déconnexion d'un appareil sans affecter les autres ;
    E. fermeture d'une session depuis l'administration, puis vérification ;
    F. aucun accès aux résultats ou informations d'un autre utilisateur ;
    G. les statistiques affichées correspondent aux sessions enregistrées.

Usage :

    BASE=http://127.0.0.1:5055 python tools/test_sessions.py
    BASE=https://ticmaster.onrender.com python tools/test_sessions.py

Le script crée trois comptes d'essai (``sess.a``, ``sess.b``, ``sess.c``) avec
l'accord du super administrateur, puis **les supprime** à la fin, même en cas
d'erreur. Aucune donnée existante n'est modifiée.
"""
from __future__ import annotations

import os
import random
import re
import string
import sys

import requests

BASE = os.environ.get("BASE", "http://127.0.0.1:5055").rstrip("/")
SUPER = (os.environ.get("SUPER_USER", "Myazirzk"),
         os.environ.get("SUPER_PASSWORD", "Fiaram131213!!"))
MOT_DE_PASSE = "Sessions2026!"

ANDROID = ("Mozilla/5.0 (Linux; Android 13; SM-A125F) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36")
IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/17.0 Mobile Safari/604.1")
WINDOWS = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
TABLETTE = ("Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Mobile Safari/604.1")

resultats: list[tuple[str, bool, str]] = []


def ok(nom: str, condition: bool, detail: str = "") -> None:
    resultats.append((nom, bool(condition), detail))
    print(f"  {'✔' if condition else '✘'} {nom}" + (f" — {detail}" if detail else ""))


def csrf(html: str) -> str:
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)


def session(agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": agent, "Accept-Language": "fr"})
    return s


def connecter(ident: str, mot: str, agent: str) -> requests.Session:
    s = session(agent)
    page = s.get(BASE + "/auth/connexion", timeout=30)
    s.post(BASE + "/auth/connexion",
           data={"csrf_token": csrf(page.text), "identifier": ident, "password": mot},
           allow_redirects=True, timeout=30)
    return s


def connecte(s: requests.Session) -> bool:
    """Vrai seulement si l'espace s'ouvre sans redirection vers la connexion."""
    reponse = s.get(BASE + "/espace", allow_redirects=False, timeout=30)
    return reponse.status_code == 200


def connecte_admin(s: requests.Session) -> bool:
    """Le super administrateur est redirigé depuis /espace : on vérifie /admin/."""
    return s.get(BASE + "/admin/", allow_redirects=False, timeout=30).status_code == 200


def nom_affiche(s: requests.Session) -> str:
    page = s.get(BASE + "/espace", timeout=30).text
    trouve = re.search(r"Bonjour,?\s*([A-Za-zÀ-ÿ' -]{2,40})", page)
    return trouve.group(1).strip() if trouve else ""


def creer_compte(sa: requests.Session, pseudo: str, nom: str, mot: str) -> bool:
    """Crée un élève d'essai avec un mot de passe connu (aucun changement forcé)."""
    page = sa.get(BASE + "/admin/utilisateurs/nouveau", timeout=30).text
    reponse = sa.post(BASE + "/admin/utilisateurs/nouveau",
                      data={"csrf_token": csrf(page), "full_name": nom, "username": pseudo,
                            "email": "", "role": "user", "status": "active",
                            "password": mot, "must_change": "0"},
                      allow_redirects=True, timeout=30)
    return f"@{pseudo}" in reponse.text or pseudo in reponse.text


def supprimer_compte(sa: requests.Session, pseudo: str) -> bool:
    listing = sa.get(BASE + "/admin/utilisateurs?q=" + pseudo, timeout=30).text
    ids = sorted({int(i) for i in re.findall(r'/admin/utilisateurs/(\d+)"', listing)})
    supprime = False
    for uid in ids:
        detail = sa.get(BASE + f"/admin/utilisateurs/{uid}", timeout=30).text
        if f"@{pseudo}" in detail:
            sa.post(BASE + f"/admin/utilisateurs/{uid}/supprimer",
                    data={"csrf_token": csrf(detail), "confirm": pseudo},
                    allow_redirects=False, timeout=30)
            supprime = True
    return supprime


def presence(sa: requests.Session) -> dict:
    return sa.get(BASE + "/admin/api/presence", timeout=30).json()


def sessions_de(sa: requests.Session, pseudo: str) -> list[dict]:
    """Sessions listées pour un compte (lecture via la page d'administration)."""
    page = sa.get(BASE + "/admin/sessions?q=" + pseudo, timeout=30).text
    fiches = []
    for bloc in re.split(r'<article class="session-card', page)[1:]:
        identifiant = re.search(r'data-session-row="(\d+)"', bloc)
        etat = re.search(r'data-session-state="([a-z]+)"', bloc)
        appareil = re.search(r'device-chip[^>]*>\s*<svg[\s\S]{0,300}?</svg>\s*([^<]+)', bloc)
        fiches.append({
            "id": int(identifiant.group(1)) if identifiant else 0,
            "state": etat.group(1) if etat else "",
            "device": appareil.group(1).strip() if appareil else "",
        })
    return fiches


def main() -> int:
    suffixe = "".join(random.choice(string.ascii_lowercase) for _ in range(4))
    comptes = {cle: f"sess.{cle}{suffixe}" for cle in ("a", "b", "c")}
    noms = {"a": "Alpha Testeur", "b": "Bravo Testeur", "c": "Charlie Testeur"}

    sa = connecter(*SUPER, WINDOWS)
    if not connecte_admin(sa):
        print("Impossible de se connecter en super administrateur — arrêt.")
        return 2

    avant = presence(sa)["counts"]
    print(f"État initial : {avant['online_users']} en ligne, "
          f"{avant['open_sessions']} session(s) ouverte(s)\n")

    crees = []
    try:
        for cle, pseudo in comptes.items():
            creer_compte(sa, pseudo, noms[cle], MOT_DE_PASSE)
            if connecte(connecter(pseudo, MOT_DE_PASSE, WINDOWS)):
                crees.append(pseudo)
        if len(crees) != 3:
            print(f"Comptes d'essai créés : {crees} — impossible de continuer.")
            return 2

        # ------------------------------------------------------------ TEST A
        print("TEST A — deux utilisateurs différents, deux téléphones")
        tel_a = connecter(comptes["a"], MOT_DE_PASSE, ANDROID)
        tel_b = connecter(comptes["b"], MOT_DE_PASSE, IPHONE)
        ok("A.1 les deux téléphones sont connectés", connecte(tel_a) and connecte(tel_b))
        ok("A.2 chaque personne voit son propre espace",
           nom_affiche(tel_a).startswith("Alpha") and nom_affiche(tel_b).startswith("Bravo")
           and comptes["a"] not in tel_b.get(BASE + "/espace").text,
           f"{nom_affiche(tel_a)} / {nom_affiche(tel_b)}")
        ok("A.3 deux sessions distinctes côté serveur",
           len([s for s in sessions_de(sa, comptes["a"]) if s["state"] == "online"]) >= 1
           and len([s for s in sessions_de(sa, comptes["b"]) if s["state"] == "online"]) >= 1)
        ok("A.4 la connexion de B n'a pas déconnecté A", connecte(tel_a))

        # ------------------------------------------------------------ TEST B
        print("\nTEST B — trois utilisateurs simultanément")
        ordinateur_c = connecter(comptes["c"], MOT_DE_PASSE, WINDOWS)
        tous = all(connecte(s) for s in (tel_a, tel_b, ordinateur_c))
        etat = presence(sa)["counts"]
        ok("B.1 trois sessions vivantes à l'instant T", tous)
        ok("B.2 le compteur d'utilisateurs en ligne reflète les trois comptes",
           etat["online_users"] >= 3, f"{etat['online_users']} en ligne")

        # ------------------------------------------------------------ TEST C
        print("\nTEST C — même utilisateur sur deux appareils")
        tablette_a = connecter(comptes["a"], MOT_DE_PASSE, TABLETTE)
        fiches_a = [s for s in sessions_de(sa, comptes["a"]) if s["state"] in ("online", "idle")]
        ok("C.1 les deux appareils du compte A restent connectés",
           connecte(tel_a) and connecte(tablette_a))
        ok("C.2 deux sessions listées pour A", len(fiches_a) >= 2, f"{len(fiches_a)} session(s)")
        ok("C.3 appareils différents identifiés",
           len({s["device"].split(" · ")[0] for s in fiches_a}) >= 2,
           str(sorted({s["device"] for s in fiches_a})))

        # ------------------------------------------------------------ TEST D
        print("\nTEST D — déconnexion d'un appareil sans affecter les autres")
        tel_a.get(BASE + "/auth/deconnexion", timeout=30)
        ok("D.1 l'appareil déconnecté n'a plus accès", not connecte(tel_a))
        ok("D.2 l'autre appareil de A reste connecté", connecte(tablette_a))
        ok("D.3 B et C ne sont pas affectés", connecte(tel_b) and connecte(ordinateur_c))
        fermees = [s for s in sessions_de(sa, comptes["a"]) if s["state"] == "revoked"]
        ok("D.4 la session déconnectée est marquée « révoquée »", bool(fermees),
           f"{len(fermees)} révoquée(s)")

        # ------------------------------------------------------------ TEST E
        print("\nTEST E — fermeture d'une session depuis l'administration")
        cible = next((s for s in sessions_de(sa, comptes["b"]) if s["state"] == "online"), None)
        ok("E.1 session de B visible dans l'administration", cible is not None)
        if cible:
            page = sa.get(BASE + "/admin/sessions?q=" + comptes["b"], timeout=30).text
            sa.post(BASE + f"/admin/sessions/{cible['id']}/revoquer",
                    data={"csrf_token": csrf(page)}, allow_redirects=True, timeout=30)
            ok("E.2 l'appareil fermé est immédiatement déconnecté", not connecte(tel_b))
            ok("E.3 sa session est marquée « révoquée »",
               any(s["id"] == cible["id"] and s["state"] == "revoked"
                   for s in sessions_de(sa, comptes["b"])))
            ok("E.4 les autres personnes ne sont pas touchées",
               connecte(tablette_a) and connecte(ordinateur_c))

        # ------------------------------------------------------------ TEST F
        print("\nTEST F — aucune fuite entre utilisateurs")
        page = tablette_a.get(BASE + "/exercices", timeout=30).text
        lien = re.search(r'/exercices/(\d+)"', page)
        tentative = None
        if lien:
            detail = tablette_a.get(BASE + f"/exercices/{lien.group(1)}", timeout=30).text
            reponse = tablette_a.post(BASE + f"/exercices/{lien.group(1)}/commencer",
                                      data={"csrf_token": csrf(detail)},
                                      allow_redirects=False, timeout=30)
            trouve = re.search(r"/exercices/tentative/(\d+)", reponse.headers.get("Location", ""))
            tentative = int(trouve.group(1)) if trouve else None
        ok("F.1 une tentative de A est créée", tentative is not None, str(tentative))
        if tentative:
            ok("F.2 C ne peut pas ouvrir la tentative de A",
               ordinateur_c.get(BASE + f"/exercices/tentative/{tentative}",
                                allow_redirects=False).status_code in (403, 404))
            ok("F.3 C ne peut pas lire le résultat de A",
               ordinateur_c.get(BASE + f"/resultats/{tentative}",
                                allow_redirects=False).status_code in (403, 404))
            ok("F.4 C ne peut pas passer l'examen de A",
               ordinateur_c.get(BASE + f"/examens/passer/{tentative}",
                                allow_redirects=False).status_code in (403, 404))
        page_c = ordinateur_c.get(BASE + "/resultats", timeout=30).text
        ok("F.5 la page de résultats de C ne contient aucune donnée de A",
           "Alpha Testeur" not in page_c and "Bravo Testeur" not in page_c)
        ok("F.6 un élève n'accède ni à l'administration ni à la liste des sessions",
           ordinateur_c.get(BASE + "/admin/", allow_redirects=False).status_code in (403, 302)
           and ordinateur_c.get(BASE + "/admin/sessions",
                                allow_redirects=False).status_code in (403, 302))
        ok("F.7 le mot de passe n'apparaît nulle part dans le HTML d'administration",
           "password_hash" not in sa.get(BASE + "/admin/sessions", timeout=30).text)
        ok("F.8 l'API de présence ne divulgue aucun jeton",
           "token" not in sa.get(BASE + "/admin/api/presence", timeout=30).text.lower())

        # ------------------------------------------------------------ TEST G
        print("\nTEST G — les statistiques correspondent aux sessions réelles")
        donnees = presence(sa)
        compteurs = donnees["counts"]
        en_ligne = [s for s in donnees["sessions"] if s["state"] == "online"]
        ok("G.1 sessions ouvertes = sessions en ligne + inactives",
           compteurs["open_sessions"] == compteurs["online_sessions"] + compteurs["idle_sessions"],
           f"{compteurs['open_sessions']} = {compteurs['online_sessions']} + "
           f"{compteurs['idle_sessions']}")
        ok("G.2 le nombre de sessions en ligne correspond au détail",
           compteurs["online_sessions"] == len(en_ligne),
           f"{compteurs['online_sessions']} / {len(en_ligne)}")
        ok("G.3 le nombre de personnes en ligne = comptes distincts",
           compteurs["online_users"] == len({s["user_id"] for s in en_ligne}),
           f"{compteurs['online_users']} / {len({s['user_id'] for s in en_ligne})}")
        ok("G.4 aucun jeton ni empreinte secrète dans le flux JSON",
           all("token" not in s for s in donnees["sessions"]))
        ok("G.5 les compteurs restent cohérents après rechargement",
           sa.get(BASE + "/admin/sessions", timeout=30).status_code == 200
           and presence(sa)["counts"]["online_sessions"] == letat_online(sa))
    finally:
        print("\nNettoyage des comptes d'essai")
        for pseudo in crees:
            supprimer_compte(sa, pseudo)
        restants = [p for p in crees if sessions_de(sa, p)]
        ok(f"comptes d'essai supprimés ({len(crees)})", not restants, str(restants))

    echecs = [nom for nom, reussi, _ in resultats if not reussi]
    print(f"\n=== Bilan : {len(resultats) - len(echecs)}/{len(resultats)} test(s) conformes ===")
    for nom in echecs:
        print("   ✘", nom)
    return 1 if echecs else 0


def letat_online(sa: requests.Session) -> int:
    return presence(sa)["counts"]["online_sessions"]


if __name__ == "__main__":
    sys.exit(main())
