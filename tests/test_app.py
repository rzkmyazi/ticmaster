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
    Attempt, BattleMember, BattleRoom, Exercise, Module, Question, Option, User, utcnow,
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
