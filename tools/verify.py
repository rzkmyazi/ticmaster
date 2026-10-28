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


def rand_suffix(n: int = 5) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def main() -> int:
    print(f"\n=== TIC MASTER · vérification de {BASE} ===\n")

    # ------------------------------------------------------------------ santé
    print("▸ Santé")
    r = requests.get(BASE + "/sante", timeout=20)
    ok("/sante", r.status_code == 200 and r.json().get("status") == "ok", r.text[:60])

    print("▸ Pages publiques et absence d'inscription")
    for path, expected in (("/", 200), ("/a-propos", 200), ("/auth/connexion", 200),
                           ("/auth/mot-de-passe-oublie", 200),
                           ("/inscription", 404), ("/register", 404),
                           ("/auth/inscription", 404)):
        code = requests.get(BASE + path, timeout=20).status_code
        ok(f"{path} → {code}", code == expected, f"attendu {expected}")
    home = requests.get(BASE + "/", timeout=20).text.lower()
    ok("aucune inscription publique sur l'accueil",
       "s'inscrire" not in home and "créer un compte" not in home)

    # ------------------------------------------------------------- connexions
    print("▸ Connexion des trois rôles")
    sa = login(*SUPER)
    ensure_accounts(sa)
    u = login(*USER)
    a = login(*ADMIN)

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
        r = p.post(BASE + "/api/battle/start", json={"code": code},
                   headers={"X-CSRF-Token": token})
        ok("démarrage de la battle", r.status_code == 200, r.text[:80])
        state = p.get(BASE + f"/api/battle/state?code={code}").json()
        room_status = (state.get("room") or {}).get("status")
        ok("question en cours",
           state.get("ok") is True and room_status == "running" and state.get("seconds_left", 0) > 0,
           f"statut={room_status}, index={state.get('index')}, restant={state.get('seconds_left')}s")
        r = p.post(BASE + "/api/battle/rename", json={"code": code, "name": "Autre nom"},
                   headers={"X-CSRF-Token": token})
        ok("renommage d'une battle solo refusé", r.status_code == 400, str(r.status_code))

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
