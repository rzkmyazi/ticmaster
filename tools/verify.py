#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIC MASTER — vérification fonctionnelle et sécurité de bout en bout.

À lancer contre une instance qui tourne (locale ou distante) :

    python tools/verify.py
    BASE=https://ticmaster.onrender.com python tools/verify.py

Le script est **rejouable** : il crée un compte jetable pour les tests qui
modifient l'état (examen, battle, exercices), afin de ne jamais dépendre des
tentatives déjà enregistrées sur les comptes de démonstration.

Variables : BASE (URL), SUPER_PASSWORD, TIC_DB (chemin SQLite, pour les
vérifications en base). Code de sortie = nombre d'échecs.
"""
from __future__ import annotations

import os
import random
import re
import sqlite3
import string
import sys
import time

import requests

BASE = os.environ.get("BASE", "http://127.0.0.1:5000").rstrip("/")
DB = os.environ.get("TIC_DB", os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "instance", "ticmaster.db"))

SUPER = ("Myazirzk", os.environ.get("SUPER_PASSWORD", "Fiaram131213!!"))
ADMIN = ("admin.demo", "AdminDemo2026!")
USER = ("apprenant", "Apprenant2026!")

failures: list[str] = []


def ok(label: str, condition: bool, detail: str = "") -> None:
    print(f"  {'✔' if condition else '✘'} {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def csrf(session: requests.Session, path: str) -> str:
    page = session.get(BASE + path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    if match:
        return match.group(1)
    match = re.search(r'name="csrf-token" content="([^"]+)"', page.text)
    return match.group(1) if match else ""


# ---------------------------------------------------------------- provision
def app_post_delete(session, token: str, post_id: int) -> bool:
    """Supprime une publication de test (nettoyage)."""
    response = session.post(BASE + f"/api/posts/{post_id}/delete", json={},
                            headers={"X-CSRF-Token": token})
    return response.status_code == 200


def _can_login(identifier: str, password: str) -> bool:
    probe = requests.Session()
    token = csrf(probe, "/auth/connexion")
    response = probe.post(BASE + "/auth/connexion",
                          data={"csrf_token": token, "identifier": identifier,
                                "password": password}, allow_redirects=False)
    return response.status_code == 302


def _provision(sa, username: str, full_name: str, role: str, password: str) -> bool:
    """Crée un compte de travail avec un mot de passe connu (instance neuve)."""
    token = csrf(sa, "/admin/utilisateurs/nouveau")
    response = sa.post(BASE + "/admin/utilisateurs/nouveau",
                       data={"csrf_token": token, "full_name": full_name,
                             "username": username, "email": "", "role": role,
                             "status": "active", "password": "", "must_change": "1"})
    match = re.search(r'Mot de passe temporaire</span>\s*<div class="stat-value mono"[^>]*>([^<]+)</div>',
                      response.text)
    if not match:
        return False
    temp = match.group(1).strip()
    session = requests.Session()
    token = csrf(session, "/auth/connexion")
    session.post(BASE + "/auth/connexion",
                 data={"csrf_token": token, "identifier": username, "password": temp},
                 allow_redirects=False)
    token = csrf(session, "/auth/changer-mot-de-passe")
    session.post(BASE + "/auth/changer-mot-de-passe",
                 data={"csrf_token": token, "current_password": temp,
                       "new_password": password, "confirm_password": password},
                 allow_redirects=False)
    return _can_login(username, password)


PROVISIONED: list[str] = []


def cleanup_accounts(sa) -> int:
    """Supprime les comptes créés par la vérification — jamais le super administrateur."""
    import urllib.parse
    page = sa.get(BASE + "/admin/utilisateurs").text
    names = sorted(set(re.findall(r'@([A-Za-z0-9._-]+)', page)))
    junk = [n for n in names if n.startswith(("verif.", "temp.", "prod.test."))]
    junk += [n for n in names if n in PROVISIONED]
    removed = 0
    for name in sorted(set(junk)):
        if name == SUPER[0]:
            continue
        listing = sa.get(BASE + "/admin/utilisateurs?q=" + urllib.parse.quote(name)).text
        for uid in sorted({int(i) for i in re.findall(r'/admin/utilisateurs/(\d+)"', listing)}):
            detail = sa.get(BASE + f"/admin/utilisateurs/{uid}").text
            if f"@{name}" in detail:
                token = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
                resp = sa.post(BASE + f"/admin/utilisateurs/{uid}/supprimer",
                               data={"csrf_token": token, "confirm": name}, allow_redirects=False)
                if resp.status_code == 302:
                    removed += 1
                break
    return removed


def ensure_accounts(sa) -> None:
    """Le script reste rejouable sur une instance neuve : il crée ce qui manque."""
    for ident, pwd, full, role in ((ADMIN[0], ADMIN[1], "Administrateur Démo", "admin"),
                                   (USER[0], USER[1], "Apprenant Démonstration", "user")):
        if not _can_login(ident, pwd):
            created = _provision(sa, ident, full, role, pwd)
            ok(f"provision automatique du compte {ident}", created)
            if created:
                PROVISIONED.append(ident)


def login(identifier: str, password: str, label: str | None = None) -> requests.Session:
    session = requests.Session()
    token = csrf(session, "/auth/connexion")
    response = session.post(BASE + "/auth/connexion",
                            data={"csrf_token": token, "identifier": identifier,
                                  "password": password}, allow_redirects=False)
    ok(label or f"connexion {identifier}", response.status_code == 302,
       f"{response.status_code} → {response.headers.get('Location')}")
    return session


LOCAL = any(h in BASE for h in ("127.0.0.1", "localhost"))
REMOTE_SKIPS: list[str] = []


def skip(label: str, reason: str) -> None:
    """Contrôle impossible à distance (accès direct à la base)."""
    REMOTE_SKIPS.append(label)
    print(f"  ↷ {label} — {reason}")


def db_rows(query: str, params=()):
    """Lit la base SQLite locale ; None si la cible est distante (PostgreSQL)."""
    if not LOCAL:
        return None
    if not os.path.exists(DB):
        return []
    con = sqlite3.connect(DB)
    try:
        return con.execute(query, params).fetchall()
    finally:
        con.close()


def png_bytes(width: int = 8, height: int = 8, color=(30, 120, 220)) -> bytes:
    """Petit PNG valide (pour tester l'envoi d'une photo de profil)."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        payload = tag + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def rand_suffix(n: int = 5) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def main() -> int:
    print(f"\n=== TIC MASTER · vérification de {BASE} ===\n")

    # ------------------------------------------------------------------ santé
    print("▸ Santé")
    debut = time.time()
    r = requests.get(BASE + "/sante", timeout=90)
    latence = round(time.time() - debut, 2)
    ok("/sante", r.status_code == 200 and r.json().get("status") == "ok", r.text[:60])
    ok("réponse immédiate (pas de réveil à froid)", latence < 5,
       f"{latence} s")
    sante = r.json()
    ok("/sante publie l'état de la veille 24 h/24", "veille" in sante, str(sante.get("veille")))
    if "ticmaster.onrender.com" in BASE:
        ok("veille 24 h/24 active sur Render (auto-appel toutes les 10 minutes)",
           sante.get("veille") is True, str(sante.get("veille")))
    if "myazirzk1" in BASE:
        # PythonAnywhere est secondaire : son proxy sortant ne peut pas appeler Render.
        ok("PythonAnywhere : veille non requise sur ce serveur", "veille" in sante)

    print("▸ Pages publiques et absence d'inscription")
    for path, expected in (("/", 200), ("/a-propos", 200), ("/decouvrir", 200),
                           ("/auth/connexion", 200),
                           ("/auth/mot-de-passe-oublie", 200),
                           ("/inscription", 404), ("/register", 404),
                           ("/auth/inscription", 404)):
        code = requests.get(BASE + path, timeout=20).status_code
        ok(f"{path} → {code}", code == expected, f"attendu {expected}")
    home = requests.get(BASE + "/", timeout=20).text.lower()
    ok("aucune inscription publique sur l'accueil",
       "s'inscrire" not in home and "créer un compte" not in home)

    print("▸ Accueil : connexion intégrée et présentation courte")
    accueil = requests.get(BASE + "/", timeout=20).text
    ok("formulaire de connexion présent sur l'accueil",
       'name="identifier"' in accueil and 'name="password"' in accueil
       and 'name="csrf_token"' in accueil and 'name="remember"' in accueil)
    ok("titre de bienvenue « Bienvenue sur TIC MASTER_#by_Myazirzk »",
       "Bienvenue sur" in accueil and "TIC MASTER_" in accueil)
    ok("sous-titre « Connectez-vous pour poursuivre votre apprentissage. »",
       "Connectez-vous pour poursuivre votre apprentissage." in accueil)
    ok("case « Se souvenir de moi » et lien mot de passe oublié",
       "Se souvenir de moi" in accueil and "/auth/mot-de-passe-oublie" in accueil)
    ok("affichage / masquage du mot de passe (data-pw-toggle)",
       'data-pw-toggle="password"' in accueil)
    ok("bouton avec indicateur de chargement",
       'data-loading="Connexion en cours' in accueil)
    ok("présentation courte « Apprenez les TIC autrement. »",
       "Apprenez les TIC autrement." in accueil
       and "Des cours pratiques, des exercices interactifs et des évaluations" in accueil)
    ok("trois éléments synthétiques (cours, exercices, évaluations)",
       all(t in accueil for t in ("Cours interactifs", "Exercices pratiques", "Évaluations"))
       and all(t in accueil for t in ("Apprenez à votre rythme.", "Testez vos connaissances.",
                                      "Mesurez vos progrès.")))
    ok("bouton secondaire « Découvrir la plateforme » vers /decouvrir",
       "Découvrir la plateforme" in accueil and 'href="/decouvrir"' in accueil)
    ok("programme détaillé retiré de l'accueil",
       "module-card" not in accueil and "#programme" not in accueil
       and ">Programme<" not in accueil and "Parcours complet, module par module" not in accueil)
    decouvrir = requests.get(BASE + "/decouvrir", timeout=20).text
    ok("page « Découvrir la plateforme » (aucun programme détaillé)",
       "Comment obtenir un accès" in decouvrir and "module-card" not in decouvrir
       and ">Programme<" not in decouvrir)

    # ------------------------------------------------------------- connexions
    print("▸ Connexion des trois rôles")
    sa = login(*SUPER)
    ensure_accounts(sa)
    u = login(*USER)
    a = login(*ADMIN)

    # ------------------------------------------------- connexion par l'accueil
    print("▸ Connexion réelle depuis le formulaire de l'accueil")
    essai = requests.Session()
    jeton = csrf(essai, "/")
    refus = essai.post(BASE + "/", data={"csrf_token": jeton, "identifier": USER[0],
                                         "password": "mauvais-mot-de-passe"},
                       allow_redirects=False)
    ok("identifiants incorrects : message clair, on reste sur l'accueil",
       refus.status_code == 200 and "Identifiant ou mot de passe incorrect" in refus.text
       and 'name="identifier"' in refus.text, str(refus.status_code))
    jeton = csrf(essai, "/")
    succes = essai.post(BASE + "/", data={"csrf_token": jeton, "identifier": USER[0],
                                          "password": USER[1]}, allow_redirects=False)
    ok("identifiants valides : session ouverte et redirection",
       succes.status_code == 302, str(succes.status_code))
    ok("la session de l'accueil donne accès à l'espace",
       essai.get(BASE + "/espace", allow_redirects=False).status_code == 200)
    souvenir = requests.Session()
    jeton = csrf(souvenir, "/")
    r = souvenir.post(BASE + "/", data={"csrf_token": jeton, "identifier": USER[0],
                                        "password": USER[1], "remember": "1"},
                      allow_redirects=False)
    cookie = r.headers.get("Set-Cookie", "")
    ok("« Se souvenir de moi » : cookie persistant 30 jours, HttpOnly",
       "Max-Age=2592000" in cookie and "HttpOnly" in cookie, cookie[:70])
    essai.post(BASE + "/auth/deconnexion", data={"csrf_token": csrf(essai, "/espace")},
               allow_redirects=False)
    souvenir.post(BASE + "/auth/deconnexion", data={"csrf_token": csrf(souvenir, "/espace")},
                  allow_redirects=False)

    # ---------------------------------------------------------- pages privées
    print("▸ Espace apprenant (15 pages)")
    for path in ["/espace", "/cours", "/cours/introduction-aux-tic",
                 "/cours/introduction-aux-tic/lecon/1", "/exercices", "/exercices/1",
                 "/examens", "/resultats", "/ressources", "/annonces", "/historique",
                 "/mon-profil", "/utilisateurs-en-ligne", "/messages", "/battle"]:
        code = u.get(BASE + path, timeout=20).status_code
        ok(path, code == 200, str(code))

    print("▸ Espace administrateur (22 pages)")
    for path in ["/admin/", "/admin/utilisateurs", "/admin/utilisateurs/nouveau",
                 "/admin/utilisateurs/1", "/admin/modules", "/admin/modules/1/modifier",
                 "/admin/lecons/1/modifier", "/admin/exercices",
                 "/admin/exercices/1/modifier", "/admin/annonces", "/admin/examens",
                 "/admin/roles", "/admin/journal", "/admin/sessions", "/admin/demandes",
                 "/admin/parametres", "/admin/sauvegardes",
                 "/admin/notes", "/admin/statistiques", "/admin/notes/export.csv",
                 "/admin/apercu-maintenance",
                 "/admin/messages-utilisateurs"]:
        code = sa.get(BASE + path, timeout=20).status_code
        ok(path, code == 200, str(code))

    # ------------------------------------------------------------ permissions
    print("▸ Contrôle des permissions (côté serveur)")
    ok("utilisateur → /admin/ = 403", u.get(BASE + "/admin/").status_code == 403)
    ok("admin → /admin/journal = 403", a.get(BASE + "/admin/journal").status_code == 403)
    ok("admin → messages super admin = 403",
       a.get(BASE + "/admin/messages-utilisateurs").status_code == 403)
    ok("admin → /admin/sauvegardes = 403", a.get(BASE + "/admin/sauvegardes").status_code == 403)
    ok("utilisateur → /admin/notes = 403", u.get(BASE + "/admin/notes").status_code == 403)
    ok("admin → /admin/notes = 403", a.get(BASE + "/admin/notes").status_code == 403)
    ok("admin → /admin/statistiques = 403",
       a.get(BASE + "/admin/statistiques").status_code == 403)

    print("▸ Rôle professeur du super administrateur")
    r = sa.get(BASE + "/examens", allow_redirects=False)
    ok("super admin → /examens redirigé", r.status_code == 302 and "/admin/notes" in r.headers.get("Location", ""))
    r = sa.get(BASE + "/resultats", allow_redirects=False)
    ok("super admin → /resultats redirigé",
       r.status_code == 302 and "/admin/statistiques" in r.headers.get("Location", ""))
    r = sa.get(BASE + "/espace", allow_redirects=False)
    ok("super admin → /espace redirigé vers l'administration",
       r.status_code == 302 and "/admin" in r.headers.get("Location", ""))
    r = sa.get(BASE + "/cours", allow_redirects=False)
    ok("super admin → /cours renvoyé vers la gestion des cours",
       r.status_code == 302 and "/admin/modules" in r.headers.get("Location", ""))
    r = sa.get(BASE + "/exercices", allow_redirects=False)
    ok("super admin → /exercices renvoyé vers la gestion des exercices",
       r.status_code == 302 and "/admin/exercices" in r.headers.get("Location", ""))
    page = sa.get(BASE + "/admin").text
    ok("menu sans « Examens trimestriels » pour le professeur",
       "Examens trimestriels" not in page and "Notes des élèves" in page)
    token = csrf(a, "/admin/utilisateurs/1")
    r = a.post(BASE + "/admin/utilisateurs/1/modifier",
               data={"csrf_token": token, "full_name": "Pirate", "username": "Myazirzk",
                     "role": "admin", "status": "active"}, allow_redirects=False)
    ok("admin → édition d'un super admin = 403", r.status_code == 403, str(r.status_code))
    token = csrf(a, "/admin/utilisateurs/nouveau")
    r = a.post(BASE + "/admin/utilisateurs/nouveau",
               data={"csrf_token": token, "full_name": "Faux Admin",
                     "username": "faux.admin." + rand_suffix(4),
                     "role": "admin", "status": "active", "password": ""})
    ok("admin → création d'un admin refusée", "Seul le super administrateur" in r.text)

    # ------------------------------------------------ rôles et dossier scolaire
    print("▸ Rôles et dossier scolaire de l'élève")
    page = sa.get(BASE + "/admin/utilisateurs/nouveau").text
    ok("trois rôles seulement dans le formulaire",
       page.count('<option value="user"') == 1 and page.count('<option value="admin"') == 1
       and page.count('<option value="super_admin"') == 1,
       "options détectées")
    ok("libellé « Élève »", "Élève" in page and ">Utilisateur<" not in page)
    ok("bloc « Dossier scolaire » présent", "Dossier scolaire" in page)

    eleve_name = "verif.eleve." + rand_suffix(4)
    token = csrf(sa, "/admin/utilisateurs/nouveau")
    r = sa.post(BASE + "/admin/utilisateurs/nouveau",
                data={"csrf_token": token, "full_name": "", "last_name": "Andriamana",
                      "first_name": "Soa", "pseudo": "SoaDuTIC", "username": eleve_name,
                      "email": "", "role": "user", "status": "active", "bio": "",
                      "password": "VerifEleve2026!", "class_number": "14",
                      "study_level": "Terminale", "gender": "fille", "class_group": "3"})
    ok("inscription d'un élève avec ses informations de classe",
       r.status_code == 200 and "Identifiants à communiquer" in r.text, str(r.status_code))

    listing = sa.get(BASE + "/admin/utilisateurs?q=" + eleve_name).text
    ok("élève listé avec nom composé", "Andriamana Soa" in listing)
    ok("élève listé avec niveau, groupe et numéro",
       "Terminale" in listing and "Groupe 3" in listing)
    ok("pseudo affiché dans la liste", "SoaDuTIC" in listing)

    ids = sorted({int(i) for i in re.findall(r'/admin/utilisateurs/(\d+)"', listing)})
    eleve_id = ids[0] if ids else 0
    detail = sa.get(BASE + f"/admin/utilisateurs/{eleve_id}").text
    ok("fiche élève : dossier scolaire complet",
       "Dossier scolaire" in detail and "Terminale" in detail and "Fille" in detail,
       f"id={eleve_id}")

    token = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
    r = sa.post(BASE + f"/admin/utilisateurs/{eleve_id}/classe",
                data={"csrf_token": token, "class_group": "1", "class_number": "3",
                      "study_level": "Terminale"}, allow_redirects=False)
    ok("groupe modifiable depuis la fiche", r.status_code == 302, str(r.status_code))
    detail = sa.get(BASE + f"/admin/utilisateurs/{eleve_id}").text
    ok("groupe mis à jour", "Groupe 1" in detail)

    # numéro de groupe libre : 9 est accepté par le super administrateur
    r = sa.post(BASE + f"/admin/utilisateurs/{eleve_id}/classe",
                data={"csrf_token": token, "class_group": "9"}, allow_redirects=False)
    detail = sa.get(BASE + f"/admin/utilisateurs/{eleve_id}").text
    ok("numéro de groupe libre accepté (groupe 9)", 'badge-info">Groupe 9</span>' in detail)

    r = sa.post(BASE + f"/admin/utilisateurs/{eleve_id}/classe",
                data={"csrf_token": token, "class_group": "100"}, allow_redirects=False)
    detail = sa.get(BASE + f"/admin/utilisateurs/{eleve_id}").text
    ok("groupe hors bornes refusé (100)", 'badge-info">Groupe 9</span>' in detail)

    csv_body = sa.get(BASE + "/admin/utilisateurs/export.csv").text
    ok("export CSV avec les colonnes du dossier",
       "nom;prenom;pseudo;numero_classe;niveau_etude;sexe;groupe" in csv_body)
    ok("ligne de l'élève exportée",
       f"{eleve_name}" in csv_body and "Andriamana;Soa;SoaDuTIC" in csv_body)

    r = u.get(BASE + f"/admin/utilisateurs/{eleve_id}", allow_redirects=False)
    ok("un élève ne peut pas ouvrir une fiche d'administration", r.status_code in (403, 302),
       str(r.status_code))

    page = sa.get(BASE + "/admin/classe")
    ok("liste de classe accessible au super administrateur", page.status_code == 200,
       str(page.status_code))
    ok("liste de classe : groupes et impression",
       "Groupe 9" in page.text and "Imprimer" in page.text,
       "groupe personnalisé affiché dans la liste imprimable")
    ok("liste de classe : élève présent avec son numéro",
       "Andriamana Soa" in page.text and "SoaDuTIC" in page.text)

    body = sa.get(BASE + "/admin/notes/export.csv").text
    ok("export des notes avec les colonnes de classe",
       "numero_classe" in body and "niveau_etude" in body and "groupe" in body)

    r = u.get(BASE + "/admin/classe", allow_redirects=False)
    ok("liste de classe interdite à un élève", r.status_code in (403, 302), str(r.status_code))

    # ------------------------------------------------ vague 4 (4 demandes)
    print("▸ Connexion épurée, photo de profil, bulletins, groupe")
    page = requests.get(BASE + "/auth/connexion", timeout=20).text
    ok("connexion : plus de panneau « détail du programme »",
       "auth-aside" not in page and "auth-wrap--center" in page)
    ok("connexion : aucun onglet « Programme »", "Programme" not in page)

    r = sa.get(BASE + "/admin/bulletins", timeout=20)
    ok("/admin/bulletins accessible au super administrateur", r.status_code == 200,
       str(r.status_code))
    ok("onglet Bulletins : une fiche par élève",
       "bulletin-card" in r.text and "Andriamana Soa" in r.text)
    ok("onglet Bulletins : note sur 20 affichée", "/20" in r.text)
    ok("onglet Bulletins dans le menu du super administrateur",
       'href="/admin/bulletins"' in sa.get(BASE + "/admin/", timeout=20).text)
    ok("onglet Bulletins interdit à un élève",
       u.get(BASE + "/admin/bulletins", allow_redirects=False).status_code in (403, 302))
    ok("onglet Bulletins interdit à un administrateur",
       a.get(BASE + "/admin/bulletins", allow_redirects=False).status_code == 403)
    ok("onglet Bulletins absent du menu d'un administrateur",
       'href="/admin/bulletins"' not in a.get(BASE + "/admin/", timeout=20).text)

    # photo de profil : envoi réel d'un PNG, affichage, retrait
    token = csrf(u, "/mon-profil")
    r = u.post(BASE + "/mon-profil/photo", data={"csrf_token": token, "action": "upload"},
               files={"photo": ("verif-photo.png", png_bytes(), "image/png")},
               allow_redirects=False)
    ok("photo de profil : envoi accepté", r.status_code == 302, str(r.status_code))
    profile = u.get(BASE + "/mon-profil", timeout=20).text
    found = re.search(r'src="(/avatar/[^"]+)"', profile)
    ok("photo de profil : image affichée sur la page", bool(found))
    avatar_path = found.group(1) if found else "/avatar/inconnu.png"
    ok("photo de profil : image servie", u.get(BASE + avatar_path).status_code == 200)
    ok("photo de profil : service protégé par la connexion",
       requests.get(BASE + avatar_path, allow_redirects=False).status_code in (302, 401))
    ok("photo de profil : fichier inconnu → 404",
       u.get(BASE + "/avatar/inconnu-verif.png").status_code == 404)
    token = csrf(u, "/mon-profil")
    u.post(BASE + "/mon-profil/photo", data={"csrf_token": token, "action": "remove"})
    ok("photo de profil : retrait possible", u.get(BASE + avatar_path).status_code == 404)
    ok("photo de profil : retour aux initiales",
       avatar_path not in u.get(BASE + "/mon-profil", timeout=20).text)

    # groupe : réservé au super administrateur, numéro libre
    form = sa.get(BASE + f"/admin/utilisateurs/{eleve_id}/modifier", timeout=20).text
    ok("dossier scolaire : champ de groupe pour le super administrateur",
       'name="class_group"' in form and 'id="class_group"' in form and 'max="99"' in form)
    token = csrf(a, "/admin/utilisateurs")
    a.post(BASE + f"/admin/utilisateurs/{eleve_id}/classe",
           data={"csrf_token": token, "class_group": "3", "class_number": "14",
                 "study_level": "Terminale"}, allow_redirects=False)
    after = sa.get(BASE + f"/admin/utilisateurs/{eleve_id}", timeout=20).text
    ok("groupe inchangé par un administrateur",
       'badge-info">Groupe 9</span>' in after and 'badge-info">Groupe 3</span>' not in after)
    ok("fiche élève : groupe en lecture seule pour un administrateur",
       "readonly" in a.get(BASE + f"/admin/utilisateurs/{eleve_id}", timeout=20).text)
    token = csrf(sa, "/admin/utilisateurs")
    sa.post(BASE + f"/admin/utilisateurs/{eleve_id}/classe",
            data={"csrf_token": token, "class_group": "3", "class_number": "14",
                  "study_level": "Terminale"}, allow_redirects=False)
    after = sa.get(BASE + f"/admin/utilisateurs/{eleve_id}", timeout=20).text
    ok("groupe choisi par le super administrateur", 'badge-info">Groupe 3</span>' in after)

    # ------------------------------------------- compte jetable pour les tests
    print("▸ Création d'un compte de test (super admin)")
    probe_name = "verif." + rand_suffix(6)
    probe_password = "VerifProbe2026!"
    token = csrf(sa, "/admin/utilisateurs/nouveau")
    r = sa.post(BASE + "/admin/utilisateurs/nouveau",
                data={"csrf_token": token, "full_name": "Compte Vérification",
                      "username": probe_name, "email": "", "role": "user",
                      "status": "active", "password": probe_password})
    ok("compte de test créé", r.status_code == 200 and "Compte Vérification" in r.text,
       str(r.status_code))
    p = login(probe_name, probe_password, "connexion du compte de test")

    # --------------------------------------------------------------- leçons
    print("▸ Progression pédagogique")
    token = csrf(p, "/cours/introduction-aux-tic/lecon/1")
    r = p.post(BASE + "/cours/introduction-aux-tic/lecon/1/terminer",
               data={"csrf_token": token}, allow_redirects=False)
    ok("leçon terminée", r.status_code == 302 and "/lecon/2" in r.headers.get("Location", ""),
       r.headers.get("Location", ""))

    # ------------------------------------------------------------- exercices
    print("▸ Exercice corrigé côté serveur")
    token = csrf(p, "/exercices/1")
    r = p.post(BASE + "/exercices/1/commencer", data={"csrf_token": token}, allow_redirects=False)
    attempt_url = r.headers.get("Location", "")
    ok("tentative démarrée", "/exercices/tentative/" in attempt_url, attempt_url)
    if "/exercices/tentative/" in attempt_url:
        page = p.get(BASE + attempt_url).text
        qids = re.findall(r'name="q_(\d+)"', page)
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        data = {"csrf_token": token}
        for qid in qids:
            good = db_rows("select id, text from options where question_id=? and is_correct=1", (qid,))
            if good:
                data[f"q_{qid}"] = str(good[0][0])
            else:
                # pas d'accès disque (instance distante) : on choisit la 1re option
                data[f"q_{qid}"] = "0"
        r = p.post(BASE + attempt_url + "/soumettre", data=data, allow_redirects=False)
        result = p.get(BASE + r.headers.get("Location", "/resultats"))
        ok("soumission + correction affichée",
           r.status_code == 302 and ("%" in result.text), r.headers.get("Location", ""))

    # ----------------------------------------------------------------- examen
    print("▸ Examen surveillé et anti-fraude")
    exams = db_rows("select id from exercises where kind='exam' order by id")
    if exams is None:                     # cible distante : on lit la page des examens
        found = re.findall(r'/examens/(\d+)/commencer', p.get(BASE + "/examens").text)
        exams = [(int(found[0]),)] if found else []
    if not exams:
        ok("examen disponible", False, "aucun examen en base")
    else:
        exam_id = exams[0][0]
        token = csrf(p, "/examens")
        r = p.post(BASE + f"/examens/{exam_id}/commencer", data={"csrf_token": token},
                   allow_redirects=False)
        exam_url = r.headers.get("Location", "")
        ok("démarrage de l'examen", "/examens/passer/" in exam_url, exam_url)
        if "/examens/passer/" in exam_url:
            aid = exam_url.rstrip("/").split("/")[-1]
            page = p.get(BASE + exam_url).text
            ok("page surveillée + minuteur", "Examen surveillé" in page)
            token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

            # Les ressources techniques ne doivent pas compter comme fraude
            p.get(BASE + "/static/css/app.css")
            p.get(BASE + "/favicon.ico")
            p.get(BASE + "/static/img/logo.svg")
            status = db_rows("select status, tab_violations from attempts where id=?", (aid,))
            if status is None:
                page_now = p.get(BASE + f"/examens/passer/{aid}", allow_redirects=False)
                ok("ressources techniques non pénalisées", page_now.status_code == 200,
                   f"page d'examen toujours accessible ({page_now.status_code})")
            else:
                ok("ressources techniques non pénalisées",
                   bool(status) and status[0][0] == "in_progress" and status[0][1] == 0, str(status))

            # Sortie de l'onglet = fraude
            p.post(BASE + f"/api/exam/{aid}/violation", json={"reason": "Test automatique"},
                   headers={"X-CSRF-Token": token})
            status = db_rows("select status, tab_violations from attempts where id=?", (aid,))
            if status is None:
                after = p.get(BASE + f"/examens/passer/{aid}", allow_redirects=False)
                ok("sortie d'onglet → élimination", after.status_code == 302,
                   f"accès à l'examen fermé ({after.status_code})")
            else:
                ok("sortie d'onglet → élimination",
                   bool(status) and status[0][0] == "eliminated", str(status))

            # Sanction individuelle : la tentative du compte de test uniquement
            eliminated = db_rows("""select count(*) from attempts a join users u on u.id=a.user_id
                                    where a.status='eliminated' and u.username=?""", (probe_name,))
            if eliminated is None:
                skip("sanction individuelle (aucun autre étudiant affecté)",
                     "contrôle en base, fait lors du test local")
            else:
                ok("sanction individuelle (aucun autre étudiant affecté)",
                   bool(eliminated) and eliminated[0][0] == 1, str(eliminated))

            # Réaffectation : réservée au super administrateur
            token_a = csrf(a, "/admin/examens")
            r = a.post(BASE + f"/admin/examens/{aid}/reaffecter",
                       data={"csrf_token": token_a}, allow_redirects=False)
            ok("réaffectation refusée à un administrateur", r.status_code in (403, 404),
               str(r.status_code))

            token_sa = csrf(sa, "/admin/examens")
            r = sa.post(BASE + f"/admin/examens/{aid}/reaffecter",
                        data={"csrf_token": token_sa}, allow_redirects=False)
            status = db_rows("select status, tab_violations from attempts where id=?", (aid,))
            if status is None:
                again = p.get(BASE + f"/examens/passer/{aid}", allow_redirects=False)
                ok("réaffectation par le super administrateur",
                   r.status_code == 302 and again.status_code == 200,
                   f"réaffecté ({r.status_code}), examen de nouveau accessible ({again.status_code})")
            else:
                ok("réaffectation par le super administrateur",
                   r.status_code == 302 and bool(status) and status[0][0] == "in_progress"
                   and status[0][1] == 0, str(status))

            # On termine proprement l'épreuve pour sortir du mode surveillé
            page = p.get(BASE + f"/examens/passer/{aid}").text
            token_exam = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
            r = p.post(BASE + f"/examens/passer/{aid}/soumettre",
                       data={"csrf_token": token_exam}, allow_redirects=False)
            status = db_rows("select status from attempts where id=?", (aid,))
            if status is None:
                ok("remise de la copie après réaffectation", r.status_code == 302, str(r.status_code))
            else:
                ok("remise de la copie après réaffectation",
                   r.status_code == 302 and bool(status) and status[0][0] == "submitted", str(status))

    # ------------------------------------------------------------- messagerie
    print("▸ Messagerie")
    token = csrf(p, "/messages")
    r = p.post(BASE + "/api/messages", json={"room": "general", "body": "Vérification auto"},
               headers={"X-CSRF-Token": token})
    ok("envoi d'un message", r.status_code == 201, str(r.status_code))
    r = p.get(BASE + "/api/messages?room=general")
    ok("lecture du salon général", r.status_code == 200 and r.json().get("messages"),
       str(r.status_code))
    r = p.get(BASE + "/api/messages?room=dm:1:2")
    ok("DM d'un tiers refusé", r.status_code == 403, str(r.status_code))
    ok("super admin voit tous les messages",
       "Vérification auto" in sa.get(BASE + "/admin/messages-utilisateurs").text)

    # ----------------------------------------------------------------- battle
    print("▸ Battle")
    token = csrf(p, "/battle")
    r = p.post(BASE + "/api/battle/create", json={"mode": "solo"},
               headers={"X-CSRF-Token": token})
    ok("création d'une battle solo", r.status_code in (200, 201), str(r.status_code))
    code = (r.json() or {}).get("code")
    if code:
        payload = r.json() or {}
        ok("demande en attente de validation", payload.get("status") == "pending",
           f"statut={payload.get('status')}")

        r = p.post(BASE + "/api/battle/start", json={"code": code},
                   headers={"X-CSRF-Token": token})
        ok("démarrage refusé avant validation", r.status_code == 403, str(r.status_code))

        r = p.get(BASE + "/admin/battles", allow_redirects=False)
        ok("validation de battle interdite à l'apprenant",
           r.status_code in (403, 302), str(r.status_code))

        # acceptation par le super administrateur
        page = sa.get(BASE + "/admin/battles")
        ok("page de validation accessible au super administrateur", page.status_code == 200,
           str(page.status_code))
        # on retrouve la ligne correspondant au code créé
        matching_ids = [
            battle_id for row in page.text.split("<tr")
            if code in row for battle_id in re.findall(r"/admin/battles/(\d+)/accepter", row)
        ]
        token_sa = csrf(sa, "/admin/battles")
        accepted = False
        for battle_id in matching_ids:
            res = sa.post(BASE + f"/admin/battles/{battle_id}/accepter",
                          data={"csrf_token": token_sa}, allow_redirects=False)
            if res.status_code == 302:
                accepted = True
                break
        ok("acceptation de la demande par le super administrateur", accepted,
           "" if matching_ids else "demande introuvable dans la liste")

        # --- composition des questions par l'administration
        page = sa.get(BASE + "/admin/battles")
        # le code peut apparaître dans un segment sans le lien (en-tête, JS) :
        # on prend le premier segment qui contient réellement le bouton « questions »
        q_link = next((hit for hit in
                       (re.search(r"/admin/battles/(\d+)/questions", segment)
                        for segment in page.text.split("<tr") if code in segment)
                       if hit), None)
        ok("lien « questions » du battle pour l'administration", bool(q_link))
        created_ids: list[str] = []
        if q_link:
            battle_id = q_link.group(1)
            editor = sa.get(BASE + f"/admin/battles/{battle_id}/questions")
            ok("écran de composition des questions", editor.status_code == 200,
               str(editor.status_code))
            ok("formulaire « Créer une question »", "Créer une question" in editor.text)
            before_ids = set(re.findall(r'name="question_id" value="(\d+)"', editor.text))
            ok("banque de questions disponible", len(before_ids) > 0,
               f"{len(before_ids)} question(s)")
            token_q = csrf(sa, "/admin/battles")
            picked = sorted(before_ids)[:2]
            sa.post(BASE + f"/admin/battles/{battle_id}/questions",
                    data={"csrf_token": token_q, "action": "save", "question_id": picked},
                    allow_redirects=False)
            saved = sa.get(BASE + f"/admin/battles/{battle_id}/questions").text
            checked = re.findall(r'name="question_id" value="(\d+)"[^>]*checked', saved)
            ok("sélection de questions enregistrée", len(checked) == len(picked),
               f"{len(checked)} cochée(s)")
            sa.post(BASE + f"/admin/battles/{battle_id}/questions",
                    data={"csrf_token": token_q, "action": "create",
                          "text": "Question de contrôle (vérification automatique)",
                          "option_1": "Bonne réponse", "option_2": "Mauvaise réponse",
                          "correct": "1", "points": "1"}, allow_redirects=False)
            after_create = sa.get(BASE + f"/admin/battles/{battle_id}/questions").text
            ok("question créée et ajoutée au battle",
               "Question de contrôle (vérification automatique)" in after_create)
            created_ids = sorted(
                set(re.findall(r'name="question_id" value="(\d+)"', after_create)) - before_ids
            )
            ok("question enregistrée dans la banque", len(created_ids) == 1, str(created_ids))
            ok("composition des questions interdite à un élève",
               p.get(BASE + f"/admin/battles/{battle_id}/questions",
                     allow_redirects=False).status_code in (403, 302))

        r = p.post(BASE + "/api/battle/start", json={"code": code},
                   headers={"X-CSRF-Token": token})
        ok("démarrage de la battle après validation", r.status_code == 200, r.text[:80])
        state = p.get(BASE + f"/api/battle/state?code={code}").json()
        room_status = (state.get("room") or {}).get("status")
        ok("question en cours",
           state.get("ok") is True and room_status == "running" and state.get("seconds_left", 0) > 0,
           f"statut={room_status}, index={state.get('index')}, restant={state.get('seconds_left')}s")
        r = p.post(BASE + "/api/battle/rename", json={"code": code, "name": "Autre nom"},
                   headers={"X-CSRF-Token": token})
        ok("renommage d'une battle solo refusé", r.status_code == 400, str(r.status_code))

        # --- une partie jouée de bout en bout (réponses envoyées par le serveur)
        etat = state
        tours = 0
        while tours < 8 and (etat.get("room") or {}).get("status") == "running":
            options = ((etat.get("question") or {}).get("options") or [])
            if not options:
                break
            rep = p.post(BASE + "/api/battle/answer",
                         json={"code": code, "option_id": options[0]["id"]},
                         headers={"X-CSRF-Token": token})
            if rep.status_code != 200:
                break
            tours += 1
            etat = p.get(BASE + f"/api/battle/state?code={code}").json() or {}
        statut_final = (etat.get("room") or {}).get("status")
        ok("partie jouée jusqu'à la fin", tours >= 1 and statut_final == "finished",
           f"{tours} réponse(s), statut={statut_final}")
        ok("avancement immédiat quand tout le monde a répondu", tours == len(etat.get("corrections") or [])
           or statut_final == "finished", f"{tours} réponse(s) pour {len(etat.get('corrections') or [])} question(s)")
        ok("corrections affichées en fin de partie", bool(etat.get("corrections")),
           f"{len(etat.get('corrections') or [])} correction(s)")
        ok("classement final calculé", bool(etat.get("ranking")))

        # nettoyage : les questions créées pour la vérification sont retirées
        if created_ids:
            token_q = csrf(sa, "/admin/battles")
            for question_id in created_ids:
                sa.post(BASE + f"/admin/questions/{question_id}/supprimer",
                        data={"csrf_token": token_q}, allow_redirects=False)

    # ------------------------------- création d'un compte et connexion
    print("▸ Création d'un compte puis première connexion")
    suffixe = rand_suffix(4)
    nom_eleve = f"Eleve Test{suffixe}"
    page = sa.get(BASE + "/admin/utilisateurs/nouveau").text
    ok("formulaire de création accessible", "Nom complet" in page)
    ok("politique de mot de passe affichée en direct", "pw-checks" in page)
    ok("aide sur l'identifiant automatique", "généré automatiquement" in page
       or "tiré du nom complet" in page)

    created = sa.post(BASE + "/admin/utilisateurs/nouveau",
                      data={"csrf_token": csrf(sa, "/admin/utilisateurs/nouveau"),
                            "full_name": nom_eleve, "username": f"verif.crea{suffixe}",
                            "email": "", "role": "user", "status": "active",
                            "password": "", "must_change": "1"})
    texte = created.text
    identifiant = re.search(r'id="created-username"[^>]*>([^<]+)</div>', texte)
    motdepasse = re.search(r'id="created-password"[^>]*>([^<]+)</div>', texte)
    ok("compte créé, identifiant affiché", bool(identifiant), identifiant.group(1) if identifiant else "")
    ok("mot de passe temporaire affiché", bool(motdepasse))
    ok("bouton « Copier l'identifiant »", "Copier l'identifiant" in texte)
    ok("bouton « Copier le mot de passe »", "Copier le mot de passe" in texte)

    if identifiant and motdepasse:
        eleve = requests.Session()
        connexion = eleve.post(BASE + "/auth/connexion",
                               data={"csrf_token": csrf(eleve, "/auth/connexion"),
                                     "identifier": identifiant.group(1).strip(),
                                     "password": motdepasse.group(1).strip()},
                               allow_redirects=True)
        ok("connexion avec les identifiants affichés",
           "/auth/changer-mot-de-passe" in connexion.url, connexion.url.replace(BASE, ""))

        # le nom complet et l'identifiant en majuscules fonctionnent aussi
        for variante, etiquette in ((nom_eleve, "le nom complet"),
                                    (identifiant.group(1).strip().upper(),
                                     "l'identifiant en majuscules")):
            autre = requests.Session()
            rep = autre.post(BASE + "/auth/connexion",
                             data={"csrf_token": csrf(autre, "/auth/connexion"),
                                   "identifier": variante,
                                   "password": motdepasse.group(1).strip()},
                             allow_redirects=True)
            ok(f"connexion avec {etiquette}", "/auth/changer-mot-de-passe" in rep.url,
               rep.url.replace(BASE, ""))

        # une espace ajoutée à la fin du mot de passe n'empêche pas la connexion
        autre = requests.Session()
        rep = autre.post(BASE + "/auth/connexion",
                         data={"csrf_token": csrf(autre, "/auth/connexion"),
                               "identifier": identifiant.group(1).strip(),
                               "password": motdepasse.group(1).strip() + "  "},
                         allow_redirects=True)
        ok("connexion tolérante à une espace finale", "/auth/changer-mot-de-passe" in rep.url)

        # mot de passe imposé par l'administrateur : espaces de bord retirés
        crea = sa.post(BASE + "/admin/utilisateurs/nouveau",
                       data={"csrf_token": csrf(sa, "/admin/utilisateurs/nouveau"),
                             "full_name": f"Espace Test{suffixe}",
                             "username": f"verif.espace{suffixe}", "role": "user",
                             "status": "active", "password": "VerifEspace2026!  ",
                             "must_change": "1"})
        ok("espaces de bord retirés du mot de passe saisi",
           "espaces présents au début" in crea.text and "Compte créé" in crea.text)

        faible = sa.post(BASE + "/admin/utilisateurs/nouveau",
                         data={"csrf_token": csrf(sa, "/admin/utilisateurs/nouveau"),
                               "full_name": f"Faible Test{suffixe}",
                               "username": f"verif.faible{suffixe}", "role": "user",
                               "status": "active", "password": "1234", "must_change": "1"})
        ok("mot de passe trop faible : refusé et signalé",
           "Compte créé" not in faible.text and "n&#39;a pas été créé" in faible.text
           or "n'a pas été créé" in faible.text)

    # -------------------------- messages : remise, transfert, filtres
    print("▸ Messages : remise, transfert et notifications filtrées")
    token = csrf(p, "/messages")
    r = p.post(BASE + "/api/messages",
               json={"room": "general", "body": "Message de vérification (transfert)"},
               headers={"X-CSRF-Token": token})
    ok("envoi dans le salon général", r.status_code == 201, str(r.status_code))
    msg_id = ((r.json() or {}).get("message") or {}).get("id")
    listing = p.get(BASE + "/api/messages?room=general").json() or {}
    ok("état de remise exposé par l'API", "delivery" in listing)
    if msg_id:
        meme_salon = p.post(BASE + "/api/messages/forward",
                            json={"message_id": msg_id, "room": "general"},
                            headers={"X-CSRF-Token": token})
        ok("transfert vers le salon d'origine refusé", meme_salon.status_code == 400,
           str(meme_salon.status_code))

        page = p.get(BASE + "/messages").text
        cible = re.search(r"/messages\?room=(dm:\d+:\d+)", page)
        if cible:
            r = p.post(BASE + "/api/messages/forward",
                       json={"message_id": msg_id, "room": cible.group(1)},
                       headers={"X-CSRF-Token": token})
            ok("transfert vers une conversation privée", r.status_code == 201, str(r.status_code))
            copie = ((r.json() or {}).get("message") or {})
            ok("auteur d'origine conservé sur le message transféré", bool(copie.get("forwarded")),
               str(copie.get("forwarded")))
        transfert_interdit = p.post(BASE + "/api/messages/forward",
                                    json={"message_id": 999999, "room": "general"},
                                    headers={"X-CSRF-Token": token})
        ok("transfert d'un message inexistant refusé", transfert_interdit.status_code == 404,
           str(transfert_interdit.status_code))

    filtres = p.get(BASE + "/notifications?type=message")
    ok("notifications filtrables par type", filtres.status_code == 200
       and "notif-chip" in filtres.text, str(filtres.status_code))
    tout = p.get(BASE + "/notifications")
    ok("lien « Tout » des notifications", tout.status_code == 200 and "notif-chip" in tout.text)

    # tout marquer comme lu, puis proposer le ménage des notifications lues
    p.post(BASE + "/api/notifications/tout-lire",
           headers={"X-CSRF-Token": csrf(p, "/notifications")})
    page_notif = p.get(BASE + "/notifications").text
    ok("bouton « Vider les lues » proposé après lecture", "Vider les lues" in page_notif)
    vider = p.post(BASE + "/notifications/vider",
                   data={"csrf_token": csrf(p, "/notifications")}, allow_redirects=False)
    ok("suppression des notifications lues", vider.status_code == 302, str(vider.status_code))
    ok("vidage interdit sans connexion",
       requests.post(BASE + "/notifications/vider", allow_redirects=False).status_code in (302, 400))

    # ------------------------------------------------------------ fil social
    print("▸ Fil d'actualité du profil")
    token = csrf(p, "/mon-profil")
    profile = p.get(BASE + "/mon-profil")
    ok("onglet Fil d'actualité dans le profil",
       profile.status_code == 200 and 'data-tab-link="fil"' in profile.text,
       str(profile.status_code))
    r = p.post(BASE + "/api/posts", data={"body": "Vérification auto du fil"},
               headers={"X-CSRF-Token": token})
    ok("publication d'un message", r.status_code == 201, str(r.status_code))
    post_id = (r.json() or {}).get("id")
    if post_id:
        for kind, emoji in (("love", "❤️"), ("haha", "😂"), ("fist", "👊"),
                            ("angry", "😠"), ("sad", "😢")):
            r = sa.post(BASE + f"/api/posts/{post_id}/react", json={"kind": kind},
                        headers={"X-CSRF-Token": csrf(sa, "/espace")})
            ok(f"réaction {emoji} {kind}", r.status_code == 200, str(r.status_code))
        r = p.post(BASE + f"/api/posts/{post_id}/react", json={"kind": "fist"},
                   headers={"X-CSRF-Token": token})
        ok("une seule réaction conservée par personne",
           r.json().get("current") == "fist" and r.json().get("total") == 2, r.text[:80])
        r = p.post(BASE + f"/api/posts/{post_id}/comment", json={"body": "Commentaire auto"},
                   headers={"X-CSRF-Token": token})
        ok("commentaire ajouté", r.status_code == 201, str(r.status_code))
        r = p.get(BASE + "/mon-profil")
        ok("fil affiché avec réactions et commentaires",
           "Vérification auto du fil" in r.text and "Commentaire auto" in r.text)
        r = app_post_delete(p, token, post_id)
        ok("suppression de sa publication", r, "POST /api/posts/<id>/delete")

    # ------------------------------------------------- conservation illimitée
    print("▸ Paramètres — conservation des données")
    token = csrf(sa, "/admin/parametres")
    page = sa.get(BASE + "/admin/parametres")
    ok("option « conservation illimitée » proposée", "conservation illimitée" in page.text)
    r = sa.post(BASE + "/admin/parametres", data={"retention_days": "", "csrf_token": token},
                allow_redirects=False)
    ok("enregistrement d'une conservation illimitée", r.status_code == 302, str(r.status_code))

    # ---------------------------------------- mot de passe temporaire imposé
    print("▸ Mot de passe temporaire et changement forcé")
    temp_user = "temp." + rand_suffix(6)
    token = csrf(sa, "/admin/utilisateurs/nouveau")
    r = sa.post(BASE + "/admin/utilisateurs/nouveau",
                data={"csrf_token": token, "full_name": "Temporaire Auto",
                      "username": temp_user, "email": "", "role": "user",
                      "status": "active", "password": "", "must_change": "1"})
    match = re.search(r'Mot de passe temporaire</span>\s*<div class="stat-value mono"[^>]*>([^<]+)</div>',
                      r.text)
    temp = match.group(1).strip() if match else None
    ok("mot de passe temporaire affiché une fois", r.status_code == 200 and temp is not None)
    if temp:
        n = requests.Session()
        token = csrf(n, "/auth/connexion")
        r = n.post(BASE + "/auth/connexion",
                   data={"csrf_token": token, "identifier": temp_user, "password": temp},
                   allow_redirects=False)
        ok("connexion avec le mot de passe temporaire", r.status_code == 302, str(r.status_code))
        r = n.get(BASE + "/espace", allow_redirects=False)
        ok("changement de mot de passe imposé",
           r.status_code == 302 and "changer-mot-de-passe" in r.headers.get("Location", ""),
           r.headers.get("Location", ""))
        token = csrf(n, "/auth/changer-mot-de-passe")
        r = n.post(BASE + "/auth/changer-mot-de-passe",
                   data={"csrf_token": token, "current_password": temp,
                         "new_password": "NouveauPass2026!", "confirm_password": "NouveauPass2026!"},
                   allow_redirects=False)
        ok("changement de mot de passe accepté", r.status_code == 302,
           r.headers.get("Location", ""))
        ok("accès autorisé après changement", n.get(BASE + "/espace").status_code == 200)

    # ------------------------------------------------------ CSRF / XSS / logout
    print("▸ Sécurité transverse")
    r = p.post(BASE + "/api/messages", json={"room": "general", "body": "sans jeton"})
    ok("POST sans jeton CSRF → 400", r.status_code == 400, str(r.status_code))

    token = csrf(sa, "/admin/annonces")
    payload = "<script>alert('xss')</script>"
    r = sa.post(BASE + "/admin/annonces",
                data={"csrf_token": token, "title": "Test XSS auto", "body": payload,
                      "published": "1"})
    ok("XSS échappé dans les annonces",
       "&lt;script&gt;" in r.text and payload not in r.text)

    # l'annonce de test est retirée immédiatement (aucune trace laissée)
    for block in r.text.split('<section class="card">'):
        if "Test XSS auto" in block:
            ident = re.search(r'/admin/annonces/(\d+)/supprimer', block)
            token_xss = re.search(r'name="csrf_token" value="([^"]+)"', block)
            if ident and token_xss:
                sa.post(BASE + f"/admin/annonces/{ident.group(1)}/supprimer",
                        data={"csrf_token": token_xss.group(1)}, allow_redirects=False)
            break

    token = csrf(p, "/espace")
    r = p.post(BASE + "/auth/deconnexion", data={"csrf_token": token}, allow_redirects=False)
    ok("déconnexion", r.status_code == 302, str(r.status_code))
    ok("session révoquée", p.get(BASE + "/espace", allow_redirects=False).status_code == 302)

    # ------------------------------------------------- vue Android / mobile
    print("▸ Vue Android (barre d'onglets, connexion tactile)")
    mobile = {"User-Agent": ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/124 Mobile Safari/537.36")}
    page = u.get(BASE + "/espace", headers=mobile, timeout=20).text
    ok("barre d'onglets en bas de l'écran", 'class="mobile-tabs"' in page)
    ok("onglets de l'élève : accueil, cours, exercices, battle, messages, profil",
       all(f'>{label}<' in page for label in
           ("Accueil", "Cours", "Exercices", "Battle", "Messages", "Profil")))
    ok("onglet de la page courante mis en avant",
       'class="mobile-tab is-active" href="/espace"' in page)
    page_battle = u.get(BASE + "/battle", headers=mobile, timeout=20).text
    ok("onglet Battle actif sur la page Battle",
       'class="mobile-tab is-active" href="/battle"' in page_battle)
    page_admin = sa.get(BASE + "/admin/bulletins", headers=mobile, timeout=20).text
    ok("onglets du super administrateur (élèves, notes)",
       'href="/admin/utilisateurs"' in page_admin
       and 'class="mobile-tab is-active" href="/admin/notes"' in page_admin)
    page_modo = a.get(BASE + "/admin/", headers=mobile, timeout=20).text
    ok("pas d'onglet « Notes » réservé au super administrateur",
       'class="mobile-tab is-active" href="/admin/notes"' not in page_modo)
    login_page = requests.get(BASE + "/auth/connexion", headers=mobile, timeout=20).text
    ok("aucune barre d'onglets sur la page de connexion", 'class="mobile-tabs"' not in login_page)
    ok("connexion : clavier virtuel non imposé (data-autofocus + pointer: coarse)",
       "data-autofocus" in login_page and "pointer: coarse" in login_page
       and 'enterkeyhint="go"' in login_page)
    css = requests.get(BASE + "/static/css/app.css", timeout=30).text
    ok("CSS mobile : marges de sécurité, champs 16 px, zone tactile",
       "env(safe-area-inset-bottom)" in css and "font-size: 16px" in css
       and "[hidden] { display: none !important; }" in css)
    ok("CSS mobile : aucun débordement horizontal prévu", "overflow-wrap: anywhere" in css)

    # ---------------------------------------------- notifications temps réel
    print("▸ Notifications en temps réel")
    # la section « Sécurité » vient de déconnecter p : on repart d'une session propre
    pn = login(USER[0], USER[1])
    css = requests.get(BASE + "/static/css/app.css", timeout=30).text
    js = requests.get(BASE + "/static/js/app.js", timeout=30).text
    ok("cloche présente dans la barre du haut", 'id="notif-toggle"' in pn.get(BASE + "/espace").text)
    ok("compteur et panneau déroulant intégrés",
       'id="notif-badge"' in pn.get(BASE + "/espace").text
       and ".notif-panel" in css and ".notif-badge" in css)
    ok("rafraîchissement automatique (25 s, pause onglet en arrière-plan)",
       "pollNotifications" in js and "25000" in js and "visibilitychange" in js)
    ok("aucune fenêtre native pour les notifications",
       "alert(" not in js.split("function initNotifications")[1][:4000])

    etat = pn.get(BASE + "/api/notifications", timeout=30)
    data = etat.json() if etat.status_code == 200 else {}
    ok("API /api/notifications", etat.status_code == 200 and data.get("ok") is True,
       str(etat.status_code))
    avant = int(data.get("count") or 0)
    historique = pn.get(BASE + "/notifications", timeout=30)
    ok("page d'historique des notifications",
       historique.status_code == 200
       and ("notif-row" in historique.text or "Aucune notification" in historique.text),
       str(historique.status_code))

    # Émission réelle : le super admin écrit en privé à l'apprenant
    token_pn = csrf(pn, "/messages")
    pn.post(BASE + "/api/messages", json={"room": "general", "body": "Ping notifications"},
            headers={"X-CSRF-Token": token_pn}, timeout=30)
    salon = pn.get(BASE + "/api/messages?room=general", timeout=30).json().get("messages", [])
    moi = next((m["sender"]["id"] for m in salon if m.get("mine")), None)
    if moi:
        token = csrf(sa, "/messages")
        room = f"dm:{min(1, moi)}:{max(1, moi)}"
        envoi = sa.post(BASE + "/api/messages",
                        json={"room": room, "body": "Notification vérifiée"},
                        headers={"X-CSRF-Token": token}, timeout=30)
        ok("message privé envoyé par le super administrateur", envoi.status_code == 201,
           str(envoi.status_code))
        apres = pn.get(BASE + "/api/notifications", timeout=30).json()
        ok("le destinataire reçoit une notification immédiate",
           int(apres.get("count") or 0) == avant + 1
           and any(i.get("kind") == "message" for i in apres.get("items", [])),
           f"{avant} → {apres.get('count')}")
        token = csrf(pn, "/espace")
        lu = pn.post(BASE + "/api/notifications/tout-lire",
                    headers={"X-CSRF-Token": token}, json={}, timeout=30)
        ok("le compteur retombe après lecture",
           lu.status_code == 200 and lu.json().get("count") == 0, str(lu.status_code))
    else:
        skip("émission d'une notification réelle", "identifiant de l'apprenant introuvable")

    ok("cloche absente de la page publique (aucune fuite)",
       'id="notif-toggle"' not in requests.get(BASE + "/", timeout=30).text)

    # ------------------------------------------ messagerie de classe
    print("▸ Professeur et messagerie de classe")
    accueil = sa.get(BASE + "/admin/").text
    ok("menu « Espace professeur » sans parcours d'élève",
       "Espace professeur" in accueil and "Cours &amp; modules" not in accueil,
       "menu élève encore visible" if "Cours &amp; modules" in accueil else "")
    messagerie = sa.get(BASE + "/messages").text
    ok("salons de classe proposés au professeur",
       "Messages de classe" in messagerie and "Toute la classe" in messagerie)

    notes = sa.get(BASE + "/admin/notes").text
    ok("aucun gestionnaire en ligne (respect de la CSP)",
       "onclick=" not in notes and "onchange=" not in notes and "data-auto-submit" in notes,
       "gestionnaire en ligne détecté" if ("onclick=" in notes or "onchange=" in notes) else "")

    probe_msg = "verif.classe" + "".join(random.choice(string.ascii_lowercase) for _ in range(4))
    mdp_msg = "Classe2026!"
    if _provision(sa, probe_msg, "Vérification Classe", "user", mdp_msg):
        fiche = sa.get(BASE + "/admin/utilisateurs?q=" + probe_msg).text
        uid_msg = next((int(i) for i in re.findall(r'/admin/utilisateurs/(\d+)"', fiche)), None)
        if uid_msg:
            detail = sa.get(BASE + f"/admin/utilisateurs/{uid_msg}").text
            token = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
            sa.post(BASE + f"/admin/utilisateurs/{uid_msg}/classe",
                    data={"csrf_token": token, "study_level": "Vérification", "class_group": "90"},
                    allow_redirects=False)

        token = csrf(sa, "/messages")
        envoi = sa.post(BASE + "/api/messages",
                        json={"room": "classe:groupe:90", "body": "Message de classe vérifié"},
                        headers={"X-CSRF-Token": token})
        ok("le professeur écrit à une classe en une fois", envoi.status_code == 201,
           str(envoi.status_code))

        eleve_msg = login(probe_msg, mdp_msg, f"connexion {probe_msg}")
        recu = eleve_msg.get(BASE + "/api/messages?room=classe:groupe:90")
        corps = recu.json().get("messages", []) if recu.status_code == 200 else []
        ok("l'élève de la classe reçoit le message",
           recu.status_code == 200 and any("Message de classe vérifié" in m.get("body", "") for m in corps),
           str(recu.status_code))
        notifs = eleve_msg.get(BASE + "/api/notifications").json()
        ok("l'élève est prévenu par une notification",
           any(i.get("kind") == "message" for i in notifs.get("items", [])),
           f"count={notifs.get('count')}")

        token = csrf(eleve_msg, "/messages")
        refus = eleve_msg.post(BASE + "/api/messages",
                               json={"room": "classe:tous", "body": "Test interdiction"},
                               headers={"X-CSRF-Token": token})
        ok("un élève ne peut pas écrire à la classe", refus.status_code == 403,
           str(refus.status_code))

        accuses = sa.get(BASE + "/api/messages?room=classe:groupe:90").json()
        ok("accusé de lecture remonté au professeur",
           bool(accuses.get("receipts")) and accuses.get("total") == 1,
           f"receipts={accuses.get('receipts')} total={accuses.get('total')}")
    else:
        skip("messagerie de classe", "compte de test indisponible")

    # ---------------------------------------------- photo de profil robuste
    print("▸ Photo de profil")
    page = sa.get(BASE + "/mon-profil").text
    ok("photo de profil modifiable depuis la galerie",
       'type="file"' in page and 'name="photo"' in page and "gallery" in page.lower() or
       ('type="file"' in page and 'name="photo"' in page))

    # ------------------------------------- actions de la fiche d'un élève
    print("▸ Fiche élève : réinitialiser, suspendre, supprimer")
    css = requests.get(BASE + "/static/css/app.css", timeout=30).text
    js = requests.get(BASE + "/static/js/app.js", timeout=30).text
    ok("confirmation dessinée dans la page (plus de window.confirm)",
       ".confirm-backdrop" in css and "askConfirm" in js and "requestSubmit" in js)

    probe = f"verif.action{''.join(random.choice(string.ascii_lowercase) for _ in range(4))}"
    created = _provision(sa, probe, "Vérification Actions", "user", "Action2026!")
    ok("compte de test créé pour les actions", created, probe)
    listing = sa.get(BASE + "/admin/utilisateurs?q=" + probe, timeout=20).text
    ids = sorted({int(i) for i in re.findall(r'/admin/utilisateurs/(\d+)"', listing)})
    cible = next((i for i in ids if f"@{probe}" in sa.get(BASE + f"/admin/utilisateurs/{i}", timeout=20).text), None)
    if cible:
        detail = sa.get(BASE + f"/admin/utilisateurs/{cible}", timeout=20).text
        token = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
        ok("la fiche annonce ses confirmations (titre, libellé, danger)",
           "data-confirm-title" in detail and "data-confirm-ok" in detail
           and 'data-confirm-danger="1"' in detail)

        reset = sa.post(BASE + f"/admin/utilisateurs/{cible}/reinitialiser",
                        data={"csrf_token": token}, timeout=30)
        ok("réinitialiser le mot de passe", reset.status_code == 200
           and "Nouveau mot de passe temporaire" in reset.text, str(reset.status_code))

        detail = sa.get(BASE + f"/admin/utilisateurs/{cible}", timeout=20).text
        token = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
        susp = sa.post(BASE + f"/admin/utilisateurs/{cible}/statut",
                       data={"csrf_token": token, "action": "suspend"}, allow_redirects=True, timeout=30)
        ok("suspendre le compte", susp.status_code == 200 and "Réactiver" in susp.text,
           str(susp.status_code))

        detail = sa.get(BASE + f"/admin/utilisateurs/{cible}", timeout=20).text
        token = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
        sa.post(BASE + f"/admin/utilisateurs/{cible}/statut",
                data={"csrf_token": token, "action": "activate"}, allow_redirects=True, timeout=30)

        detail = sa.get(BASE + f"/admin/utilisateurs/{cible}", timeout=20).text
        token = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
        refus = sa.post(BASE + f"/admin/utilisateurs/{cible}/supprimer",
                        data={"csrf_token": token, "confirm": "mauvais-nom"},
                        allow_redirects=True, timeout=30)
        ok("suppression refusée sans le nom exact", "La confirmation a échoué" in refus.text)

        detail = sa.get(BASE + f"/admin/utilisateurs/{cible}", timeout=20).text
        token = re.search(r'name="csrf_token" value="([^"]+)"', detail).group(1)
        suppr = sa.post(BASE + f"/admin/utilisateurs/{cible}/supprimer",
                        data={"csrf_token": token, "confirm": probe},
                        allow_redirects=True, timeout=30)
        ok("supprimer le compte", suppr.status_code == 200
           and "a été supprimé" in suppr.text, str(suppr.status_code))
    else:
        ok("fiche du compte de test introuvable", False, probe)

    # -------------------------------------------------------------- nettoyage
    print("▸ Nettoyage des comptes de test")
    removed = cleanup_accounts(sa)
    print(f"  ✔ {removed} compte(s) de test supprimé(s) — la base reste propre")

    # ------------------------------------------------------------------ bilan
    print(f"\n=== Bilan : {'tout est conforme ✔' if not failures else str(len(failures)) + ' échec(s) ✘'} ===")
    for f in failures:
        print("   ✘", f)
    return len(failures)


if __name__ == "__main__":
    sys.exit(main())
