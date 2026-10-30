# -*- coding: utf-8 -*-
"""Notifications V2.2 — texte propre, déduplication, propriété, suppression.

Lancement :  pytest -q tests/test_notifications.py
Aucun accès à la base réelle : SQLite en mémoire, comptes de test.
"""
from __future__ import annotations

import re

import pytest

from app import create_app
from app.extensions import db
from app.models import Notification, ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_USER, STATUS_ACTIVE, User
from app.notifications import CONTENU_RETIRE, notify, notify_many, sanitize_rows
from app.text_safety import clean_text, clean_title

XSS = "<script>alert('xss')</script>"


# ---------------------------------------------------------------------------
# Fixtures (noms propres à ce fichier : aucune interférence avec test_app.py)
# ---------------------------------------------------------------------------
@pytest.fixture()
def nf_app():
    application = create_app("testing")
    application.config.update(SECRET_KEY="test-secret-key", PREFERRED_URL_SCHEME="http",
                              SERVER_NAME=None)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def nf_client(nf_app):
    return nf_app.test_client()


@pytest.fixture(autouse=True)
def _limiteur_vide():
    from app.security.core import limiter
    limiter._events.clear()
    yield
    limiter._events.clear()


def _user(nf_app, username="eleve", role=ROLE_USER, password="MotDePasse2026!"):
    with nf_app.app_context():
        user = User(username=username, full_name=username.title(), role=role,
                    status=STATUS_ACTIVE, must_change_password=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def _jeton(client):
    client.get("/auth/connexion")
    with client.session_transaction() as sess:
        return sess.get("csrf_token")


def _connexion(client, identifiant, mot_de_passe="MotDePasse2026!"):
    jeton = _jeton(client)
    return client.post("/auth/connexion",
                       data={"csrf_token": jeton, "identifier": identifiant,
                             "password": mot_de_passe},
                       follow_redirects=False)


# ---------------------------------------------------------------------------
# 1. Nettoyage du texte (le cœur du défaut signalé)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("brut", [
    XSS,
    "&lt;script&gt;alert('xss')&lt;/script&gt;",
    "&amp;lt;script&amp;gt;alert('xss')&amp;lt;/script&amp;gt;",
    "<img src=x onerror=alert(1)>",
    "<style>body{display:none}</style>",
    "<iframe src='javascript:alert(1)'></iframe>",
])
def test_balisage_jamais_affiche(brut):
    """Un contenu qui n'est que du code ne produit aucun texte affichable."""
    assert clean_text(brut) == ""


def test_texte_utile_conserve_balises_retirees():
    assert clean_text("Annonce <b>importante</b> pour la classe") == "Annonce importante pour la classe"
    assert "<" not in clean_text("<p>Bonjour</p> à tous")
    assert "script" not in clean_text("<scr<script>ipt>alert(1)</script>").lower()


def test_titre_court_et_sans_balise():
    titre = clean_title("<b>" + "A" * 300 + "</b>", limit=40)
    assert "<" not in titre and ">" not in titre
    assert len(titre) <= 41          # 40 caractères + le « … » de coupe


# ---------------------------------------------------------------------------
# 2. Notification stockée déjà propre
# ---------------------------------------------------------------------------
def test_notification_stockee_propre(nf_app):
    with nf_app.app_context():
        eleve = User(username="eleve", full_name="Élève", role=ROLE_USER,
                     status=STATUS_ACTIVE, must_change_password=False)
        eleve.set_password("MotDePasse2026!")
        prof = User(username="prof", full_name="Prof", role=ROLE_ADMIN,
                    status=STATUS_ACTIVE, must_change_password=False)
        prof.set_password("MotDePasse2026!")
        db.session.add_all([eleve, prof])
        db.session.commit()

        notify(eleve.id, "annonce", f"Nouvelle annonce : Test XSS auto", XSS,
               "/notifications", actor=prof, icon="megaphone")
        row = Notification.query.filter_by(user_id=eleve.id).one()
        assert XSS not in row.title and XSS not in row.body
        assert "<" not in row.title and "<" not in row.body
        assert row.body == CONTENU_RETIRE          # il n'y avait que du code
        assert row.kind == "annonce" and row.icon == "megaphone"


def test_api_notifications_texte_propre(nf_app, nf_client):
    _user(nf_app, "eleve")
    _user(nf_app, "prof", role=ROLE_ADMIN)
    with nf_app.app_context():
        eleve = User.query.filter_by(username="eleve").one()
        prof = User.query.filter_by(username="prof").one()
        notify(eleve.id, "annonce", "Nouvelle annonce : Test XSS auto", XSS,
               "/notifications", actor=prof, icon="megaphone")
    assert _connexion(nf_client, "eleve").status_code == 302

    data = nf_client.get("/api/notifications").get_json()
    assert data["ok"] is True and data["count"] == 1
    item = data["items"][0]
    for cle in ("title", "body", "label", "at"):
        assert "<" not in item[cle] and ">" not in item[cle]
    assert "script" not in item["body"].lower()
    assert item["at"]                                  # date + heure présentes


def test_page_historique_sans_balise(nf_app, nf_client):
    _user(nf_app, "eleve")
    with nf_app.app_context():
        eleve = User.query.filter_by(username="eleve").one()
        notify(eleve.id, "annonce", "Nouvelle annonce : Test XSS auto", XSS, "/notifications")
        # ligne ancienne, écrite avant la correction
        db.session.add(Notification(user_id=eleve.id, kind="annonce",
                                    title="Ancienne <b>annonce</b>", body=XSS,
                                    url="/notifications", icon="bell"))
        db.session.commit()

    _connexion(nf_client, "eleve")
    page = nf_client.get("/notifications").get_data(as_text=True)
    assert "<script>alert('xss')</script>" not in page
    assert "&lt;script&gt;" not in page
    assert "Ancienne annonce" in page


def test_sanitize_rows_repare_l_existant(nf_app):
    with nf_app.app_context():
        eleve = User(username="eleve", role=ROLE_USER, status=STATUS_ACTIVE,
                     must_change_password=False)
        eleve.set_password("MotDePasse2026!")
        db.session.add(eleve)
        db.session.commit()
        db.session.add_all([
            Notification(user_id=eleve.id, kind="annonce",
                         title="Nouvelle annonce : Test XSS auto", body=XSS),
            Notification(user_id=eleve.id, kind="message",
                         title="Message <b>important</b>", body="Texte &amp; suite"),
        ])
        db.session.commit()

        assert sanitize_rows() == 2
        for row in Notification.query.all():
            assert "<" not in row.title and ">" not in row.title
            assert "<" not in row.body
            assert XSS not in row.body


# ---------------------------------------------------------------------------
# 3. Pas de doublon, pas d'annonce répétée
# ---------------------------------------------------------------------------
def test_meme_annonce_une_seule_notification(nf_app):
    with nf_app.app_context():
        eleve = User(username="eleve", role=ROLE_USER, status=STATUS_ACTIVE,
                     must_change_password=False)
        eleve.set_password("MotDePasse2026!")
        db.session.add(eleve)
        db.session.commit()

        for _ in range(3):
            notify(eleve.id, "annonce", "Nouvelle annonce : Règlement", "Texte",
                   "/notifications", dedupe_key="annonce:42")
        assert Notification.query.filter_by(user_id=eleve.id).count() == 1


def test_notify_many_ne_double_pas_les_destinataires(nf_app):
    with nf_app.app_context():
        eleve = User(username="eleve", role=ROLE_USER, status=STATUS_ACTIVE,
                     must_change_password=False)
        eleve.set_password("MotDePasse2026!")
        db.session.add(eleve)
        db.session.commit()

        envoyees = notify_many([eleve.id, eleve.id, eleve.id], "system", "Entretien",
                               "La plateforme sera en maintenance.", "/notifications",
                               dedupe_key="systeme:entretien:2026-11")
        assert envoyees == 1
        assert Notification.query.count() == 1


def test_doublon_automatique_par_titre(nf_app):
    with nf_app.app_context():
        eleve = User(username="eleve", role=ROLE_USER, status=STATUS_ACTIVE,
                     must_change_password=False)
        eleve.set_password("MotDePasse2026!")
        db.session.add(eleve)
        db.session.commit()

        notify(eleve.id, "system", "Sauvegarde terminée", "OK")
        notify(eleve.id, "system", "Sauvegarde terminée", "OK")
        assert Notification.query.count() == 1

        # un événement qui peut légitimement se répéter passe avec dedupe_hours=0
        notify(eleve.id, "compte", "Connexion depuis un nouvel appareil", "Android",
               dedupe_hours=0)
        notify(eleve.id, "compte", "Connexion depuis un nouvel appareil", "Android",
               dedupe_hours=0)
        assert Notification.query.filter_by(kind="compte").count() == 2


def test_pas_de_notification_a_soi_meme(nf_app):
    with nf_app.app_context():
        prof = User(username="prof", role=ROLE_ADMIN, status=STATUS_ACTIVE,
                    must_change_password=False)
        prof.set_password("MotDePasse2026!")
        db.session.add(prof)
        db.session.commit()
        assert notify(prof.id, "annonce", "Test", "Test", actor=prof) is None
        assert Notification.query.count() == 0


# ---------------------------------------------------------------------------
# 4. Propriété et permissions
# ---------------------------------------------------------------------------
def _deux_eleves(nf_app):
    _user(nf_app, "eleve")
    _user(nf_app, "intrus")
    with nf_app.app_context():
        eleve = User.query.filter_by(username="eleve").one()
        row = notify(eleve.id, "message", "Nouveau message de Prof", "Bonjour", "/messages")
        return eleve.id, row.id


def test_lire_la_notification_d_un_autre_refuse(nf_app, nf_client):
    _, notif_id = _deux_eleves(nf_app)
    _connexion(nf_client, "intrus")
    jeton = _jeton(nf_client)
    r = nf_client.post(f"/api/notifications/{notif_id}/lue",
                       headers={"X-CSRF-Token": jeton})
    assert r.status_code == 404
    with nf_app.app_context():
        assert db.session.get(Notification, notif_id).read_at is None


def test_supprimer_la_notification_d_un_autre_refuse(nf_app, nf_client):
    _, notif_id = _deux_eleves(nf_app)
    _connexion(nf_client, "intrus")
    jeton = _jeton(nf_client)
    r = nf_client.delete(f"/api/notifications/{notif_id}", headers={"X-CSRF-Token": jeton})
    assert r.status_code == 404
    with nf_app.app_context():
        assert db.session.get(Notification, notif_id) is not None


def test_supprimer_sa_notification(nf_app, nf_client):
    _, notif_id = _deux_eleves(nf_app)
    _connexion(nf_client, "eleve")
    jeton = _jeton(nf_client)

    avant = nf_client.get("/api/notifications").get_json()
    assert avant["count"] == 1

    r = nf_client.delete(f"/api/notifications/{notif_id}", headers={"X-CSRF-Token": jeton})
    data = r.get_json()
    assert r.status_code == 200 and data["ok"] is True
    assert data["count"] == 0

    with nf_app.app_context():
        assert db.session.get(Notification, notif_id) is None
    apres = nf_client.get("/api/notifications").get_json()
    assert apres["count"] == 0 and apres["items"] == []


def test_suppression_formulaire_sans_javascript(nf_app, nf_client):
    _, notif_id = _deux_eleves(nf_app)
    _connexion(nf_client, "eleve")
    jeton = _jeton(nf_client)
    r = nf_client.post(f"/notifications/{notif_id}/supprimer",
                       data={"csrf_token": jeton}, follow_redirects=False)
    assert r.status_code == 302
    with nf_app.app_context():
        assert db.session.get(Notification, notif_id) is None


def test_csrf_obligatoire_pour_supprimer(nf_app, nf_client):
    _, notif_id = _deux_eleves(nf_app)
    _connexion(nf_client, "eleve")
    r = nf_client.delete(f"/api/notifications/{notif_id}")
    assert r.status_code == 400
    with nf_app.app_context():
        assert db.session.get(Notification, notif_id) is not None


def test_anonyme_redirige_vers_la_connexion(nf_client):
    r = nf_client.get("/api/notifications")
    assert r.status_code in (302, 401, 403)


def test_compteur_synchronise(nf_app, nf_client):
    _deux_eleves(nf_app)
    _connexion(nf_client, "eleve")
    jeton = _jeton(nf_client)
    assert nf_client.get("/api/notifications").get_json()["count"] == 1
    assert nf_client.post("/api/notifications/tout-lire",
                          headers={"X-CSRF-Token": jeton}).get_json()["count"] == 0
    assert nf_client.get("/api/notifications").get_json()["count"] == 0
    with nf_app.app_context():
        assert Notification.query.filter(Notification.read_at.is_(None)).count() == 0


# ---------------------------------------------------------------------------
# 5. Fusion des doublons (action du super administrateur) et statistiques
# ---------------------------------------------------------------------------
def _super_admin(nf_app):
    with nf_app.app_context():
        chef = User(username="chef", full_name="Chef", role=ROLE_SUPER_ADMIN,
                    status=STATUS_ACTIVE, must_change_password=False)
        chef.set_password("MotDePasse2026!")
        db.session.add(chef)
        db.session.commit()
        return chef.id


def test_stats_detecte_les_doublons(nf_app):
    from app.notifications import stats

    with nf_app.app_context():
        eleve = User(username="eleve", role=ROLE_USER, status=STATUS_ACTIVE,
                     must_change_password=False)
        eleve.set_password("MotDePasse2026!")
        db.session.add(eleve)
        db.session.commit()
        for _ in range(3):
            db.session.add(Notification(user_id=eleve.id, kind="annonce",
                                        title="Nouvelle annonce : Règlement",
                                        body="Texte identique"))
        db.session.commit()
        info = stats()
        assert info["total"] == 3 and info["groupes"] == 1 and info["en_trop"] == 2


def test_fusion_reservee_au_super_admin(nf_app, nf_client):
    _super_admin(nf_app)
    _user(nf_app, "prof", role=ROLE_ADMIN)
    _connexion(nf_client, "prof")
    jeton = _jeton(nf_client)
    r = nf_client.post("/admin/notifications/dedoublier", data={"csrf_token": jeton, "kind": "annonce"})
    assert r.status_code in (302, 403)
    assert r.headers.get("Location", "").find("/admin/notifications/dedoublier") == -1


def test_fusion_conserve_une_copie(nf_app, nf_client):
    _super_admin(nf_app)
    _user(nf_app, "eleve")
    with nf_app.app_context():
        eleve = User.query.filter_by(username="eleve").one()
        for _ in range(4):
            db.session.add(Notification(user_id=eleve.id, kind="annonce",
                                        title="Nouvelle annonce : Test XSS auto",
                                        body="Contenu retiré"))
        db.session.commit()

    _connexion(nf_client, "chef")
    jeton = _jeton(nf_client)
    r = nf_client.post("/admin/notifications/dedoublier",
                       data={"csrf_token": jeton, "kind": "annonce"},
                       follow_redirects=False)
    assert r.status_code == 302
    with nf_app.app_context():
        assert Notification.query.filter_by(kind="annonce").count() == 1


def test_page_parametres_affiche_l_etat(nf_app, nf_client):
    _super_admin(nf_app)
    _connexion(nf_client, "chef")
    page = nf_client.get("/admin/parametres?onglet=maintenance").get_data(as_text=True)
    assert "Notifications" in page and "notification(s) en base" in page
