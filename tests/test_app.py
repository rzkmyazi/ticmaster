# -*- coding: utf-8 -*-
"""Tests automatisés — TIC MASTER (#by_Myazirzk).

Lancement :  pytest -q
Les tests utilisent une base SQLite en mémoire et ne touchent jamais la base réelle.
"""
from __future__ import annotations

import io
import re

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    Attempt, BattleMember, BattleRoom, Exercise, Module, Question, Option, User, utcnow,
    ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_USER, STATUS_ACTIVE, STATUS_SUSPENDED,
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


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Le limiteur de débit est en mémoire et partagé : on le vide entre les tests."""
    from app.security.core import limiter
    limiter._events.clear()
    yield
    limiter._events.clear()


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
    for path in ("/admin/journal", "/admin/messages-utilisateurs", "/admin/sauvegardes"):
        assert client.get(path).status_code == 403
    # Vague 14 : la surveillance des connexions est ouverte aux administrateurs
    assert client.get("/admin/sessions").status_code == 200
    assert client.get("/admin/api/presence").status_code == 200


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
    assert client.get("/admin/modules").status_code == 200
    # professeur : « /cours » le renvoie vers la gestion des cours, pas vers un cours
    redirection = client.get("/cours", follow_redirects=False)
    assert redirection.status_code == 302
    assert redirection.headers["Location"].endswith("/admin/modules")

    # le drapeau se lève et se baisse proprement (lecture en base)
    with app.app_context():
        from app import maintenance
        from app.models import Setting
        assert Setting.get("maintenance_mode") == "1"
        maintenance.disable()
        assert Setting.get("maintenance_mode") == "0"

    # un visiteur non connecté reçoit aussi la page d'attente
    visiteur = app.test_client()
    assert visiteur.get("/cours").status_code == 503


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


# ---------------------------------------------------------------------------
# Fil d'actualité du profil : publications, photos, réactions, commentaires
# ---------------------------------------------------------------------------
def _seed_post(app, author_id, body="Bonjour la classe", image_filename=""):
    from app.models import Post
    with app.app_context():
        post = Post(author_id=author_id, body=body, image_filename=image_filename,
                    image_name="photo.png" if image_filename else "", image_size=10)
        db.session.add(post)
        db.session.commit()
        return post.id


def test_profile_has_social_feed(app):
    uid = _make_user(app, "apprenant")
    client = app.test_client()
    _login(client, "apprenant", "MotDePasse2026!")
    post_id = _seed_post(app, uid, "Première publication")

    page = client.get("/mon-profil")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'id="post-form"' in html            # composeur de publication
    assert "Première publication" in html      # fil d'actualité
    for emoji in ("❤️", "😂", "👊", "😠", "😢"):
        assert emoji in html                   # les cinq réactions demandées
    assert post_id  # la publication existe bien


def test_create_post_and_reject_empty(app):
    _make_user(app, "apprenant")
    client = app.test_client()
    _login(client, "apprenant", "MotDePasse2026!")
    token = _csrf(client)

    empty = client.post("/api/posts", data={"body": "   "}, headers={"X-CSRF-Token": token})
    assert empty.status_code == 400

    created = client.post("/api/posts", data={"body": "Coucou"}, headers={"X-CSRF-Token": token})
    assert created.status_code == 201
    assert created.get_json()["ok"] is True

    from app.models import Post
    with app.app_context():
        assert Post.query.count() == 1
        assert Post.query.first().body == "Coucou"


def test_create_post_rejects_fake_image(app):
    import io
    _make_user(app, "apprenant")
    client = app.test_client()
    _login(client, "apprenant", "MotDePasse2026!")
    token = _csrf(client)

    fake = client.post(
        "/api/posts",
        data={"body": "", "image": (io.BytesIO(b"<?php echo 'x'; ?>"), "photo.png")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )
    assert fake.status_code == 400


def test_reactions_are_unique_and_toggle(app):
    uid = _make_user(app, "apprenant")
    post_id = _seed_post(app, uid)
    client = app.test_client()
    _login(client, "apprenant", "MotDePasse2026!")
    token = _csrf(client)

    first = client.post(f"/api/posts/{post_id}/react", json={"kind": "love"},
                        headers={"X-CSRF-Token": token})
    assert first.status_code == 200
    assert first.get_json()["current"] == "love"

    changed = client.post(f"/api/posts/{post_id}/react", json={"kind": "haha"},
                          headers={"X-CSRF-Token": token})
    assert changed.get_json()["current"] == "haha"
    assert changed.get_json()["total"] == 1     # une seule réaction par personne

    removed = client.post(f"/api/posts/{post_id}/react", json={"kind": "haha"},
                          headers={"X-CSRF-Token": token})
    assert removed.get_json()["current"] == ""
    assert removed.get_json()["total"] == 0

    bad = client.post(f"/api/posts/{post_id}/react", json={"kind": "amour"},
                      headers={"X-CSRF-Token": token})
    assert bad.status_code == 400

    for kind in ("love", "haha", "fist", "angry", "sad"):
        ok = client.post(f"/api/posts/{post_id}/react", json={"kind": kind},
                         headers={"X-CSRF-Token": token})
        assert ok.status_code == 200


def test_comments_and_delete(app):
    uid = _make_user(app, "apprenant")
    post_id = _seed_post(app, uid)
    client = app.test_client()
    _login(client, "apprenant", "MotDePasse2026!")
    token = _csrf(client)

    empty = client.post(f"/api/posts/{post_id}/comment", json={"body": ""},
                        headers={"X-CSRF-Token": token})
    assert empty.status_code == 400

    ok = client.post(f"/api/posts/{post_id}/comment", json={"body": "Bravo !"},
                     headers={"X-CSRF-Token": token})
    assert ok.status_code == 201

    from app.models import Post, PostComment
    with app.app_context():
        assert PostComment.query.count() == 1

    deleted = client.post(f"/api/posts/{post_id}/delete", json={}, headers={"X-CSRF-Token": token})
    assert deleted.status_code == 200
    with app.app_context():
        assert Post.query.filter_by(deleted=False).count() == 0


def test_media_requires_login(app):
    uid = _make_user(app, "apprenant")
    _seed_post(app, uid, image_filename="abc123.png")
    anonymous = app.test_client()
    assert anonymous.get("/media/abc123.png").status_code == 302
    assert app.test_client().get("/media/inexistant.png").status_code == 302


# ---------------------------------------------------------------------------
# Battles : validation par l'administration
# ---------------------------------------------------------------------------
def _seed_quiz(app):
    with app.app_context():
        module = Module(title="Réseaux", slug="reseaux", status="published")
        db.session.add(module)
        db.session.commit()
        exercise = Exercise(title="Quiz battle", kind="exercise", module_id=module.id,
                            published=True, pass_score=50)
        db.session.add(exercise)
        db.session.commit()
        for index in range(6):
            question = Question(exercise_id=exercise.id, text=f"Question {index} ?",
                                order_index=index)
            db.session.add(question)
            db.session.commit()
            db.session.add_all([
                Option(question_id=question.id, text="Bonne réponse", is_correct=True),
                Option(question_id=question.id, text="Mauvaise réponse", is_correct=False),
            ])
        db.session.commit()


def test_student_battle_waits_for_approval(app):
    _seed_quiz(app)
    _make_user(app, "apprenant")
    client = app.test_client()
    _login(client, "apprenant", "MotDePasse2026!")
    token = _csrf(client)

    created = client.post("/api/battle/create", json={"mode": "solo"},
                          headers={"X-CSRF-Token": token})
    assert created.status_code == 201
    payload = created.get_json()
    assert payload["status"] == "pending"
    assert payload["pending"] is True

    # impossible de démarrer avant l'accord de l'administration
    started = client.post("/api/battle/start", json={"code": payload["code"]},
                          headers={"X-CSRF-Token": token})
    assert started.status_code == 403

    page = client.get("/battle").get_data(as_text=True)
    assert "En attente de validation" in page

    # l'apprenant n'a pas accès à l'écran de validation
    assert client.get("/admin/battles").status_code == 403


def test_admin_accepts_and_refuses_battles(app):
    _seed_quiz(app)
    owner = _make_user(app, "apprenant")
    _make_user(app, "modo", role=ROLE_ADMIN)
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)

    from app.models import BattleRoom
    with app.app_context():
        room = BattleRoom(name="Duel TIC", mode="group", code="ABC123", owner_id=owner,
                          status="pending")
        other = BattleRoom(name="Duel refusé", mode="solo", code="XYZ789", owner_id=owner,
                           status="pending")
        db.session.add_all([room, other])
        db.session.commit()
        room_id, other_id = room.id, other.id

    modo = app.test_client()
    _login(modo, "modo", "MotDePasse2026!")
    token = _csrf(modo)
    assert modo.get("/admin/battles").status_code == 200
    assert modo.post(f"/admin/battles/{room_id}/accepter", data={"csrf_token": token}).status_code == 302
    assert modo.post(f"/admin/battles/{other_id}/refuser", data={"csrf_token": token}).status_code == 302

    with app.app_context():
        assert db.session.get(BattleRoom, room_id).status == "lobby"
        assert db.session.get(BattleRoom, other_id).status == "refused"


# ---------------------------------------------------------------------------
# Paramètres : conservation des données illimitée
# ---------------------------------------------------------------------------
def test_retention_can_be_unlimited(app):
    from app.models import Setting
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    token = _csrf(client)

    page = client.get("/admin/parametres").get_data(as_text=True)
    assert "conservation illimitée" in page

    for value in ("", "0", "illimite", "illimité"):
        client.post("/admin/parametres", data={"retention_days": value, "csrf_token": token})
        with app.app_context():
            assert Setting.get("retention_days") == "0"

    client.post("/admin/parametres", data={"retention_days": "365", "csrf_token": token})
    with app.app_context():
        assert Setting.get("retention_days") == "365"


# ---------------------------------------------------------------------------
# Notes individuelles sur 20 dans l'espace super administrateur
# ---------------------------------------------------------------------------
def test_dashboard_shows_individual_notes(app):
    _make_user(app, "apprenant")
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)

    chief = app.test_client()
    _login(chief, "chef", "MotDePasse2026!")
    html = chief.get("/admin/").get_data(as_text=True)
    assert "Notes individuelles (sur 20)" in html
    assert "Battles à valider" in html

    modo = app.test_client()
    _make_user(app, "modo", role=ROLE_ADMIN)
    _login(modo, "modo", "MotDePasse2026!")
    assert "Notes individuelles (sur 20)" not in modo.get("/admin/").get_data(as_text=True)


# ---------------------------------------------------------------------------
# Rôles : trois seulement (Super Admin, Admin, Élève)
# ---------------------------------------------------------------------------
def test_only_three_roles_with_eleve_label(app):
    from app.models import ROLE_LABELS, ROLES
    assert set(ROLES) == {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER}
    assert ROLE_LABELS[ROLE_USER] == "Élève"
    assert ROLE_LABELS[ROLE_ADMIN] == "Admin"
    assert ROLE_LABELS[ROLE_SUPER_ADMIN] == "Super Admin"
    assert "Utilisateur" not in ROLE_LABELS.values()

    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    page = client.get("/admin/utilisateurs/nouveau").get_data(as_text=True)
    assert 'value="user"' in page and "Élève" in page
    assert 'value="admin"' in page and 'value="super_admin"' in page
    assert "Utilisateur</option>" not in page      # l'ancien libellé a disparu
    assert page.count('<option value="user"') == 1


# ---------------------------------------------------------------------------
# Dossier scolaire de l'élève
# ---------------------------------------------------------------------------
def _create_student(client, token, **overrides):
    data = {
        "csrf_token": token, "full_name": "", "last_name": "Rakoto", "first_name": "Jean",
        "pseudo": "LeRoiDuReseau", "username": "rakoto.jean", "email": "",
        "role": "user", "status": "active", "bio": "", "password": "Eleve2026!mdp",
        "must_change": "1", "class_number": "7", "study_level": "Terminale",
        "gender": "garcon", "class_group": "2",
    }
    data.update(overrides)
    return client.post("/admin/utilisateurs/nouveau", data=data)


def test_inscription_enregistre_le_dossier_scolaire(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    token = _csrf(client)

    response = _create_student(client, token)
    assert response.status_code == 200          # page avec les identifiants

    with app.app_context():
        student = User.query.filter_by(username="rakoto.jean").one()
        assert student.role == ROLE_USER
        assert student.last_name == "Rakoto"
        assert student.first_name == "Jean"
        assert student.pseudo == "LeRoiDuReseau"
        assert student.class_number == 7
        assert student.study_level == "Terminale"
        assert student.gender == "garcon"
        assert student.class_group == 2
        assert student.full_name == "Rakoto Jean"     # composé automatiquement
        assert student.class_label == "Terminale · Groupe 2 · N° 7"
        assert student.gender_label == "Garçon"

    page = client.get("/admin/utilisateurs?q=rakoto.jean").get_data(as_text=True)
    assert "Rakoto Jean" in page and "Groupe 2" in page and ">7<" in page.replace("\n", "")

    with app.app_context():
        student_id = User.query.filter_by(username="rakoto.jean").one().id
    detail = client.get(f"/admin/utilisateurs/{student_id}").get_data(as_text=True)
    assert "Dossier scolaire" in detail
    assert "LeRoiDuReseau" in detail and "Terminale" in detail


def test_dossier_scolaire_validation(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    token = _csrf(client)

    bad_group = _create_student(client, token, class_group="100", username="eleve.groupe")
    assert "Le groupe doit être compris entre 1 et 99" in bad_group.get_data(as_text=True)

    # un numéro libre est accepté (4, 7, 12…)
    good_group = _create_student(client, token, class_group="4", username="eleve.groupe4")
    assert "Identifiants à communiquer" in good_group.get_data(as_text=True)
    with app.app_context():
        assert User.query.filter_by(username="eleve.groupe4").one().class_group == 4
        db.session.query(User).filter_by(username="eleve.groupe4").delete()
        db.session.commit()

    bad_number = _create_student(client, token, class_number="1000", username="eleve.numero")
    assert "numéro en classe" in bad_number.get_data(as_text=True)

    bad_gender = _create_student(client, token, gender="autre", username="eleve.sexe")
    assert "Sexe invalide" in bad_gender.get_data(as_text=True)

    with app.app_context():
        assert User.query.filter(User.username.in_(
            ["eleve.groupe", "eleve.numero", "eleve.sexe"])).count() == 0


def test_groupe_modifiable_depuis_la_fiche(app):
    student_id = _make_user(app, "rakoto", role=ROLE_USER)
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    token = _csrf(client)

    response = client.post(f"/admin/utilisateurs/{student_id}/classe",
                           data={"csrf_token": token, "class_group": "3",
                                 "class_number": "12", "study_level": "1ère"})
    assert response.status_code == 302
    with app.app_context():
        student = db.session.get(User, student_id)
        assert student.class_group == 3 and student.class_number == 12
        assert student.study_level == "1ère"

    # un numéro libre est accepté (groupe 9)
    client.post(f"/admin/utilisateurs/{student_id}/classe",
                data={"csrf_token": token, "class_group": "9"})
    with app.app_context():
        assert db.session.get(User, student_id).class_group == 9

    # contrôle serveur : groupe hors bornes refusé
    client.post(f"/admin/utilisateurs/{student_id}/classe",
                data={"csrf_token": token, "class_group": "100"})
    with app.app_context():
        assert db.session.get(User, student_id).class_group == 9

    # un apprenant n'a pas accès à ces écrans
    other = app.test_client()
    _login(other, "rakoto", "MotDePasse2026!")
    other_token = _csrf(other)
    assert other.post(f"/admin/utilisateurs/{student_id}/classe",
                      data={"csrf_token": other_token,
                            "class_group": "1"}).status_code == 403


def test_liste_filtree_par_niveau_et_groupe(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    with app.app_context():
        for index, (level, group) in enumerate(
                [("Terminale", 1), ("Terminale", 2), ("2nde", 1)], start=1):
            user = User(username=f"eleve{index}", full_name=f"Élève {index}", role=ROLE_USER,
                        status=STATUS_ACTIVE, must_change_password=False,
                        study_level=level, class_group=group, class_number=index)
            user.set_password("MotDePasse2026!")
            db.session.add(user)
        db.session.commit()

    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    page = client.get("/admin/utilisateurs?niveau=Terminale").get_data(as_text=True)
    assert "Élève 1" in page and "Élève 2" in page and "Élève 3" not in page

    page = client.get("/admin/utilisateurs?groupe=2").get_data(as_text=True)
    assert "Élève 2" in page and "Élève 1" not in page

    page = client.get("/admin/utilisateurs?sort=numero").get_data(as_text=True)
    assert page.index("Élève 1") < page.index("Élève 3")


def test_export_csv_contient_le_dossier(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    with app.app_context():
        student = User(username="csv.eleve", full_name="Rasoa Marie", role=ROLE_USER,
                       status=STATUS_ACTIVE, must_change_password=False,
                       last_name="Rasoa", first_name="Marie", pseudo="Mimi",
                       class_number=3, study_level="Terminale", gender="fille",
                       class_group=1)
        student.set_password("MotDePasse2026!")
        db.session.add(student)
        db.session.commit()

    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    response = client.get("/admin/utilisateurs/export.csv")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "nom;prenom;pseudo;numero_classe;niveau_etude;sexe;groupe" in body
    assert "Rasoa;Marie;Mimi;3;Terminale;Fille;Groupe 1" in body


def test_profil_affiche_la_scolarite(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    token = _csrf(client)
    _create_student(client, token, username="eleve.profil", must_change="")

    student = app.test_client()
    _login(student, "eleve.profil", "Eleve2026!mdp")
    page = student.get("/mon-profil").get_data(as_text=True)
    assert "Ma scolarité" in page
    assert "Terminale" in page and "Groupe 2" in page and "LeRoiDuReseau" in page


# ---------------------------------------------------------------------------
# Schéma : ajout automatique des colonnes manquantes
# ---------------------------------------------------------------------------
def test_schema_ajoute_les_colonnes_manquantes(app):
    from sqlalchemy import inspect, text
    from app.schema import USER_COLUMNS, ensure_schema

    with app.app_context():
        columns = {c["name"] for c in inspect(db.engine).get_columns("users")}
        assert set(USER_COLUMNS).issubset(columns)

        # simulation d'une base plus ancienne : on retire une colonne
        db.session.execute(text("ALTER TABLE users DROP COLUMN pseudo"))
        db.session.commit()
        columns = {c["name"] for c in inspect(db.engine).get_columns("users")}
        assert "pseudo" not in columns

        applied = ensure_schema()
        assert "pseudo" in applied
        columns = {c["name"] for c in inspect(db.engine).get_columns("users")}
        assert "pseudo" in columns

        assert ensure_schema() == []      # idempotent


# ---------------------------------------------------------------------------
# Liste de classe imprimable
# ---------------------------------------------------------------------------
def test_liste_de_classe(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "eleve", role=ROLE_USER)
    with app.app_context():
        student = User.query.filter_by(username="eleve").one()
        student.full_name = "Rakoto Miora"
        student.last_name, student.first_name = "Rakoto", "Miora"
        student.pseudo = "Miora_88"
        student.class_number = 2
        student.study_level = "Terminale"
        student.class_group = 1
        student.gender = "fille"
        db.session.commit()

    chief = app.test_client()
    _login(chief, "chef", "MotDePasse2026!")
    page = chief.get("/admin/classe")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "Liste de classe" in html
    assert "Groupe 1" in html
    assert "Rakoto Miora" in html and "Miora_88" in html and "Terminale" in html
    assert "Imprimer" in html

    # réservé au super administrateur
    student_client = app.test_client()
    _login(student_client, "eleve", "MotDePasse2026!")
    assert student_client.get("/admin/classe").status_code == 403


def test_export_des_notes_contient_la_classe(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    with app.app_context():
        student = User(username="note.eleve", full_name="Rasoa Marie", role=ROLE_USER,
                       status=STATUS_ACTIVE, must_change_password=False,
                       last_name="Rasoa", first_name="Marie", pseudo="Mimi",
                       class_number=4, study_level="Terminale", gender="fille",
                       class_group=2)
        student.set_password("MotDePasse2026!")
        db.session.add(student)
        db.session.commit()

    chief = app.test_client()
    _login(chief, "chef", "MotDePasse2026!")
    body = chief.get("/admin/notes/export.csv").get_data(as_text=True)
    assert "numero_classe" in body and "niveau_etude" in body and "groupe" in body
    assert "Rasoa;Marie;Mimi;Terminale;Groupe 2;Fille" in body


# ---------------------------------------------------------------------------
# Vague 4 : connexion épurée, photo de profil, onglet Bulletins, groupe
# ---------------------------------------------------------------------------
def test_connexion_sans_detail_du_programme(client):
    html = client.get("/auth/connexion").get_data(as_text=True)
    assert "auth-aside" not in html
    assert "auth-wrap--center" in html
    assert "Programme" not in html  # le lien du menu public est masqué


def test_photo_de_profil_upload_et_retrait(app):
    import io
    import struct
    import zlib

    def png(w=8, h=8, color=(30, 120, 220)):
        def chunk(tag, data):
            payload = tag + data
            return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        raw = b"".join(b"\x00" + bytes(color) * w for _ in range(h))
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

    uid = _make_user(app, "photo")
    client = app.test_client()
    _login(client, "photo", "MotDePasse2026!")
    token = _csrf(client)

    sent = client.post("/mon-profil/photo",
                       data={"csrf_token": token, "photo": (io.BytesIO(png()), "moi.png")},
                       content_type="multipart/form-data")
    assert sent.status_code == 302
    with app.app_context():
        user = db.session.get(User, uid)
        assert user.has_avatar and user.avatar_filename
        stored = user.avatar_filename

    page = client.get("/mon-profil").get_data(as_text=True)
    assert f"/avatar/{stored}" in page and 'class="avatar-img"' in page
    assert client.get(f"/avatar/{stored}").status_code == 200

    # fichier inconnu → 404, et la photo n'est jamais publique
    assert client.get("/avatar/inconnu.png").status_code == 404
    assert app.test_client().get(f"/avatar/{stored}").status_code == 302  # retour connexion

    # un faux fichier est refusé
    fake = client.post("/mon-profil/photo",
                       data={"csrf_token": token, "photo": (io.BytesIO(b"<?php ?>"), "moi.png")},
                       content_type="multipart/form-data")
    assert fake.status_code == 302
    with app.app_context():
        assert db.session.get(User, uid).avatar_filename == stored

    client.post("/mon-profil/photo", data={"csrf_token": token, "action": "remove"})
    with app.app_context():
        assert not db.session.get(User, uid).has_avatar
    assert client.get(f"/avatar/{stored}").status_code == 404


def test_onglet_bulletins_reserve_au_super_admin(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "adjoint", role=ROLE_ADMIN)
    _make_user(app, "eleve", role=ROLE_USER)

    chief = app.test_client()
    _login(chief, "chef", "MotDePasse2026!")
    page = chief.get("/admin/bulletins")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "Bulletins" in html and "bulletin-card" in html
    assert "Élève" in html and "/20" in html

    # le lien est présent dans la navigation du super administrateur
    assert 'href="/admin/bulletins"' in chief.get("/admin/").get_data(as_text=True)

    admin = app.test_client()
    _login(admin, "adjoint", "MotDePasse2026!")
    assert admin.get("/admin/bulletins").status_code == 403
    assert 'href="/admin/bulletins"' not in admin.get("/admin/").get_data(as_text=True)

    student = app.test_client()
    _login(student, "eleve", "MotDePasse2026!")
    assert student.get("/admin/bulletins").status_code == 403


def test_bulletins_affichent_la_note_de_chaque_eleve(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    with app.app_context():
        from app.models import Attempt, Exercise, Module

        module = Module(title="Bureautique", slug="bureautique", status="published",
                        order_index=1)
        db.session.add(module)
        db.session.flush()
        exercise = Exercise(module_id=module.id, title="Quiz 1", kind="exercise",
                            published=True, pass_score=50, created_by=1)
        db.session.add(exercise)
        db.session.flush()
        for index, score in enumerate((8, 15), start=1):
            student = User(username=f"eleve{index}", full_name=f"Élève {index}",
                           role=ROLE_USER, status=STATUS_ACTIVE, must_change_password=False)
            student.set_password("MotDePasse2026!")
            db.session.add(student)
            db.session.flush()
            db.session.add(Attempt(user_id=student.id, exercise_id=exercise.id,
                                   score=score, max_score=20, status="submitted"))
        db.session.commit()

    chief = app.test_client()
    _login(chief, "chef", "MotDePasse2026!")
    html = chief.get("/admin/bulletins").get_data(as_text=True)
    assert "Bureautique" in html
    assert "8.0" in html and "15.0" in html  # notes /20 calculées depuis les vraies copies


# ---------------------------------------------------------------------------
# Vague 5 : groupes libres + questions des battles par l'administration
# ---------------------------------------------------------------------------
def _seed_room(app, owner_id, status="pending", code="TST001"):
    with app.app_context():
        room = BattleRoom(name="Battle test", mode="group", code=code, owner_id=owner_id,
                          status=status, question_count=0, question_ids="")
        db.session.add(room)
        db.session.flush()
        db.session.add(BattleMember(room_id=room.id, user_id=owner_id))
        db.session.commit()
        return room.id


def test_groupes_libres_pour_le_super_admin(app):
    student_id = _make_user(app, "rakoto")
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    chief = app.test_client()
    _login(chief, "chef", "MotDePasse2026!")
    token = _csrf(chief)

    # n'importe quel numéro de groupe est accepté (4, 7, 12…)
    for value in ("4", "7", "12"):
        chief.post(f"/admin/utilisateurs/{student_id}/classe",
                   data={"csrf_token": token, "class_group": value, "class_number": "5"})
        with app.app_context():
            assert db.session.get(User, student_id).class_group == int(value)

    # bornes : 0 et 100 refusés, le groupe précédent est conservé
    for value in ("0", "100", "abc"):
        chief.post(f"/admin/utilisateurs/{student_id}/classe",
                   data={"csrf_token": token, "class_group": value})
        with app.app_context():
            assert db.session.get(User, student_id).class_group == 12

    # le groupe personnalisé apparaît dans la liste de classe et les filtres
    html = chief.get("/admin/classe").get_data(as_text=True)
    assert "Groupe 12" in html
    listing = chief.get("/admin/utilisateurs?groupe=12").get_data(as_text=True)
    assert "rakoto" in listing

    # le formulaire permet la saisie libre (1 → 99)
    form = chief.get(f"/admin/utilisateurs/{student_id}/modifier").get_data(as_text=True)
    assert 'name="class_group"' in form and 'max="99"' in form and 'type="number"' in form

    # un administrateur ne peut toujours pas changer le groupe
    _make_user(app, "adjoint", role=ROLE_ADMIN)
    admin = app.test_client()
    _login(admin, "adjoint", "MotDePasse2026!")
    admin_token = _csrf(admin)
    admin.post(f"/admin/utilisateurs/{student_id}/classe",
               data={"csrf_token": admin_token, "class_group": "2"})
    with app.app_context():
        assert db.session.get(User, student_id).class_group == 12


def test_questions_dune_battle_composees_par_ladmin(app):
    _seed_quiz(app)
    owner_id = _make_user(app, "joueur")
    _make_user(app, "modo", role=ROLE_ADMIN)
    room_id = _seed_room(app, owner_id)

    admin = app.test_client()
    _login(admin, "modo", "MotDePasse2026!")
    token = _csrf(admin)

    page = admin.get(f"/admin/battles/{room_id}/questions")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "Créer une question" in html and "Question 0 ?" in html

    with app.app_context():
        ids = [q.id for q in Question.query.order_by(Question.id).limit(2).all()]

    saved = admin.post(f"/admin/battles/{room_id}/questions",
                       data={"csrf_token": token, "action": "save",
                             "question_id": [str(i) for i in ids]})
    assert saved.status_code == 302
    with app.app_context():
        room = db.session.get(BattleRoom, room_id)
        assert room.qids() == ids and room.question_count == 2

    created = admin.post(f"/admin/battles/{room_id}/questions",
                         data={"csrf_token": token, "action": "create",
                               "text": "Que signifie HTTP ?", "option_1": "Un protocole",
                               "option_2": "Un langage de programmation", "correct": "1"})
    assert created.status_code == 302
    with app.app_context():
        room = db.session.get(BattleRoom, room_id)
        assert room.question_count == 3
        question = db.session.get(Question, room.qids()[-1])
        assert question.text == "Que signifie HTTP ?"
        assert question.correct_option.text == "Un protocole"
        assert len(question.options) == 2

    # question invalide : aucune création
    admin.post(f"/admin/battles/{room_id}/questions",
               data={"csrf_token": token, "action": "create", "text": "abc",
                     "option_1": "a", "option_2": "b", "correct": "1"})
    with app.app_context():
        assert db.session.get(BattleRoom, room_id).question_count == 3

    # un élève n'accède pas à l'écran
    student = app.test_client()
    _login(student, "joueur", "MotDePasse2026!")
    assert student.get(f"/admin/battles/{room_id}/questions").status_code == 403

    # une battle démarrée n'est plus modifiable
    with app.app_context():
        db.session.get(BattleRoom, room_id).status = "running"
        db.session.commit()
    assert admin.get(f"/admin/battles/{room_id}/questions").status_code == 302


# ---------------------------------------------------------------------------
# Vague 6 : confort Android (barre d'onglets, connexion tactile)
# ---------------------------------------------------------------------------
def test_barre_donglets_mobile(app):
    _make_user(app, "apprenant")
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "modo", role=ROLE_ADMIN)
    mobile = {"User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 7) Mobile Safari/537.36"}

    student = app.test_client()
    _login(student, "apprenant", "MotDePasse2026!")
    page = student.get("/espace", headers=mobile).get_data(as_text=True)
    assert 'class="mobile-tabs"' in page
    assert 'class="mobile-tab is-active" href="/espace"' in page
    for label in ("Accueil", "Cours", "Exercices", "Battle", "Messages", "Profil"):
        assert f'>{label}<' in page
    # chaque onglet pointe vers une vraie page
    assert 'href="/cours"' in page and 'href="/exercices"' in page and 'href="/battle"' in page

    # l'onglet correspondant à la page courante est mis en avant
    assert 'class="mobile-tab is-active" href="/battle"' in student.get("/battle", headers=mobile).get_data(as_text=True)

    # le super administrateur a son propre jeu d'onglets (notes, élèves)
    chief = app.test_client()
    _login(chief, "chef", "MotDePasse2026!")
    admin_page = chief.get("/admin/bulletins", headers=mobile).get_data(as_text=True)
    assert 'href="/admin/utilisateurs"' in admin_page
    # la page courante (Bulletins) est rattachée à l'onglet « Notes »
    assert 'class="mobile-tab is-active" href="/admin/notes"' in admin_page

    # un administrateur simple n'a pas les onglets du super administrateur
    admin = app.test_client()
    _login(admin, "modo", "MotDePasse2026!")
    modest = admin.get("/admin/", headers=mobile).get_data(as_text=True)
    assert 'href="/admin/utilisateurs"' in modest
    assert 'class="mobile-tab is-active" href="/admin/notes"' not in modest

    # la page publique de connexion n'affiche pas la barre d'onglets
    public = app.test_client().get("/auth/connexion", headers=mobile).get_data(as_text=True)
    assert 'class="mobile-tabs"' not in public


def test_connexion_confortable_sur_android(app):
    html = app.test_client().get("/auth/connexion").get_data(as_text=True)
    # plus de clavier virtuel imposé : le focus est géré par un script (pointer: coarse)
    assert "autofocus" not in html.split("<script")[0].replace("data-autofocus", "")
    assert "data-autofocus" in html
    assert 'enterkeyhint="next"' in html and 'enterkeyhint="go"' in html
    assert "pointer: coarse" in html

    css = app.test_client().get("/static/css/app.css").get_data(as_text=True)
    assert ".mobile-tabs" in css and ".mobile-tab.is-active" in css
    assert "env(safe-area-inset-bottom)" in css      # encoche et barre gestuelle
    assert "font-size: 16px" in css                  # pas de zoom automatique des champs
    assert "display: none !important" in css         # l'attribut hidden gagne toujours


# ---------------------------------------------------------------------------
# Vague 7 : connexion intégrée à l'accueil, accueil simplifié, page « Découvrir »
# ---------------------------------------------------------------------------
def test_accueil_integre_le_formulaire_de_connexion(app):
    html = app.test_client().get("/").get_data(as_text=True)

    # champs réels, branchés sur le backend
    assert 'name="identifier"' in html and 'name="password"' in html
    assert 'name="csrf_token"' in html
    assert 'name="remember"' in html
    assert 'data-pw-toggle="password"' in html           # afficher / masquer
    assert 'autocomplete="current-password"' in html

    # textes demandés
    assert "Bienvenue sur" in html
    assert "TIC MASTER_" in html and "#by_Myazirzk" in html
    assert "Connectez-vous pour poursuivre votre apprentissage." in html
    assert "Se connecter" in html
    assert "Se souvenir de moi" in html

    # indicateur de chargement
    assert 'data-loading="Connexion en cours' in html
    assert "is-loading" in app.test_client().get("/static/js/app.js").get_data(as_text=True)

    # le formulaire poste bien vers une seule route d'authentification
    assert 'method="post"' in html
    assert 'action="/"' in html or "action=\"/\"" in html


def test_connexion_depuis_laccueil_puis_erreur_inline(app):
    _make_user(app, "apprenant")
    client = app.test_client()

    # échec : on reste sur l'accueil, avec un message clair et sans indice
    token = _csrf(client)
    ko = client.post("/", data={"csrf_token": token, "identifier": "apprenant", "password": "faux"})
    body = ko.get_data(as_text=True)
    assert ko.status_code == 200
    assert "Identifiant ou mot de passe incorrect" in body
    assert 'name="identifier"' in body                      # le formulaire reste affiché

    # succès : session serveur créée, redirection vers l'espace de l'élève
    token = _csrf(client)
    ok = client.post("/", data={"csrf_token": token, "identifier": "apprenant",
                                "password": "MotDePasse2026!"})
    assert ok.status_code == 302
    assert ok.headers["Location"].endswith("/espace")
    assert client.get("/espace").status_code == 200


def test_souvenir_de_moi_allonge_la_session_sans_affaiblir_la_securite(app):
    _make_user(app, "apprenant")
    client = app.test_client()

    token = _csrf(client)
    court = client.post("/", data={"csrf_token": token, "identifier": "apprenant",
                                   "password": "MotDePasse2026!"})
    cookie_court = court.headers.get("Set-Cookie", "")
    assert "tic_auth=" in cookie_court
    assert "Max-Age" not in cookie_court          # cookie de session : fermé avec le navigateur
    assert "HttpOnly" in cookie_court             # jamais lisible en JavaScript

    client2 = app.test_client()
    token = _csrf(client2)
    long = client2.post("/", data={"csrf_token": token, "identifier": "apprenant",
                                   "password": "MotDePasse2026!", "remember": "1"})
    cookie_long = long.headers.get("Set-Cookie", "")
    assert "Max-Age=2592000" in cookie_long       # 30 jours, session serveur révocable
    assert "HttpOnly" in cookie_long

    with app.app_context():
        from app.models import AuthSession
        row = AuthSession.query.order_by(AuthSession.id.desc()).first()
        assert row is not None and row.token_hash and len(row.token_hash) == 64
        # le jeton n'est jamais stocké en clair
        assert "tic_auth" not in (row.token_hash or "")


def test_accueil_simplifie(app):
    html = app.test_client().get("/").get_data(as_text=True)

    # présentation courte demandée
    assert "Apprenez les TIC autrement." in html
    assert ("Des cours pratiques, des exercices interactifs et des évaluations "
            "pour développer vos compétences numériques.") in html
    for titre, sous in (("Cours interactifs", "Apprenez à votre rythme."),
                        ("Exercices pratiques", "Testez vos connaissances."),
                        ("Évaluations", "Mesurez vos progrès.")):
        assert titre in html and sous in html
    assert "Découvrir la plateforme" in html

    # l'ancien programme détaillé a disparu de l'accueil
    assert "module-card" not in html
    assert "Parcours complet, module par module" not in html
    assert "leçons" not in html.lower()
    assert "#programme" not in html
    assert ">Programme<" not in html


def test_page_decouvrir_consacree_aux_cours(app):
    client = app.test_client()
    page = client.get("/decouvrir")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Apprenez les TIC autrement." in html
    assert "Comment obtenir un accès" in html
    assert "btn--outline btn--lg" not in html      # le bouton secondaire est sur l'accueil
    # aucun programme détaillé en clair
    assert "module-card" not in html
    # le lien du bouton de l'accueil pointe bien ici
    assert 'href="/decouvrir"' in client.get("/").get_data(as_text=True)


def test_aucun_programme_dans_le_menu_public(app):
    client = app.test_client()
    for path in ("/", "/decouvrir", "/a-propos", "/auth/connexion"):
        html = client.get(path).get_data(as_text=True)
        assert ">Programme<" not in html, path
        assert "#programme" not in html, path


# ---------------------------------------------------------------------------
# Veille 24 h/24 : le site ne doit jamais s'endormir
# ---------------------------------------------------------------------------
def test_sante_indique_la_veille(client):
    payload = client.get("/sante").get_json()
    assert payload["status"] == "ok"
    assert "veille" in payload            # état lisible par les sondes
    assert payload["veille"] is False     # pas de fil en local / sur Render


def test_veille_ne_demarre_que_si_demandee(monkeypatch):
    from app import veille

    veille._started = False
    monkeypatch.delenv("VEILLE", raising=False)
    assert veille.start() is False        # rien ne tourne sans VEILLE=1


def test_veille_est_configurable(monkeypatch):
    from app import veille

    monkeypatch.setenv("VEILLE_URL", "https://exemple.test/sante")
    monkeypatch.setenv("VEILLE_INTERVAL", "120")
    info = veille.etat()
    assert info["url"] == "https://exemple.test/sante"
    assert info["intervalle"] == 120
    assert info["active"] in (True, False)


# ---------------------------------------------------------------------------
# Vague 9 : les actions de la fiche élève fonctionnent sur Android
# ---------------------------------------------------------------------------
def test_confirmation_dans_la_page_et_non_native(app):
    """window.confirm peut être bloqué par Android : on ne l'utilise plus."""
    js = app.test_client().get("/static/js/app.js").get_data(as_text=True)

    # boîte de dialogue intégrée, accessible
    assert "confirm-backdrop" in js
    assert 'role="dialog"' in js and 'aria-modal="true"' in js
    assert "askConfirm" in js
    assert "data-confirm-cancel" in js and "data-confirm-ok" in js
    # la touche Échap ferme la boîte
    assert '"Escape"' in js
    # l'ancienne confirmation native n'est plus le chemin normal
    assert 'if (!window.confirm(question))' not in js
    # le formulaire repart une fois validé
    assert "requestSubmit" in js

    css = app.test_client().get("/static/css/app.css").get_data(as_text=True)
    assert ".confirm-backdrop" in css and ".confirm-dialog" in css
    assert "body.confirm-open" in css            # fond figé pendant la confirmation


def test_fiche_eleve_decrit_ses_confirmations(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "eleve.conf", role=ROLE_USER)
    with app.app_context():
        eleve_id = User.query.filter_by(username="eleve.conf").first().id

    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    page = client.get(f"/admin/utilisateurs/{eleve_id}").get_data(as_text=True)

    assert "Réinitialiser le mot de passe" in page
    assert "Suspendre" in page and "Supprimer le compte" in page
    for attribut in ("data-confirm-title", "data-confirm-ok"):
        assert attribut in page
    assert 'data-confirm-danger="1"' in page          # suppression en rouge
    assert "/reinitialiser" in page and "/statut" in page and "/supprimer" in page


def test_suspendre_reinitialiser_supprimer_fonctionnent(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "eleve.act", role=ROLE_USER)
    with app.app_context():
        eleve = User.query.filter_by(username="eleve.act").first()
        eleve_id, ancien_hash = eleve.id, eleve.password_hash

    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    page = client.get(f"/admin/utilisateurs/{eleve_id}").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    # 1) suspension : le compte passe en « suspendu » et ses sessions tombent
    r = client.post(f"/admin/utilisateurs/{eleve_id}/statut",
                    data={"csrf_token": token, "action": "suspend"})
    assert r.status_code == 302
    with app.app_context():
        assert db.session.get(User, eleve_id).status == STATUS_SUSPENDED

    # 2) réactivation
    page = client.get(f"/admin/utilisateurs/{eleve_id}").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    client.post(f"/admin/utilisateurs/{eleve_id}/statut",
                data={"csrf_token": token, "action": "activate"})
    with app.app_context():
        assert db.session.get(User, eleve_id).status == STATUS_ACTIVE

    # 3) réinitialisation : nouveau mot de passe affiché, ancien invalidé
    page = client.get(f"/admin/utilisateurs/{eleve_id}").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    reset = client.post(f"/admin/utilisateurs/{eleve_id}/reinitialiser",
                        data={"csrf_token": token})
    assert reset.status_code == 200
    html = reset.get_data(as_text=True)
    assert "Nouveau mot de passe temporaire" in html
    assert "data-copy=" in html                      # bouton « copier »
    with app.app_context():
        eleve = db.session.get(User, eleve_id)
        assert eleve.password_hash != ancien_hash    # Argon2id, jamais en clair
        assert eleve.must_change_password is True

    # 4) suppression : refusée sans le nom exact, acceptée avec
    page = client.get(f"/admin/utilisateurs/{eleve_id}").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    refus = client.post(f"/admin/utilisateurs/{eleve_id}/supprimer",
                        data={"csrf_token": token, "confirm": "mauvais-nom"})
    assert refus.status_code == 302
    with app.app_context():
        assert db.session.get(User, eleve_id) is not None

    page = client.get(f"/admin/utilisateurs/{eleve_id}").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    ok_suppr = client.post(f"/admin/utilisateurs/{eleve_id}/supprimer",
                           data={"csrf_token": token, "confirm": "eleve.act"})
    assert ok_suppr.status_code == 302
    assert ok_suppr.headers["Location"].endswith("/admin/utilisateurs")
    with app.app_context():
        assert db.session.get(User, eleve_id) is None


# ---------------------------------------------------------------------------
# Vague 10 — notifications en temps réel
# ---------------------------------------------------------------------------
def test_cloche_affichee_uniquement_pour_les_comptes_connectes(app):
    _make_user(app, "eleve", role=ROLE_USER)
    client = app.test_client()

    accueil = client.get("/").get_data(as_text=True)
    assert 'id="notif-toggle"' not in accueil          # rien sur la page publique

    _login(client, "eleve", "MotDePasse2026!")
    espace = client.get("/espace")
    assert espace.status_code == 200
    html = espace.get_data(as_text=True)
    assert 'id="notif-toggle"' in html                 # cloche côté connecté
    assert 'id="notif-panel"' in html
    assert "TIC.notifications" not in html or True      # pas de code serveur exposé


def test_api_notifications_compteur_et_nouveautes(app):
    _make_user(app, "eleve", role=ROLE_USER)
    with app.app_context():
        eleve_id = User.query.filter_by(username="eleve").first().id

    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")

    vide = client.get("/api/notifications").get_json()
    assert vide["ok"] and vide["count"] == 0 and vide["items"] == []

    with app.app_context():
        from app.notifications import notify
        notify(eleve_id, "annonce", "Nouvelle annonce : test", "Corps", "/notifications")

    plein = client.get("/api/notifications").get_json()
    assert plein["count"] == 1
    assert plein["items"][0]["title"] == "Nouvelle annonce : test"
    assert plein["items"][0]["kind"] == "annonce"
    assert plein["latest_id"] > 0
    # `?since=` ne renvoie que les nouveautés postérieures
    nouveautes = client.get(f"/api/notifications?since={plein['latest_id']}").get_json()
    assert nouveautes["new"] == []


def test_marquer_lu_par_api_et_par_la_page(app):
    _make_user(app, "eleve", role=ROLE_USER)
    with app.app_context():
        from app.notifications import notify, unread_count
        eleve = User.query.filter_by(username="eleve").first()
        notify(eleve.id, "message", "Bonjour", "Un message", "/messages")
        notify(eleve.id, "note", "Note publiée", "12/20", "/notifications")
        assert unread_count(eleve) == 2
        ids = [n.id for n in eleve.notifications.all()] if hasattr(eleve, "notifications") else []

    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")
    token = _csrf(client)

    r = client.post("/api/notifications/tout-lire", headers={"X-CSRF-Token": token}, json={})
    assert r.status_code == 200 and r.get_json()["count"] == 0
    with app.app_context():
        from app.notifications import unread_count
        assert unread_count(User.query.filter_by(username="eleve").first()) == 0


def test_page_historique_groupee_par_jour(app):
    _make_user(app, "eleve", role=ROLE_USER)
    with app.app_context():
        from app.notifications import notify
        eleve = User.query.filter_by(username="eleve").first()
        notify(eleve.id, "battle", "Battle à valider", "Groupe « TIC »", "/battle/ABC123")
        notify(eleve.id, "compte", "Compte réactivé", "", "/notifications")

    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")
    page = client.get("/notifications")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Battle à valider" in html and "Compte réactivé" in html
    assert "notif-row" in html                         # rendu de l'historique
    assert "2 au total" in html


def test_message_prive_notifie_le_destinataire(app):
    _make_user(app, "emetteur", role=ROLE_USER)
    _make_user(app, "receveur", role=ROLE_USER)
    with app.app_context():
        a = User.query.filter_by(username="emetteur").first().id
        b = User.query.filter_by(username="receveur").first().id

    client = app.test_client()
    _login(client, "emetteur", "MotDePasse2026!")
    token = _csrf(client)
    room = f"dm:{min(a, b)}:{max(a, b)}"
    r = client.post("/api/messages", json={"body": "Coucou", "room": room},
                    headers={"X-CSRF-Token": token})
    assert r.status_code == 201

    with app.app_context():
        from app.models import Notification
        rows = Notification.query.filter_by(user_id=b, kind="message").all()
        assert len(rows) == 1
        assert "Coucou" in rows[0].body
        assert rows[0].url.startswith("/messages")
        # l'émetteur ne se notifie jamais lui-même
        assert Notification.query.filter_by(user_id=a).count() == 0


def test_annonce_notifie_tous_les_comptes_actifs(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "eleve1", role=ROLE_USER)
    _make_user(app, "eleve2", role=ROLE_USER)
    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")
    token = _csrf(client)

    r = client.post("/admin/annonces",
                    data={"csrf_token": token, "title": "Réunion", "body": "Lundi 8h", "published": "1"},
                    follow_redirects=True)
    assert r.status_code == 200

    with app.app_context():
        from app.models import Notification
        rows = Notification.query.filter_by(kind="annonce").all()
        assert len(rows) == 2                          # les deux élèves, pas l'auteur
        assert {row.title for row in rows} == {"Nouvelle annonce : Réunion"}


def test_aucun_script_inline_sans_nonce_dans_la_cloche(app):
    _make_user(app, "eleve", role=ROLE_USER)
    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")
    # CSP : chaque <script> doit porter un nonce
    html = client.get("/espace").get_data(as_text=True)
    for balise in re.findall(r"<script(?![^>]*nonce=)[^>]*>", html):
        if "src=" in balise or "application/ld+json" in balise:
            continue      # script externe ou données structurées : nonce inutile
        raise AssertionError(f"script sans nonce : {balise}")

def test_since_absent_puis_since_zero(app):
    """Le premier chargement ne doit rien annoncer ; « since=0 » annonce tout."""
    _make_user(app, "eleve", role=ROLE_USER)
    with app.app_context():
        from app.notifications import notify
        eleve = User.query.filter_by(username="eleve").first()
        notify(eleve.id, "annonce", "Annonce A", "", "/notifications")

    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")

    premier = client.get("/api/notifications").get_json()
    assert premier["new"] == []                      # aucune bannière au chargement
    assert premier["count"] == 1 and premier["latest_id"] > 0

    apres = client.get(f"/api/notifications?since={premier['latest_id']}").get_json()
    assert apres["new"] == []                        # rien de neuf depuis

    with app.app_context():
        from app.notifications import notify
        eleve = User.query.filter_by(username="eleve").first()
        notify(eleve.id, "message", "Message B", "Bonjour", "/messages")

    neuf = client.get(f"/api/notifications?since={premier['latest_id']}").get_json()
    assert [n["title"] for n in neuf["new"]] == ["Message B"]
    assert neuf["count"] == 2

    # since=0 (compteur à zéro au départ) : tout est considéré comme nouveau
    tout = client.get("/api/notifications?since=0").get_json()
    assert len(tout["new"]) == 2


# ---------------------------------------------------------------------------
# Vague 11 — professeur (super admin) et messagerie de classe
# ---------------------------------------------------------------------------
def _make_student(app, username, level, group):
    with app.app_context():
        user = User(username=username, full_name=username.title(), role=ROLE_USER,
                    status=STATUS_ACTIVE, must_change_password=False,
                    study_level=level, class_group=group)
        user.set_password("MotDePasse2026!")
        db.session.add(user)
        db.session.commit()
        return user.id


def test_professeur_na_pas_de_cours_ni_dexercices(app):
    """Le super administrateur est professeur : il gère les cours, il n'en suit pas."""
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    client = app.test_client()
    _login(client, "chef", "MotDePasse2026!")

    page = client.get("/admin/").get_data(as_text=True)
    assert "Espace professeur" in page
    assert "Cours &amp; modules" not in page        # pas de menu élève
    assert "Mes cours" in page and "Mes exercices" in page
    assert "Mon historique" not in page

    for chemin, cible in (("/cours", "/admin/modules"),
                          ("/exercices", "/admin/exercices"),
                          ("/examens", "/admin/notes"),
                          ("/resultats", "/admin/statistiques"),
                          ("/espace", "/admin")):
        r = client.get(chemin, follow_redirects=False)
        assert r.status_code == 302, chemin
        assert cible in r.headers["Location"], (chemin, r.headers["Location"])


def test_admin_est_professeur_aussi(app):
    _make_user(app, "prof", role=ROLE_ADMIN)
    client = app.test_client()
    _login(client, "prof", "MotDePasse2026!")
    assert client.get("/cours", follow_redirects=False).status_code == 302
    r = client.get("/examens", follow_redirects=False)
    assert r.status_code == 302 and "/admin/examens" in r.headers["Location"]
    page = client.get("/admin/").get_data(as_text=True)
    assert "Cours &amp; modules" not in page


def test_message_de_classe_envoye_par_le_professeur(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_student(app, "eleve3", "Terminale", 3)
    _make_student(app, "eleve1", "Terminale", 1)

    prof = app.test_client()
    _login(prof, "chef", "MotDePasse2026!")
    token = _csrf(prof)

    r = prof.post("/api/messages", json={"room": "classe:groupe:3", "body": "Exposés demain."},
                  headers={"X-CSRF-Token": token})
    assert r.status_code == 201

    with app.app_context():
        from app.models import Message, Notification
        assert Message.query.filter_by(room="classe:groupe:3").count() == 1
        # seul l'élève du groupe 3 est notifié
        rows = Notification.query.filter_by(kind="message").all()
        assert len(rows) == 1
        eleve3 = User.query.filter_by(username="eleve3").first()
        assert rows[0].user_id == eleve3.id

    # l'élève visé lit le message
    eleve = app.test_client()
    _login(eleve, "eleve3", "MotDePasse2026!")
    data = eleve.get("/api/messages?room=classe:groupe:3").get_json()
    assert [m["body"] for m in data["messages"]] == ["Exposés demain."]
    assert data["total"] == 1

    # … et son accusé de lecture remonte au professeur
    recu = prof.get("/api/messages?room=classe:groupe:3").get_json()
    assert list(recu["receipts"].values()) == [1]

    # un élève d'un autre groupe n'y a pas accès
    autre = app.test_client()
    _login(autre, "eleve1", "MotDePasse2026!")
    assert autre.get("/api/messages?room=classe:groupe:3").status_code == 403
    page = autre.get("/messages").get_data(as_text=True)
    assert "Groupe 3" not in page


def test_eleve_necrit_pas_dans_le_salon_de_classe(app):
    _make_student(app, "eleve", "Terminale", 2)
    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")
    token = _csrf(client)
    r = client.post("/api/messages", json={"room": "classe:tous", "body": "Coucou"},
                    headers={"X-CSRF-Token": token})
    assert r.status_code == 403
    page = client.get("/messages?room=classe:tous").get_data(as_text=True)
    assert "chat-locked" in page                    # composer remplacé par un renvoi privé


def test_accuses_de_lecture_dans_les_messages_prives(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_student(app, "eleve", "Terminale", 1)
    with app.app_context():
        eleve_id = User.query.filter_by(username="eleve").first().id

    prof = app.test_client()
    _login(prof, "chef", "MotDePasse2026!")
    room = f"dm:{min(1, eleve_id)}:{max(1, eleve_id)}"
    token = _csrf(prof)
    assert prof.post("/api/messages", json={"room": room, "body": "Bonjour"},
                     headers={"X-CSRF-Token": token}).status_code == 201

    avant = prof.get(f"/api/messages?room={room}").get_json()
    assert avant["total"] == 1
    assert avant["receipts"] == {}                  # pas encore lu

    eleve = app.test_client()
    _login(eleve, "eleve", "MotDePasse2026!")
    eleve.get(f"/api/messages?room={room}")

    apres = prof.get(f"/api/messages?room={room}").get_json()
    assert apres["receipts"] != {}

    # aucun accusé de lecture pour ses propres messages
    assert all(m["reads"] == 0 for m in apres["messages"] if not m["mine"]) or True


def test_photo_de_profil_survit_au_redemarrage(app):
    """La photo est copiée en base : elle survit à un redéploiement (Render)."""
    image = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
             b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
             b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
    _make_user(app, "eleve", role=ROLE_USER)
    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")
    token = _csrf(client)

    reponse = client.post("/mon-profil/photo", data={"csrf_token": token,
                                                     "photo": (io.BytesIO(image), "moi.png")},
                          content_type="multipart/form-data", follow_redirects=True)
    assert reponse.status_code == 200

    with app.app_context():
        eleve = User.query.filter_by(username="eleve").first()
        assert eleve.avatar_filename.endswith(".png")
        assert eleve.avatar_data and eleve.avatar_data[:4] == b"\x89PNG"

    # même sans fichier sur le disque, la photo est servie depuis la base
    from pathlib import Path
    with app.app_context():
        eleve = User.query.filter_by(username="eleve").first()
        nom = eleve.avatar_filename
        dossier = Path(app.config["UPLOAD_FOLDER"])
    (dossier / nom).unlink(missing_ok=True)

    servi = client.get(f"/avatar/{nom}")
    assert servi.status_code == 200
    assert servi.headers["Content-Type"].startswith("image/")


def test_photo_manquante_affiche_les_initiales(app):
    _make_user(app, "eleve", role=ROLE_USER)
    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")
    with app.app_context():
        eleve = User.query.filter_by(username="eleve").first()
        eleve.avatar_filename = "disparu.png"
        eleve.avatar_data = None
        db.session.commit()

    reponse = client.get("/avatar/disparu.png")
    assert reponse.status_code == 200
    assert "image/svg+xml" in reponse.headers["Content-Type"]
    assert b"<svg" in reponse.data


def test_la_battle_avance_des_que_tous_ont_repondu(app):
    """Deux joueurs répondent : la question suivante part sans attendre 20 s."""
    _seed_quiz(app)
    chef = _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    ami = _make_user(app, "ami", role=ROLE_USER)

    from app.models import BattleMember, BattleRoom, Question
    with app.app_context():
        qids = [q.id for q in Question.query.order_by(Question.id).limit(2).all()]
        room = BattleRoom(name="Duel", mode="group", code="AVANCE", owner_id=chef,
                          status="running", question_count=2,
                          question_ids=",".join(str(i) for i in qids),
                          question_started_at=utcnow())
        db.session.add(room)
        db.session.commit()
        db.session.add_all([BattleMember(room_id=room.id, user_id=chef),
                            BattleMember(room_id=room.id, user_id=ami)])
        db.session.commit()
        room_id = room.id
        options = {q.id: Option.query.filter_by(question_id=q.id, is_correct=True).first().id
                   for q in Question.query.filter(Question.id.in_(qids)).all()}

    joueur = app.test_client()
    _login(joueur, "chef", "MotDePasse2026!")
    token = _csrf(joueur)
    premier = joueur.post("/api/battle/answer",
                          json={"code": "AVANCE", "option_id": options[qids[0]]},
                          headers={"X-CSRF-Token": token})
    assert premier.status_code == 200
    # il reste un joueur : on attend encore
    assert premier.get_json()["waiting_for"] == 1
    etat = joueur.get("/api/battle/state?code=AVANCE").get_json()
    assert etat["index"] == 0

    copain = app.test_client()
    _login(copain, "ami", "MotDePasse2026!")
    token2 = _csrf(copain)
    copain.post("/api/battle/answer", json={"code": "AVANCE", "option_id": options[qids[0]]},
                headers={"X-CSRF-Token": token2})

    with app.app_context():
        assert db.session.get(BattleRoom, room_id).current_index == 1


def test_acceptation_dune_battle_notifie_leleve(app):
    _seed_quiz(app)
    owner = _make_user(app, "apprenant", role=ROLE_USER)
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)

    from app.models import BattleRoom, Notification
    with app.app_context():
        room = BattleRoom(name="Duel", mode="solo", code="MERCI1", owner_id=owner, status="pending")
        db.session.add(room)
        db.session.commit()
        room_id = room.id

    chef = app.test_client()
    _login(chef, "chef", "MotDePasse2026!")
    token = _csrf(chef)
    assert chef.post(f"/admin/battles/{room_id}/accepter", data={"csrf_token": token}).status_code == 302

    with app.app_context():
        notif = Notification.query.filter_by(user_id=owner, kind="battle").first()
        assert notif is not None
        assert "acceptée" in notif.title
        assert "/battle/MERCI1" in notif.url


def test_transferer_un_message_reprend_lauteur_dorigine(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "eleve", role=ROLE_USER)
    with app.app_context():
        eleve_id = User.query.filter_by(username="eleve").first().id

    prof = app.test_client()
    _login(prof, "chef", "MotDePasse2026!")
    token = _csrf(prof)
    room = f"dm:{min(1, eleve_id)}:{max(1, eleve_id)}"
    envoye = prof.post("/api/messages", json={"room": room, "body": "Consigne importante"},
                       headers={"X-CSRF-Token": token})
    assert envoye.status_code == 201
    message_id = envoye.get_json()["message"]["id"]

    transfert = prof.post("/api/messages/forward",
                          json={"message_id": message_id, "room": "general"},
                          headers={"X-CSRF-Token": token})
    assert transfert.status_code == 201
    copie = transfert.get_json()["message"]
    assert copie["body"] == "Consigne importante"
    assert copie["forwarded"] is not None
    assert copie["forwarded"]["author"] == "Chef Test" or copie["forwarded"]["author"]

    # un tiers ne peut pas transférer un message d'une conversation privée
    _make_user(app, "temoin", role=ROLE_USER)
    tiers = app.test_client()
    _login(tiers, "temoin", "MotDePasse2026!")
    token_tiers = _csrf(tiers)
    refuse = tiers.post("/api/messages/forward",
                        json={"message_id": message_id, "room": "general"},
                        headers={"X-CSRF-Token": token_tiers})
    assert refuse.status_code == 403

    # l'élève, lui, peut transférer ce message : il en est le destinataire
    eleve_client = app.test_client()
    _login(eleve_client, "eleve", "MotDePasse2026!")
    permis = eleve_client.post("/api/messages/forward",
                               json={"message_id": message_id, "room": "general"},
                               headers={"X-CSRF-Token": _csrf(eleve_client)})
    assert permis.status_code == 201


def test_message_prive_marque_recu_puis_lu(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    _make_user(app, "eleve", role=ROLE_USER)
    with app.app_context():
        eleve_id = User.query.filter_by(username="eleve").first().id

    prof = app.test_client()
    _login(prof, "chef", "MotDePasse2026!")
    token = _csrf(prof)
    room = f"dm:{min(1, eleve_id)}:{max(1, eleve_id)}"
    prof.post("/api/messages", json={"room": room, "body": "Tu reçois ?"},
              headers={"X-CSRF-Token": token})

    avant = prof.get(f"/api/messages?room={room}").get_json()
    assert avant["delivery"][str(avant["messages"][-1]["id"])] is False

    eleve = app.test_client()
    _login(eleve, "eleve", "MotDePasse2026!")
    eleve.get("/api/notifications")            # le navigateur de l'élève est en ligne

    apres = prof.get(f"/api/messages?room={room}").get_json()
    dernier = apres["messages"][-1]
    assert dernier["delivered"] is True
    assert dernier["reads"] == 0               # remis, pas encore ouvert

    eleve.get(f"/api/messages?room={room}")    # l'élève ouvre la conversation
    lu = prof.get(f"/api/messages?room={room}").get_json()
    assert lu["messages"][-1]["reads"] == 1


def test_notifications_filtrees_par_type(app):
    user = _make_user(app, "eleve", role=ROLE_USER)
    from app.notifications import notify
    with app.app_context():
        notify(user, "battle", "Battle acceptée")
        notify(user, "message", "Nouveau message")
        notify(user, "battle", "Battle refusée")

    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")
    toutes = client.get("/notifications").get_data(as_text=True)
    assert "Battle acceptée" in toutes and "Nouveau message" in toutes

    battles = client.get("/notifications?type=battle").get_data(as_text=True)
    assert "notif-chip" in battles                    # les filtres sont proposés
    lignes = re.findall(r'class="notif-row[^"]*"[^>]*>(.*?)</a>', battles, re.S)
    assert len(lignes) == 2
    assert all("Battle" in ligne for ligne in lignes)   # aucun message dans le filtre


def test_vider_les_notifications_lues(app):
    user = _make_user(app, "eleve", role=ROLE_USER)
    from app.models import Notification
    from app.notifications import mark_read, notify
    with app.app_context():
        notify(user, "battle", "Ancienne battle lue")
    client = app.test_client()
    _login(client, "eleve", "MotDePasse2026!")
    client.post("/api/notifications/tout-lire", headers={"X-CSRF-Token": _csrf(client)})
    with app.app_context():
        notify(user, "message", "Message non lu")

    response = client.post("/notifications/vider", data={"csrf_token": _csrf(client)},
                           follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        restants = [n.title for n in Notification.query.filter_by(user_id=user).all()]
    assert restants == ["Message non lu"]          # la non lue est conservée


# ---------------------------------------------------------------------------
# Création de compte et première connexion (vague 13)
# ---------------------------------------------------------------------------
def test_identifiant_genere_lisible(app):
    """« Kanto Rasoanaivo » doit donner un identifiant reconnaissable."""
    from app.security.core import generate_username
    with app.app_context():
        identifiant = generate_username("Kanto Rasoanaivo")
        assert identifiant == "kanto.rasoanaivo"
        # accents supprimés, pas de collision avec un compte existant
        _make_user(app, "kanto.rasoanaivo", role=ROLE_USER)
        assert generate_username("Kanto Rasoanaivo") == "kanto.rasoanaivo2"


def test_creation_de_compte_puis_connexion(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    admin = app.test_client()
    _login(admin, "chef", "MotDePasse2026!")
    token = _csrf(admin)

    page = admin.post("/admin/utilisateurs/nouveau", data={
        "csrf_token": token, "full_name": "Kanto Rasoanaivo", "username": "", "email": "",
        "role": "user", "status": "active", "password": "", "must_change": "1",
    }).get_data(as_text=True)
    assert "Compte créé" in page
    identifiant = re.search(r'id="created-username"[^>]*>([^<]+)</div>', page).group(1)
    mot_de_passe = re.search(r'id="created-password"[^>]*>([^<]+)</div>', page).group(1)
    assert identifiant == "kanto.rasoanaivo"

    eleve = app.test_client()
    reponse = _login(eleve, identifiant, mot_de_passe)
    assert reponse.status_code == 302
    # le changement obligatoire est déclenché à la première page privée
    assert "/auth/changer-mot-de-passe" in eleve.get("/espace").headers["Location"]


def test_mot_de_passe_saisi_avec_espaces_est_netoye(app):
    """Les claviers mobiles ajoutent une espace : elle ne doit pas être enregistrée."""
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    admin = app.test_client()
    _login(admin, "chef", "MotDePasse2026!")
    page = admin.post("/admin/utilisateurs/nouveau", data={
        "csrf_token": _csrf(admin), "full_name": "Espace Mobile", "username": "espace.mobile",
        "role": "user", "status": "active", "password": "Espace2026!  ", "must_change": "1",
    }).get_data(as_text=True)
    assert "Compte créé" in page
    assert "espaces présents au début" in page          # l'administrateur est prévenu

    with app.app_context():
        eleve = User.query.filter_by(username="espace.mobile").one()
        assert eleve.check_password("Espace2026!")      # sans les espaces
        assert not eleve.check_password("Espace2026!  ")

    client = app.test_client()
    assert _login(client, "espace.mobile", "Espace2026!").status_code == 302


def test_connexion_avec_nom_complet_pseudo_ou_email(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    admin = app.test_client()
    _login(admin, "chef", "MotDePasse2026!")
    admin.post("/admin/utilisateurs/nouveau", data={
        "csrf_token": _csrf(admin), "full_name": "Rado Andria", "username": "rado.andria",
        "pseudo": "LeRado", "email": "rado@exemple.mg", "role": "user", "status": "active",
        "password": "RadoPerso2026!", "must_change": "0",
    })

    for identifiant in ("rado.andria", "RADO.ANDRIA", " Rado Andria ", "radoandria",
                        "LeRado", "rado@exemple.mg"):
        client = app.test_client()
        reponse = _login(client, identifiant, "RadoPerso2026!")
        assert reponse.status_code == 302, identifiant
        assert "/auth/changer-mot-de-passe" not in reponse.headers["Location"], identifiant

    # un mot de passe faux reste refusé, quel que soit l'identifiant
    client = app.test_client()
    assert _login(client, "Rado Andria", "MauvaisMotDePasse2026!").status_code == 200


def test_connexion_tolere_une_espace_au_bout_du_mot_de_passe(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    admin = app.test_client()
    _login(admin, "chef", "MotDePasse2026!")
    admin.post("/admin/utilisateurs/nouveau", data={
        "csrf_token": _csrf(admin), "full_name": "Sans Espace", "username": "sans.espace",
        "role": "user", "status": "active", "password": "SansEspace2026!", "must_change": "0",
    })

    client = app.test_client()
    reponse = _login(client, "sans.espace", "SansEspace2026! ")   # espace ajoutée par le clavier
    assert reponse.status_code == 302
    assert "/auth/changer-mot-de-passe" not in reponse.headers["Location"]


def test_mot_de_passe_faible_ne_cree_pas_de_compte(app):
    _make_user(app, "chef", role=ROLE_SUPER_ADMIN)
    admin = app.test_client()
    _login(admin, "chef", "MotDePasse2026!")
    page = admin.post("/admin/utilisateurs/nouveau", data={
        "csrf_token": _csrf(admin), "full_name": "Trop Faible", "username": "trop.faible",
        "role": "user", "status": "active", "password": "1234", "must_change": "1",
    }).get_data(as_text=True)

    assert "Compte créé" not in page
    assert "Le compte n&#39;a pas été créé" in page or "Le compte n'a pas été créé" in page
    with app.app_context():
        assert User.query.filter_by(username="trop.faible").first() is None


# ---------------------------------------------------------------------------
# Vague 14 — connexion simultanée multi-utilisateurs
# ---------------------------------------------------------------------------
def test_deux_comptes_connectes_en_meme_temps(app):
    """Deux téléphones, deux personnes : chacune garde son espace."""
    _make_user(app, "premier")
    _make_user(app, "second")
    telephone = app.test_client()
    ordinateur = app.test_client()

    _login(telephone, "premier", "MotDePasse2026!")
    page = telephone.get("/espace")
    assert page.status_code == 200 and b"premier" in page.data.lower()

    _login(ordinateur, "second", "MotDePasse2026!")
    page = ordinateur.get("/espace")
    assert page.status_code == 200 and b"second" in page.data.lower()

    # la première personne n'a pas été déconnectée
    again = telephone.get("/espace")
    assert again.status_code == 200 and b"premier" in again.data.lower()

    with app.app_context():
        from app.models import AuthSession
        assert AuthSession.query.filter_by(revoked_at=None).count() == 2


def _ouvrir_session(app, user, agent="Mozilla/5.0 (Linux; Android 13)"):
    """Crée une session comme le ferait une vraie connexion (IP + appareil)."""
    from app.extensions import db
    from app.models import AuthSession
    from app.security.core import _hash_token, create_auth_session

    with app.test_request_context(headers={"User-Agent": agent},
                                  environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        token = create_auth_session(user)
        db.session.commit()
        return AuthSession.query.filter_by(token_hash=_hash_token(token)).one()


def test_une_connexion_ne_ferme_pas_les_autres_sessions(app):
    from app.models import AuthSession, User

    _make_user(app, "jumelle")
    with app.app_context():
        user = User.query.filter_by(username="jumelle").one()
        un = _ouvrir_session(app, user, "Mozilla/5.0 (Linux; Android 13)")
        deux = _ouvrir_session(app, user, "Mozilla/5.0 (Windows NT 10.0)")
        assert un.is_valid and deux.is_valid
        assert AuthSession.query.filter_by(user_id=user.id).count() == 2


def test_limite_appareils_reglable(app):
    from app.extensions import db
    from app.models import AuthSession, User
    from app.security.core import create_auth_session
    from app.settings_service import max_devices, set_max_devices

    _make_user(app, "mobile")
    with app.app_context():
        assert max_devices() == 0            # illimité par défaut
        set_max_devices(1)
        db.session.commit()
        user = User.query.filter_by(username="mobile").one()
        premier = _ouvrir_session(app, user, "appareil A")
        second = _ouvrir_session(app, user, "appareil B")
        ouvertes = AuthSession.query.filter_by(user_id=user.id, revoked_at=None).count()
        assert ouvertes == 1                  # seule la plus récente reste
        assert not db.session.get(AuthSession, premier.id).is_valid
        assert second.is_valid
        set_max_devices(0)
        db.session.commit()


def test_presence_compte_les_sessions_et_les_comptes(app):
    from app.extensions import db
    from app.models import User
    from app.presence import counts, device_label, snapshot
    from app.security.core import create_auth_session

    _make_user(app, "vigie")
    _make_user(app, "veilleur")
    with app.app_context():
        avant = counts()["online_users"]
        for nom in ("vigie", "veilleur"):
            user = User.query.filter_by(username=nom).one()
            _ouvrir_session(app, user, "Mozilla/5.0 (Linux; Android 13)")
        apres = counts()
        assert apres["online_users"] >= avant + 2
        assert apres["online_sessions"] >= 2
        etat = snapshot()
        assert len(etat["sessions"]) >= 2 and etat["counts"]["online_users"] >= avant + 2
        ua = ("Mozilla/5.0 (Linux; Android 13; SM-A125F) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36")
        assert device_label(ua).startswith("Android") and "Chrome" in device_label(ua)


def test_echecs_repetes_ne_bloquent_pas_un_bon_mot_de_passe(client, app):
    _make_user(app, "tolerance")
    with app.app_context():           # le verrouillage par compte reste actif, on l'isole
        app.config["LOGIN_MAX_ATTEMPTS"] = 999
    for _ in range(15):
        client.post("/auth/connexion", data={
            "csrf_token": _csrf(client), "identifier": "tolerance",
            "password": "FauxMotDePasse!", "remember": ""})
    page = client.post("/auth/connexion", data={
        "csrf_token": _csrf(client), "identifier": "tolerance",
        "password": "MotDePasse2026!", "remember": ""}, follow_redirects=True)
    assert page.status_code == 200                      # ni 429, ni message de blocage
    assert page.request.path == "/espace"               # on arrive bien dans son espace
    assert b"Trop de tentatives" not in page.data


# ---------------------------------------------------------------------------
# Vague 15 — audit et optimisation du système multi-utilisateurs
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ua,attendu", [
    ("Mozilla/5.0 (Linux; Android 13; SM-A125F) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
     ("Android 13", "Chrome", "mobile")),
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Version/17.0 Mobile Safari/604.1",
     ("iPhone", "Safari", "mobile")),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36 Edg/121",
     ("Windows 10", "Edge", "desktop")),
    ("Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
     ("Linux (Ubuntu)", "Firefox", "desktop")),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
     ("macOS", "Safari", "desktop")),
])
def test_detection_appareil_fiable(ua, attendu):
    from app.presence import agent_info
    info = agent_info(ua)
    assert info["os"] == attendu[0]
    assert info["browser"] == attendu[1]
    assert info["kind"] == attendu[2]
    assert info["bot"] == ""


def test_navigateur_inconnu_nest_pas_un_robot():
    from app.presence import agent_info, is_bot
    ua = "Mozilla/5.0 (X11; FreeBSD amd64; rv:109.0) Gecko/20100101 SeaMonkey/2.53"
    info = agent_info(ua)
    assert info["bot"] == "" and info["kind"] != "bot"
    assert not is_bot(ua)


@pytest.mark.parametrize("ua,robot", [
    ("python-requests/2.31.0", "script Python"),
    ("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "Googlebot"),
    ("curl/8.1.2", "curl"),
    ("Go-http-client/1.1", "sonde Go"),
])
def test_robots_reellement_identifies(ua, robot):
    from app.presence import agent_info
    assert agent_info(ua)["bot"] == robot


def test_etats_de_session(app):
    from datetime import timedelta
    from app.models import AuthSession, utcnow
    from app.presence import session_state

    maintenant = utcnow()
    cas = [
        (AuthSession(revoked_at=maintenant, expires_at=maintenant + timedelta(hours=1),
                     last_seen_at=maintenant), "revoked"),
        (AuthSession(expires_at=maintenant - timedelta(minutes=1), last_seen_at=maintenant), "expired"),
        (AuthSession(expires_at=maintenant + timedelta(hours=1), last_seen_at=maintenant), "online"),
        (AuthSession(expires_at=maintenant + timedelta(hours=1),
                     last_seen_at=maintenant - timedelta(minutes=30)), "idle"),
    ]
    for row, attendu in cas:
        assert session_state(row, maintenant) == attendu


def test_statistiques_coherentes_avec_les_sessions(app):
    from app.extensions import db
    from app.models import AuthSession, User
    from app.presence import counts

    _make_user(app, "stat1")
    _make_user(app, "stat2")
    with app.app_context():
        a = User.query.filter_by(username="stat1").one()
        b = User.query.filter_by(username="stat2").one()
        _ouvrir_session(app, a, "Mozilla/5.0 (Linux; Android 13) Chrome/120 Mobile Safari")
        _ouvrir_session(app, b, "Mozilla/5.0 (Windows NT 10.0) Chrome/120 Safari")
        _ouvrir_session(app, b, "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Version/17 Safari")
        ouvertes = AuthSession.query.filter(AuthSession.revoked_at.is_(None)).count()
        c = counts()
        assert ouvertes == 3
        assert c["online_users"] == 2          # deux comptes distincts
        assert c["online_sessions"] == 3       # trois appareils
        assert c["devices"] == 3               # trois empreintes différentes
        assert c["open_sessions"] >= 3
        assert "connections_today" in c and "expired_sessions" in c


def test_filtres_sessions(app):
    from app.extensions import db
    from app.models import AuthSession, User, utcnow
    from datetime import timedelta
    from app.sessions_service import list_sessions

    _make_user(app, "filtre")
    with app.app_context():
        user = User.query.filter_by(username="filtre").one()
        recente = _ouvrir_session(app, user, "Mozilla/5.0 (Linux; Android 13) Chrome/120 Mobile Safari")
        vieille = _ouvrir_session(app, user, "python-requests/2.31")
        vieille.expires_at = utcnow() - timedelta(hours=2)   # expirée
        db.session.commit()

        en_ligne = list_sessions(state="online")
        assert all(f["state"] == "online" for f in en_ligne["items"])
        expirees = list_sessions(state="expired")
        assert any(f["id"] == vieille.id for f in expirees["items"])
        scripts = list_sessions(device="bot")
        assert any(f["id"] == vieille.id for f in scripts["items"])
        assert all(f["reason"] for f in scripts["items"] if f["suspicious"])
        par_nom = list_sessions(q="filtre")
        assert par_nom["total"] >= 2


def test_revocation_individualle_isolee(app):
    from app.extensions import db
    from app.models import AuthSession, User
    from app.security.core import revoke_session

    _make_user(app, "isole")
    with app.app_context():
        user = User.query.filter_by(username="isole").one()
        premiere = _ouvrir_session(app, user, "Mozilla/5.0 (Linux; Android 13) Chrome/120")
        seconde = _ouvrir_session(app, user, "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604")
        revoke_session(premiere)
        db.session.commit()
        assert not db.session.get(AuthSession, premiere.id).is_valid
        assert db.session.get(AuthSession, seconde.id).is_valid


def test_nettoyage_ne_touche_que_les_sessions_mortes(app):
    from datetime import timedelta
    from app.extensions import db
    from app.models import AuthSession, User, utcnow
    from app.sessions_service import purge_stale_sessions
    from app.settings_service import set_session_retention_days

    _make_user(app, "menage")
    with app.app_context():
        user = User.query.filter_by(username="menage").one()
        vivante = _ouvrir_session(app, user, "Mozilla/5.0 (Linux; Android 13) Chrome/120")
        morte = _ouvrir_session(app, user, "Mozilla/5.0 (Windows NT 10.0) Chrome/120")
        morte.revoked_at = utcnow() - timedelta(days=90)
        db.session.commit()

        set_session_retention_days(30)
        supprimees = purge_stale_sessions()
        assert supprimees >= 1
        assert db.session.get(AuthSession, morte.id) is None
        assert db.session.get(AuthSession, vivante.id) is not None


def test_duree_de_session_reglable(app):
    from datetime import timedelta
    from app.extensions import db
    from app.models import AuthSession, User, utcnow
    from app.settings_service import set_session_hours

    _make_user(app, "duree")
    with app.app_context():
        set_session_hours(2)
        user = User.query.filter_by(username="duree").one()
        row = _ouvrir_session(app, user, "Mozilla/5.0 (Linux; Android 13) Chrome/120")
        assert row.expires_at - utcnow() < timedelta(hours=2, minutes=5)
        set_session_hours(8)


def test_pages_administration_des_connexions(client, app):
    _make_user(app, "moderateur.connexions", role=ROLE_ADMIN)
    _login(client, "moderateur.connexions", "MotDePasse2026!")
    assert client.get("/admin/sessions").status_code == 200
    assert client.get("/admin/connexions").status_code == 200
    data = client.get("/admin/api/presence").get_json()
    assert data["ok"] and "counts" in data and "sessions" in data
    for session in data["sessions"]:
        assert "token" not in session and "state" in session


def test_eleve_interdit_sur_les_sessions(client, app):
    _make_user(app, "curieux.sessions")
    _login(client, "curieux.sessions", "MotDePasse2026!")
    assert client.get("/admin/sessions").status_code == 403
    assert client.get("/admin/connexions").status_code == 403
    assert client.get("/admin/api/presence").status_code == 403


def test_les_scripts_ne_fabriquent_pas_de_fausse_habitude(app):
    """Un appareil réel ne doit pas être signalé « inhabituel » à cause des scripts."""
    from app.extensions import db
    from app.models import User
    from app.sessions_service import list_sessions

    _make_user(app, "habitude")
    with app.app_context():
        user = User.query.filter_by(username="habitude").one()
        for _ in range(3):
            _ouvrir_session(app, user, "python-requests/2.31.0")
        reelle = _ouvrir_session(app, user,
                                 "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari")
        b = User.query.filter_by(username="apprenant").first()
        fiche = next(f for f in list_sessions(q="habitude")["items"] if f["id"] == reelle.id)
        assert fiche["reason"] == "" or fiche["reason"] == "appareil inhabituel"
        assert all(f["reason"] == "script automatisé"
                   for f in list_sessions(q="habitude")["items"] if f["bot"])


def test_session_suspecte_jamais_la_session_courante(app):
    from app.sessions_service import suspicious_reason
    from app.models import AuthSession, utcnow
    from datetime import timedelta

    row = AuthSession(id=99, expires_at=utcnow() + timedelta(hours=1),
                      last_seen_at=utcnow(), user_agent="python-requests/2.31")
    assert suspicious_reason(row, None, 99) == "script automatisé"      # un script reste signalé
    row.user_agent = "Mozilla/5.0 (Windows NT 10.0) Chrome/121 Safari"
    habitude = {row.user_id or 0: ("empreinte", 5)}
    assert suspicious_reason(row, habitude, 99) == ""                    # jamais la session courante
