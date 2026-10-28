# -*- coding: utf-8 -*-
"""Tests automatisés — TIC MASTER (#by_Myazirzk).

Lancement :  pytest -q
Les tests utilisent une base SQLite en mémoire et ne touchent jamais la base réelle.
"""
from __future__ import annotations

import re

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Attempt, Exercise, Module, Question, Option, User, utcnow,
    ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_USER, STATUS_ACTIVE,
)
from app.security.core import RateLimiter
from app.security.hashing import hash_password, verify_password
from app.utils import render_content


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def app():
    application = create_app("testing")
    application.config.update(
        SECRET_KEY="test-secret-key",
        PREFERRED_URL_SCHEME="http",
        SERVER_NAME=None,
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_user(app, username="apprenant", role=ROLE_USER, password="MotDePasse2026!"):
    with app.app_context():
        user = User(username=username, full_name=username.title(), role=role,
                    status=STATUS_ACTIVE, must_change_password=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def _csrf(client):
    """Récupère le jeton CSRF de la session (créé à la première requête)."""
    client.get("/auth/connexion")
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    if not token:
        page = client.get("/auth/connexion").get_data(as_text=True)
        match = re.search(r'name="csrf_token" value="([^"]+)"', page)
        token = match.group(1) if match else None
    return token


def _login(client, identifier, password):
    token = _csrf(client)
    return client.post("/auth/connexion", data={
        "csrf_token": token, "identifier": identifier, "password": password,
    }, follow_redirects=False)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
def test_app_boots_with_routes(app):
    rules = list(app.url_map.iter_rules())
    assert len(rules) > 80
    endpoints = {r.endpoint for r in rules}
    for expected in ("auth.login", "auth.logout", "public.index", "public.about",
                     "user.dashboard", "learning.catalog", "exam.index",
                     "social.messages", "social.battle_home", "admin.dashboard"):
        assert expected in endpoints


def test_no_public_registration(client, app):
    """Aucune route d'inscription publique ne doit exister."""
    for path in ("/inscription", "/register", "/auth/inscription", "/auth/register", "/creer-un-compte"):
        assert client.get(path).status_code == 404
    home = client.get("/").get_data(as_text=True).lower()
    assert "inscrire" not in home
    assert "créer un compte" not in home
    assert 'href="/auth/login"' not in home


def test_health_endpoint(client):
    response = client.get("/sante")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------
def test_login_success_and_redirect(client, app):
    _make_user(app, "apprenant")
    response = _login(client, "apprenant", "MotDePasse2026!")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/espace")
    assert client.get("/espace").status_code == 200


def test_login_failure_is_generic(client, app):
    _make_user(app, "apprenant")
    response = _login(client, "apprenant", "mauvais-mot-de-passe")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Identifiant ou mot de passe incorrect" in body
    # aucun indice sur l'existence du compte
    assert "inconnu" not in body.lower()


def test_login_unknown_account_same_message(client, app):
    _make_user(app, "apprenant")
    inconnu = _login(client, "fantome", "MotDePasse2026!").get_data(as_text=True)
    assert "Identifiant ou mot de passe incorrect" in inconnu


def test_csrf_required_for_post(client):
    response = client.post("/auth/connexion", data={"identifier": "x", "password": "y"})
    assert response.status_code == 400


def test_logout_revokes_session(client, app):
    _make_user(app, "apprenant")
    _login(client, "apprenant", "MotDePasse2026!")
    assert client.get("/espace").status_code == 200
    token = _csrf(client)
    client.post("/auth/deconnexion", data={"csrf_token": token})
    assert client.get("/espace").status_code == 302


def test_suspended_account_cannot_login(client, app):
    uid = _make_user(app, "suspendu")
    with app.app_context():
        user = db.session.get(User, uid)
        user.status = "suspended"
        db.session.commit()
    response = _login(client, "suspendu", "MotDePasse2026!")
    assert response.status_code == 200
    assert "Identifiant ou mot de passe incorrect" in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Permissions (contrôle serveur)
# ---------------------------------------------------------------------------
def test_user_cannot_reach_admin_area(client, app):
    _make_user(app, "apprenant")
    _login(client, "apprenant", "MotDePasse2026!")
    assert client.get("/admin/").status_code == 403
    assert client.get("/admin/utilisateurs").status_code == 403


def test_admin_cannot_reach_super_admin_pages(client, app):
    _make_user(app, "moderateur", role=ROLE_ADMIN)
    _login(client, "moderateur", "MotDePasse2026!")
    assert client.get("/admin/utilisateurs").status_code == 200
    for path in ("/admin/journal", "/admin/messages-utilisateurs",
                 "/admin/sessions", "/admin/sauvegardes"):
        assert client.get(path).status_code == 403


def test_admin_cannot_edit_super_admin(client, app):
    super_id = _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "moderateur", role=ROLE_ADMIN)
    _login(client, "moderateur", "MotDePasse2026!")
    token = _csrf(client)
    response = client.post(f"/admin/utilisateurs/{super_id}/modifier",
                           data={"csrf_token": token, "full_name": "Pirate",
                                 "username": "chef", "role": "admin", "status": "active"})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------
def test_password_is_hashed_with_argon2(app):
    uid = _make_user(app, "hash")
    with app.app_context():
        user = db.session.get(User, uid)
        assert user.password_hash.startswith("$argon2")
        assert "MotDePasse2026!" not in user.password_hash
        assert verify_password(user.password_hash, "MotDePasse2026!")[0]
        assert not verify_password(user.password_hash, "autre")[0]


def test_weak_password_rejected(app):
    from app.security.core import password_ok
    assert not password_ok("court")
    assert not password_ok("sansmajuscule2!")
    assert not password_ok("SANSMINUSCULE2!")
    assert not password_ok("SansChiffre!")
    assert password_ok("MotDePasse2026!")


# ---------------------------------------------------------------------------
# Anti-force brute
# ---------------------------------------------------------------------------
def test_rate_limiter_blocks_after_threshold():
    limiter = RateLimiter()
    assert limiter.hit("cle", 3, 60) is False
    assert limiter.hit("cle", 3, 60) is False
    assert limiter.hit("cle", 3, 60) is False
    assert limiter.hit("cle", 3, 60) is True


# ---------------------------------------------------------------------------
# XSS
# ---------------------------------------------------------------------------
def test_render_content_escapes_scripts():
    html = str(render_content("<script>alert('xss')</script>"))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_content_supports_markdown():
    html = str(render_content("# Titre\n\n**gras** et `code`\n\n- un\n- deux"))
    assert "<h2>Titre</h2>" in html
    assert "<strong>gras</strong>" in html
    assert "<code>code</code>" in html
    assert "<li>un</li>" in html


# ---------------------------------------------------------------------------
# Anti-fraude d'examen
# ---------------------------------------------------------------------------
def _create_exam(app, name="Examen T1"):
    with app.app_context():
        module = Module(title="Sécurité", slug="securite", summary="", status="published")
        db.session.add(module)
        db.session.flush()
        exam = Exercise(module_id=module.id, title=name, kind="exam", term="T1",
                        duration_minutes=30, max_tab_violations=1, published=True)
        db.session.add(exam)
        db.session.flush()
        question = Question(exercise_id=exam.id, text="Question ?", points=1)
        db.session.add(question)
        db.session.flush()
        db.session.add(Option(question_id=question.id, text="Bonne", is_correct=True))
        db.session.add(Option(question_id=question.id, text="Mauvaise", is_correct=False))
        db.session.commit()
        return exam.id


def test_exam_violation_eliminates_only_the_author(client, app):
    exam_id = _create_exam(app)
    _make_user(app, "tricheur")
    _make_user(app, "honnete")
    _login(client, "tricheur", "MotDePasse2026!")

    token = _csrf(client)
    client.post(f"/examens/{exam_id}/commencer", data={"csrf_token": token})
    with app.app_context():
        attempt = Attempt.query.order_by(Attempt.id.desc()).first()
        assert attempt is not None and attempt.status == "in_progress"
        attempt_id = attempt.id

    token = _csrf(client)
    response = client.post(f"/api/exam/{attempt_id}/violation",
                           json={"reason": "Sortie d'onglet"},
                           headers={"X-CSRF-Token": token})
    assert response.status_code in (200, 201)

    with app.app_context():
        attempt = db.session.get(Attempt, attempt_id)
        assert attempt.status == "eliminated"
        assert attempt.tab_violations >= 1
        # les autres comptes ne sont pas affectés
        assert Attempt.query.count() == 1


# ---------------------------------------------------------------------------
# Isolation des données
# ---------------------------------------------------------------------------
def test_results_are_isolated_per_user(client, app):
    _make_user(app, "alice")
    _make_user(app, "bob")
    _login(client, "alice", "MotDePasse2026!")
    assert client.get("/resultats").status_code == 200
    with app.app_context():
        assert Attempt.query.count() == 0


# ---------------------------------------------------------------------------
# Mise à jour du site (maintenance)
# ---------------------------------------------------------------------------
def test_maintenance_blocks_students_but_never_admins(client, app):
    """Pendant la maintenance : élèves bloqués, super administrateur jamais bloqué."""
    _make_user(app, "apprenant")
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)

    with app.app_context():
        from app import maintenance
        maintenance.enable("Installation des nouveaux modules.", "dans 20 minutes")

    response = client.get("/cours")
    assert response.status_code == 503
    body = response.get_data(as_text=True).lower()
    assert "mise à jour" in body
    assert response.headers["Retry-After"] == "300"

    # les fichiers techniques et la santé restent disponibles
    assert client.get("/sante").status_code == 200
    assert client.get("/static/css/app.css").status_code == 200
    assert client.get("/auth/connexion").status_code == 200

    # le super administrateur garde l'accès complet
    _login(client, "chef", "MotDePasse2026!")
    assert client.get("/admin/notes").status_code == 200
    assert client.get("/cours").status_code == 200

    with app.app_context():
        from app import maintenance
        maintenance.disable()
    assert client.get("/cours").status_code == 200


# ---------------------------------------------------------------------------
# Scolarité : notes et statistiques (super administrateur seulement)
# ---------------------------------------------------------------------------
def test_grades_area_is_reserved_to_super_admin(app):
    _make_user(app, "apprenant")
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "modo", role=ROLE_ADMIN)

    student = app.test_client()
    _login(student, "apprenant", "MotDePasse2026!")
    assert student.get("/admin/notes").status_code == 403
    assert student.get("/admin/statistiques").status_code == 403

    admin_client = app.test_client()
    _login(admin_client, "modo", "MotDePasse2026!")
    assert admin_client.get("/admin/notes").status_code == 403

    chief = app.test_client()
    _login(chief, "chef", "MotDePasse2026!")
    assert chief.get("/admin/notes").status_code == 200
    assert chief.get("/admin/statistiques").status_code == 200
    assert chief.get("/admin/notes/export.csv").status_code == 200


def test_super_admin_is_a_teacher_without_exams(client, app):
    """Le super administrateur est professeur : ni examen ni statistiques personnelles."""
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _login(client, "chef", "MotDePasse2026!")

    exams = client.get("/examens", follow_redirects=False)
    assert exams.status_code == 302
    assert "/admin/notes" in exams.headers["Location"]

    results = client.get("/resultats", follow_redirects=False)
    assert results.status_code == 302
    assert "/admin/statistiques" in results.headers["Location"]

    # il ne peut pas démarrer un examen (contrôle serveur, pas seulement le menu)
    with app.app_context():
        module = Module(title="Réseaux", slug="reseaux", status="published")
        db.session.add(module)
        db.session.commit()
        exam = Exercise(title="Examen T1", kind="exam", term="T1", module_id=module.id,
                        published=True, duration_minutes=20, pass_score=50)
        db.session.add(exam)
        db.session.commit()
        exam_id = exam.id
    token = _csrf(client)
    response = client.post(f"/examens/{exam_id}/commencer", data={"csrf_token": token},
                           follow_redirects=False)
    assert response.status_code == 403
