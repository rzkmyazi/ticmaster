# -*- coding: utf-8 -*-
"""Administration : utilisateurs, rôles, contenus, surveillance, audit, sauvegardes."""
from __future__ import annotations

import csv
import io
import json
from datetime import timedelta

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request,
    Response, send_file, url_for,
)
from sqlalchemy import func, or_

from ..extensions import db
from ..models import (
    Announcement, Answer, Attempt, AuditLog, AuthSession, BattleRoom, Category, Exercise,
    Lesson, LessonProgress, Message, Module, Option, PasswordResetRequest, Question, Resource,
    Setting, User, utcnow, ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_USER, ROLE_LABELS,
    STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_DISABLED,
)
from ..security.core import (
    admin_required, can_manage_user, generate_password, generate_username, limiter,
    log_audit, password_errors, password_ok, revoke_all_sessions, revoke_session,
    super_admin_required, valid_username,
)
from .. import maintenance
from ..reports import (
    class_overview, mention as mention_for, note20, student_report as build_student_report,
    student_rows,
)
from ..utils import paginate, save_upload, slugify

bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------------------------------------------------------------------------
# Tableau de bord
# ---------------------------------------------------------------------------
@bp.route("/")
@admin_required
def dashboard():
    now = utcnow()
    week_ago = now - timedelta(days=7)

    stats = {
        "users": User.query.count(),
        "users_active": User.query.filter_by(status=STATUS_ACTIVE).count(),
        "admins": User.query.filter(User.role.in_([ROLE_ADMIN, ROLE_SUPER_ADMIN])).count(),
        "new_users_week": User.query.filter(User.created_at >= week_ago).count(),
        "modules": Module.query.filter_by(status="published").count(),
        "lessons": Lesson.query.count(),
        "exercises": Exercise.query.filter_by(kind="exercise").count(),
        "exams": Exercise.query.filter_by(kind="exam").count(),
        "attempts": Attempt.query.filter_by(status="submitted").count(),
        "eliminated": Attempt.query.filter_by(status="eliminated").count(),
        "messages": Message.query.filter_by(deleted=False).count(),
        "battles": BattleRoom.query.count(),
    }

    avg = db.session.query(func.avg(Attempt.score * 100.0 / func.nullif(Attempt.max_score, 0))).filter(
        Attempt.status == "submitted", Attempt.max_score > 0
    ).scalar()
    stats["average"] = round(avg) if avg else 0

    online_threshold = now - timedelta(seconds=current_app.config.get("PRESENCE_ONLINE_SECONDS", 120))
    stats["online"] = User.query.filter(User.last_seen_at >= online_threshold).count()

    recent_attempts = (
        Attempt.query.order_by(Attempt.started_at.desc()).limit(8).all()
    )
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    pending_requests = PasswordResetRequest.query.filter_by(status="pending").count()
    pending_battles = BattleRoom.query.filter_by(status="pending").count()

    # Notes individuelles sur 20 (super administrateur uniquement)
    individual_notes = []
    if g.user.is_super_admin:
        individual_notes = student_rows(sort="moyenne")

    # Répartition des apprenants par module (progression moyenne)
    modules = Module.query.filter_by(status="published").order_by(Module.order_index).all()
    module_stats = []
    total_learners = max(1, User.query.filter_by(role=ROLE_USER).count())
    for module in modules:
        lesson_ids = [l.id for l in module.published_lessons]
        done = 0
        if lesson_ids:
            done = LessonProgress.query.filter(LessonProgress.lesson_id.in_(lesson_ids)).count()
        possible = total_learners * max(1, len(lesson_ids))
        module_stats.append({
            "module": module,
            "percent": min(100, round(done * 100 / possible)) if possible else 0,
        })

    signups = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).date()
        count = User.query.filter(
            User.created_at >= day, User.created_at < day + timedelta(days=1)
        ).count()
        signups.append({"label": day.strftime("%d/%m"), "value": count})
    max_signup = max([s["value"] for s in signups] + [1])

    return render_template(
        "admin/dashboard.html",
        stats=stats, recent_attempts=recent_attempts, recent_users=recent_users,
        pending_requests=pending_requests, pending_battles=pending_battles,
        module_stats=module_stats, signups=signups, max_signup=max_signup,
        individual_notes=individual_notes, note20=note20, mention_for=mention_for,
    )


@bp.route("/roles")
@super_admin_required
def roles():
    counts = {
        role: User.query.filter_by(role=role).count() for role in (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER)
    }
    return render_template("admin/roles.html", counts=counts)


# ---------------------------------------------------------------------------
# Utilisateurs
# ---------------------------------------------------------------------------
@bp.route("/utilisateurs")
@admin_required
def users():
    q = (request.args.get("q") or "").strip()
    role = request.args.get("role") or ""
    status = request.args.get("status") or ""
    sort = request.args.get("sort") or "recent"
    page = request.args.get("page", type=int) or 1

    query = User.query
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(or_(
            func.lower(User.username).like(like),
            func.lower(User.full_name).like(like),
            func.lower(func.coalesce(User.email, "")).like(like),
        ))
    if role in (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER):
        query = query.filter(User.role == role)
    if status in (STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_DISABLED):
        query = query.filter(User.status == status)

    ordering = {
        "recent": User.created_at.desc(),
        "oldest": User.created_at.asc(),
        "name": User.full_name.asc(),
        "login": User.last_login_at.desc().nullslast(),
    }.get(sort, User.created_at.desc())

    pagination = paginate(query.order_by(ordering), page, per_page=15)
    return render_template(
        "admin/users.html", pagination=pagination, users=pagination.items,
        q=q, role=role, status=status, sort=sort,
    )


def _read_user_form(user: User | None):
    """Valide et applique les champs du formulaire. Retourne (ok, message, utilisateur)."""
    full_name = (request.form.get("full_name") or "").strip()[:160]
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()[:190]
    role = request.form.get("role") or ROLE_USER
    status = request.form.get("status") or STATUS_ACTIVE
    bio = (request.form.get("bio") or "").strip()[:1000]

    if len(full_name) < 2:
        return False, "Le nom complet est obligatoire (2 caractères minimum).", user
    if role not in (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER):
        return False, "Rôle invalide.", user
    if status not in (STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_DISABLED):
        return False, "Statut invalide.", user

    # Un ADMIN ne peut pas créer ni promouvoir des comptes privilégiés
    if not g.user.is_super_admin and role != ROLE_USER:
        return False, "Seul le super administrateur peut attribuer un rôle administrateur.", user
    if user and user.role == ROLE_SUPER_ADMIN and not g.user.is_super_admin:
        return False, "Action réservée au super administrateur.", user

    if user is None:
        if not username:
            username = generate_username(full_name)
        if not valid_username(username):
            return False, "Identifiant invalide : 3 à 32 caractères (lettres, chiffres, . _ -).", user
        if User.query.filter(func.lower(User.username) == username.lower()).first():
            return False, "Cet identifiant est déjà utilisé.", user

    if email and ("@" not in email or "." not in email.split("@")[-1]):
        return False, "Adresse e-mail invalide.", user
    if email:
        clash = User.query.filter(func.lower(User.email) == email)
        if user:
            clash = clash.filter(User.id != user.id)
        if clash.first():
            return False, "Cette adresse e-mail est déjà utilisée.", user

    if user is None:
        user = User(username=username.lower(), full_name=full_name, role=role, status=status)
        db.session.add(user)
    user.full_name = full_name
    user.email = email or None
    user.role = role
    user.status = status
    user.bio = bio
    if user.id is None or not user.password_hash:
        temp_password = generate_password()
        user.set_password(temp_password)
        user.must_change_password = True
        request._tic_temp_password = temp_password  # transmis une seule fois au template
    return True, "", user


@bp.route("/utilisateurs/nouveau", methods=["GET", "POST"])
@admin_required
def user_new():
    error = None
    created = None
    form = {k: request.form.get(k, "") for k in ("full_name", "username", "email", "role", "status", "bio")}

    if request.method == "POST":
        # Mot de passe : généré ou imposé par l'administrateur
        requested_password = request.form.get("password") or ""
        if requested_password and not password_ok(requested_password):
            error = "Mot de passe trop faible : " + ", ".join(password_errors(requested_password)) + "."
        else:
            ok, message, user = _read_user_form(None)
            if not ok:
                db.session.rollback()
                error = message
            else:
                if requested_password:
                    user.set_password(requested_password)
                    user.must_change_password = request.form.get("must_change") == "1"
                temp = getattr(request, "_tic_temp_password", None)
                db.session.commit()
                log_audit("user.created", target=user.username, details=f"rôle={user.role}")
                created = {
                    "username": user.username,
                    "password": requested_password or temp,
                    "full_name": user.full_name,
                    "role": user.role,
                }

    return render_template(
        "admin/user_form.html", mode="create", user=None, error=error, form=form, created=created
    )


@bp.route("/utilisateurs/<int:user_id>")
@admin_required
def user_detail(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    attempts = (
        Attempt.query.filter_by(user_id=user.id).order_by(Attempt.started_at.desc()).limit(10).all()
    )
    sessions = (
        AuthSession.query.filter_by(user_id=user.id)
        .order_by(AuthSession.created_at.desc()).limit(10).all()
    )
    lessons_done = LessonProgress.query.filter_by(user_id=user.id).count()
    return render_template(
        "admin/user_detail.html", user=user, attempts=attempts,
        sessions=sessions, lessons_done=lessons_done, temp_password=None,
    )


@bp.route("/utilisateurs/<int:user_id>/modifier", methods=["GET", "POST"])
@admin_required
def user_edit(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    if not can_manage_user(g.user, user):
        abort(403)

    error = None
    if request.method == "POST":
        ok, message, _ = _read_user_form(user)
        if not ok:
            db.session.rollback()
            error = message
        else:
            db.session.commit()
            log_audit("user.updated", target=user.username, details=f"rôle={user.role}, statut={user.status}")
            flash("Utilisateur mis à jour.", "success")
            return redirect(url_for("admin.user_detail", user_id=user.id))

    return render_template(
        "admin/user_form.html", mode="edit", user=user, error=error,
        form={k: (getattr(user, k) or "") for k in ("full_name", "username", "email", "role", "status", "bio")},
        created=None,
    )


@bp.route("/utilisateurs/<int:user_id>/statut", methods=["POST"])
@admin_required
def user_status(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    if not can_manage_user(g.user, user):
        abort(403)

    action = request.form.get("action")
    mapping = {
        "suspend": (STATUS_SUSPENDED, "Compte suspendu."),
        "activate": (STATUS_ACTIVE, "Compte réactivé."),
        "disable": (STATUS_DISABLED, "Compte désactivé."),
    }
    if action not in mapping:
        abort(400)

    new_status, message = mapping[action]
    if user.id == g.user.id and action != "activate":
        flash("Vous ne pouvez pas désactiver votre propre compte.", "danger")
        return redirect(url_for("admin.user_detail", user_id=user.id))

    user.status = new_status
    db.session.commit()
    if new_status != STATUS_ACTIVE:
        revoke_all_sessions(user)
    log_audit(f"user.{action}", target=user.username)
    flash(message, "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@bp.route("/utilisateurs/<int:user_id>/reinitialiser", methods=["POST"])
@admin_required
def user_reset_password(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    if not can_manage_user(g.user, user):
        abort(403)

    temp = generate_password()
    user.set_password(temp)
    user.must_change_password = True
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
    revoke_all_sessions(user)
    log_audit("user.password_reset", target=user.username)

    attempts = Attempt.query.filter_by(user_id=user.id).order_by(Attempt.started_at.desc()).limit(10).all()
    sessions = AuthSession.query.filter_by(user_id=user.id).order_by(AuthSession.created_at.desc()).limit(10).all()
    lessons_done = LessonProgress.query.filter_by(user_id=user.id).count()
    return render_template(
        "admin/user_detail.html", user=user, attempts=attempts, sessions=sessions,
        lessons_done=lessons_done, temp_password=temp,
    )


@bp.route("/utilisateurs/<int:user_id>/revoquer-sessions", methods=["POST"])
@admin_required
def user_revoke_sessions(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    if not can_manage_user(g.user, user):
        abort(403)
    count = revoke_all_sessions(user)
    log_audit("user.sessions_revoked", target=user.username, details=f"{count} session(s)")
    flash(f"{count} session(s) révoquée(s).", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@bp.route("/utilisateurs/<int:user_id>/supprimer", methods=["POST"])
@admin_required
def user_delete(user_id: int):
    user = db.session.get(User, user_id) or abort(404)
    if not can_manage_user(g.user, user):
        abort(403)
    if user.id == g.user.id:
        abort(403)
    if request.form.get("confirm") != user.username:
        flash("La confirmation a échoué : saisissez exactement l'identifiant pour supprimer.", "danger")
        return redirect(url_for("admin.user_detail", user_id=user.id))

    username = user.username
    # Politique de conservation : anonymisation des traces d'audit, suppression des données personnelles
    AuditLog.query.filter_by(actor_id=user.id).update({"actor_id": None})
    Message.query.filter_by(sender_id=user.id).update({"body": "[message supprimé]", "deleted": True})
    db.session.delete(user)
    db.session.commit()
    log_audit("user.deleted", target=username, details="suppression définitive (RGPD)")
    flash(f"Le compte « {username} » a été supprimé.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/utilisateurs/export.csv")
@admin_required
def users_export():
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["identifiant", "nom_complet", "email", "role", "statut",
                     "cree_le", "derniere_connexion", "mot_de_passe_a_changer"])
    for user in User.query.order_by(User.created_at).all():
        writer.writerow([
            user.username, user.full_name, user.email or "", user.role, user.status,
            user.created_at.strftime("%Y-%m-%d %H:%M"), 
            user.last_login_at.strftime("%Y-%m-%d %H:%M") if user.last_login_at else "",
            "oui" if user.must_change_password else "non",
        ])
    log_audit("users.exported")
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=utilisateurs-ticmaster.csv"},
    )


# ---------------------------------------------------------------------------
# Contenus : modules, leçons, ressources
# ---------------------------------------------------------------------------
@bp.route("/modules")
@admin_required
def modules():
    q = (request.args.get("q") or "").strip()
    status = request.args.get("status") or ""
    query = Module.query
    if q:
        query = query.filter(func.lower(Module.title).like(f"%{q.lower()}%"))
    if status in ("draft", "published", "archived"):
        query = query.filter(Module.status == status)
    items = query.order_by(Module.order_index).all()
    return render_template(
        "admin/modules.html", modules=items, q=q, status=status,
        categories=Category.query.order_by(Category.order_index).all(),
    )


@bp.route("/modules/nouveau", methods=["POST"])
@admin_required
def module_new():
    title = (request.form.get("title") or "").strip()[:190]
    if len(title) < 3:
        flash("Le titre du module est obligatoire.", "danger")
        return redirect(url_for("admin.modules"))

    module = Module(
        title=title,
        slug=slugify(title),
        summary=(request.form.get("summary") or "").strip()[:500],
        category_id=request.form.get("category_id", type=int),
        order_index=request.form.get("order_index", type=int) or (Module.query.count() + 1),
        icon=(request.form.get("icon") or "book-open")[:40],
        created_by=g.user.id,
    )
    db.session.add(module)
    db.session.commit()
    log_audit("module.created", target=module.slug)
    flash("Module créé. Ajoutez maintenant vos leçons.", "success")
    return redirect(url_for("admin.module_edit", module_id=module.id))


@bp.route("/modules/<int:module_id>/modifier", methods=["GET", "POST"])
@admin_required
def module_edit(module_id: int):
    module = db.session.get(Module, module_id) or abort(404)
    error = None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()[:190]
        if len(title) < 3:
            error = "Le titre du module est obligatoire."
        else:
            module.title = title
            module.summary = (request.form.get("summary") or "").strip()[:500]
            module.description = (request.form.get("description") or "").strip()
            module.icon = (request.form.get("icon") or "book-open")[:40]
            module.level = (request.form.get("level") or "débutant")[:20]
            module.status = request.form.get("status") if request.form.get("status") in ("draft", "published", "archived") else module.status
            module.order_index = request.form.get("order_index", type=int) or module.order_index
            module.estimated_minutes = request.form.get("estimated_minutes", type=int) or module.estimated_minutes
            category_id = request.form.get("category_id", type=int)
            module.category_id = category_id or None

            if "image" in request.files and request.files["image"].filename:
                stored, original, size = save_upload(request.files["image"])
                if stored:
                    module.image_url = f"/fichiers/{stored}"
                else:
                    error = "Image refusée : format non autorisé."

            if not error:
                db.session.commit()
                log_audit("module.updated", target=module.slug)
                flash("Module enregistré.", "success")
                return redirect(url_for("admin.module_edit", module_id=module.id))

    return render_template(
        "admin/module_edit.html", module=module, error=error,
        categories=Category.query.order_by(Category.order_index).all(),
    )


@bp.route("/modules/<int:module_id>/statut", methods=["POST"])
@admin_required
def module_status(module_id: int):
    module = db.session.get(Module, module_id) or abort(404)
    new = request.form.get("status")
    if new in ("draft", "published", "archived"):
        module.status = new
        db.session.commit()
        log_audit("module.status", target=module.slug, details=new)
        flash("Statut du module mis à jour.", "success")
    return redirect(url_for("admin.modules"))


@bp.route("/modules/<int:module_id>/supprimer", methods=["POST"])
@admin_required
def module_delete(module_id: int):
    module = db.session.get(Module, module_id) or abort(404)
    slug = module.slug
    db.session.delete(module)
    db.session.commit()
    log_audit("module.deleted", target=slug)
    flash("Module supprimé.", "success")
    return redirect(url_for("admin.modules"))


@bp.route("/modules/<int:module_id>/lecons/nouvelle", methods=["POST"])
@admin_required
def lesson_new(module_id: int):
    module = db.session.get(Module, module_id) or abort(404)
    title = (request.form.get("title") or "").strip()[:190]
    if len(title) < 3:
        flash("Le titre de la leçon est obligatoire.", "danger")
        return redirect(url_for("admin.module_edit", module_id=module.id))

    lesson = Lesson(
        module_id=module.id,
        title=title,
        content=(request.form.get("content") or "").strip(),
        order_index=request.form.get("order_index", type=int) or (len(module.lessons) + 1),
        estimated_minutes=request.form.get("estimated_minutes", type=int) or 10,
        published=request.form.get("published") == "1",
    )
    db.session.add(lesson)
    db.session.commit()
    log_audit("lesson.created", target=f"{module.slug}#{lesson.id}")
    flash("Leçon ajoutée.", "success")
    return redirect(url_for("admin.lesson_edit", lesson_id=lesson.id))


@bp.route("/lecons/<int:lesson_id>/modifier", methods=["GET", "POST"])
@admin_required
def lesson_edit(lesson_id: int):
    lesson = db.session.get(Lesson, lesson_id) or abort(404)
    error = None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()[:190]
        if len(title) < 3:
            error = "Le titre est obligatoire."
        else:
            lesson.title = title
            lesson.content = (request.form.get("content") or "").strip()
            lesson.estimated_minutes = request.form.get("estimated_minutes", type=int) or 10
            lesson.order_index = request.form.get("order_index", type=int) or lesson.order_index
            lesson.published = request.form.get("published") == "1"
            lesson.video_url = (request.form.get("video_url") or "").strip()[:400]
            lesson.document_url = (request.form.get("document_url") or "").strip()[:400]

            image = request.files.get("image")
            if image and image.filename:
                stored, _, _ = save_upload(image)
                if stored:
                    lesson.image_url = f"/fichiers/{stored}"
                else:
                    error = "Image refusée : format non autorisé."

            if not error:
                db.session.commit()
                log_audit("lesson.updated", target=f"{lesson.module.slug}#{lesson.id}")
                flash("Leçon enregistrée.", "success")
                return redirect(url_for("admin.lesson_edit", lesson_id=lesson.id))

    return render_template("admin/lesson_edit.html", lesson=lesson, error=error)


@bp.route("/lecons/<int:lesson_id>/supprimer", methods=["POST"])
@admin_required
def lesson_delete(lesson_id: int):
    lesson = db.session.get(Lesson, lesson_id) or abort(404)
    module_id = lesson.module_id
    db.session.delete(lesson)
    db.session.commit()
    log_audit("lesson.deleted", target=str(lesson_id))
    flash("Leçon supprimée.", "success")
    return redirect(url_for("admin.module_edit", module_id=module_id))


@bp.route("/modules/<int:module_id>/ressources", methods=["POST"])
@admin_required
def resource_new(module_id: int):
    module = db.session.get(Module, module_id) or abort(404)
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Sélectionnez un fichier.", "danger")
        return redirect(url_for("admin.module_edit", module_id=module.id))

    stored, original, size = save_upload(file)
    if not stored:
        flash("Format de fichier non autorisé.", "danger")
        return redirect(url_for("admin.module_edit", module_id=module.id))

    db.session.add(Resource(
        module_id=module.id,
        title=(request.form.get("title") or original)[:190],
        filename=stored,
        size=size,
    ))
    db.session.commit()
    log_audit("resource.uploaded", target=f"{module.slug}:{original}")
    flash("Ressource ajoutée.", "success")
    return redirect(url_for("admin.module_edit", module_id=module.id))


@bp.route("/ressources/<int:resource_id>/supprimer", methods=["POST"])
@admin_required
def resource_delete(resource_id: int):
    resource = db.session.get(Resource, resource_id) or abort(404)
    module_id = resource.module_id
    filename = resource.filename
    db.session.delete(resource)
    db.session.commit()

    try:
        from pathlib import Path
        (Path(current_app.config["UPLOAD_FOLDER"]) / filename).unlink(missing_ok=True)
    except Exception:  # pragma: no cover
        pass

    log_audit("resource.deleted", target=filename)
    flash("Ressource supprimée.", "success")
    return redirect(url_for("admin.module_edit", module_id=module_id))


# ---------------------------------------------------------------------------
# Exercices et questions
# ---------------------------------------------------------------------------
@bp.route("/exercices")
@admin_required
def exercises():
    kind = request.args.get("kind") or ""
    query = Exercise.query
    if kind in ("exercise", "exam"):
        query = query.filter(Exercise.kind == kind)
    items = query.order_by(Exercise.kind, Exercise.id).all()
    return render_template("admin/exercises.html", exercises=items, kind=kind,
                           modules=Module.query.order_by(Module.order_index).all())


@bp.route("/exercices/nouveau", methods=["POST"])
@admin_required
def exercise_new():
    title = (request.form.get("title") or "").strip()[:190]
    if len(title) < 3:
        flash("Le titre est obligatoire.", "danger")
        return redirect(url_for("admin.exercises"))

    exercise = Exercise(
        title=title,
        description=(request.form.get("description") or "").strip(),
        module_id=request.form.get("module_id", type=int),
        kind="exam" if request.form.get("kind") == "exam" else "exercise",
        term=(request.form.get("term") or "")[:30],
        duration_minutes=request.form.get("duration_minutes", type=int) or 20,
        pass_score=request.form.get("pass_score", type=int) or 50,
        max_tab_violations=1,
        created_by=g.user.id,
    )
    db.session.add(exercise)
    db.session.commit()
    log_audit("exercise.created", target=f"{exercise.kind}#{exercise.id}")
    flash("Exercice créé. Ajoutez maintenant les questions.", "success")
    return redirect(url_for("admin.exercise_edit", exercise_id=exercise.id))


@bp.route("/exercices/<int:exercise_id>/modifier", methods=["GET", "POST"])
@admin_required
def exercise_edit(exercise_id: int):
    exercise = db.session.get(Exercise, exercise_id) or abort(404)
    error = None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()[:190]
        if len(title) < 3:
            error = "Le titre est obligatoire."
        else:
            exercise.title = title
            exercise.description = (request.form.get("description") or "").strip()
            exercise.module_id = request.form.get("module_id", type=int)
            exercise.kind = "exam" if request.form.get("kind") == "exam" else "exercise"
            exercise.duration_minutes = request.form.get("duration_minutes", type=int) or 20
            exercise.pass_score = request.form.get("pass_score", type=int) or 50
            exercise.published = request.form.get("published") == "1"
            if exercise.kind == "exam":
                exercise.max_tab_violations = 1
            db.session.commit()
            log_audit("exercise.updated", target=f"{exercise.kind}#{exercise.id}")
            flash("Exercice enregistré.", "success")
            return redirect(url_for("admin.exercise_edit", exercise_id=exercise.id))

    return render_template(
        "admin/exercise_edit.html", exercise=exercise, error=error,
        modules=Module.query.order_by(Module.order_index).all(),
    )


@bp.route("/exercices/<int:exercise_id>/supprimer", methods=["POST"])
@admin_required
def exercise_delete(exercise_id: int):
    exercise = db.session.get(Exercise, exercise_id) or abort(404)
    db.session.delete(exercise)
    db.session.commit()
    log_audit("exercise.deleted", target=str(exercise_id))
    flash("Exercice supprimé.", "success")
    return redirect(url_for("admin.exercises"))


@bp.route("/exercices/<int:exercise_id>/questions", methods=["POST"])
@admin_required
def question_new(exercise_id: int):
    exercise = db.session.get(Exercise, exercise_id) or abort(404)
    text = (request.form.get("text") or "").strip()
    options = [(request.form.get(f"option_{i}") or "").strip() for i in range(1, 5)]
    correct_index = request.form.get("correct", type=int)

    if len(text) < 5:
        flash("L'énoncé de la question est trop court.", "danger")
        return redirect(url_for("admin.exercise_edit", exercise_id=exercise.id))
    if sum(1 for o in options if o) < 2:
        flash("Ajoutez au moins deux propositions.", "danger")
        return redirect(url_for("admin.exercise_edit", exercise_id=exercise.id))
    if correct_index is None or not (1 <= correct_index <= 4) or not options[correct_index - 1]:
        flash("Indiquez la bonne réponse.", "danger")
        return redirect(url_for("admin.exercise_edit", exercise_id=exercise.id))

    question = Question(
        exercise_id=exercise.id,
        text=text,
        explanation=(request.form.get("explanation") or "").strip(),
        points=max(1, min(10, request.form.get("points", type=int) or 1)),
        order_index=len(exercise.questions) + 1,
    )
    db.session.add(question)
    db.session.flush()
    for i, option_text in enumerate(options, start=1):
        if option_text:
            db.session.add(Option(
                question_id=question.id, text=option_text[:400],
                is_correct=(i == correct_index), order_index=i,
            ))
    db.session.commit()
    log_audit("question.created", target=f"exercise={exercise.id},question={question.id}")
    flash("Question ajoutée.", "success")
    return redirect(url_for("admin.exercise_edit", exercise_id=exercise.id))


@bp.route("/questions/<int:question_id>/modifier", methods=["POST"])
@admin_required
def question_edit(question_id: int):
    question = db.session.get(Question, question_id) or abort(404)
    text = (request.form.get("text") or "").strip()
    if len(text) >= 5:
        question.text = text
        question.explanation = (request.form.get("explanation") or "").strip()
        question.points = max(1, min(10, request.form.get("points", type=int) or 1))

        correct_index = request.form.get("correct", type=int)
        for i, option in enumerate(question.options, start=1):
            option.text = (request.form.get(f"option_{i}") or option.text).strip()[:400]
            if correct_index:
                option.is_correct = (i == correct_index)
        db.session.commit()
        log_audit("question.updated", target=str(question.id))
        flash("Question mise à jour.", "success")
    else:
        flash("Énoncé trop court.", "danger")
    return redirect(url_for("admin.exercise_edit", exercise_id=question.exercise_id))


@bp.route("/questions/<int:question_id>/supprimer", methods=["POST"])
@admin_required
def question_delete(question_id: int):
    question = db.session.get(Question, question_id) or abort(404)
    exercise_id = question.exercise_id
    db.session.delete(question)
    db.session.commit()
    log_audit("question.deleted", target=str(question_id))
    flash("Question supprimée.", "success")
    return redirect(url_for("admin.exercise_edit", exercise_id=exercise_id))


# ---------------------------------------------------------------------------
# Annonces
# ---------------------------------------------------------------------------
@bp.route("/annonces", methods=["GET", "POST"])
@admin_required
def announcements():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()[:190]
        body = (request.form.get("body") or "").strip()
        if len(title) < 3 or len(body) < 3:
            flash("Titre et contenu obligatoires.", "danger")
        else:
            announcement = Announcement(
                title=title, body=body, published=request.form.get("published") == "1",
                created_by=g.user.id,
            )
            db.session.add(announcement)
            db.session.commit()
            log_audit("announcement.created", target=str(announcement.id))
            flash("Annonce publiée.", "success")
        return redirect(url_for("admin.announcements"))

    items = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template("admin/announcements.html", announcements=items)


@bp.route("/annonces/<int:announcement_id>/modifier", methods=["POST"])
@admin_required
def announcement_edit(announcement_id: int):
    item = db.session.get(Announcement, announcement_id) or abort(404)
    item.title = (request.form.get("title") or item.title).strip()[:190]
    item.body = (request.form.get("body") or item.body).strip()
    item.published = request.form.get("published") == "1"
    db.session.commit()
    log_audit("announcement.updated", target=str(item.id))
    flash("Annonce mise à jour.", "success")
    return redirect(url_for("admin.announcements"))


@bp.route("/annonces/<int:announcement_id>/supprimer", methods=["POST"])
@admin_required
def announcement_delete(announcement_id: int):
    item = db.session.get(Announcement, announcement_id) or abort(404)
    db.session.delete(item)
    db.session.commit()
    log_audit("announcement.deleted", target=str(announcement_id))
    flash("Annonce supprimée.", "success")
    return redirect(url_for("admin.announcements"))


# ---------------------------------------------------------------------------
# Surveillance des examens
# ---------------------------------------------------------------------------
@bp.route("/examens")
@admin_required
def exams():
    status = request.args.get("status") or ""
    query = Attempt.query.join(Exercise, Attempt.exercise_id == Exercise.id).filter(Exercise.kind == "exam")
    if status in ("in_progress", "submitted", "eliminated"):
        query = query.filter(Attempt.status == status)
    attempts = query.order_by(Attempt.started_at.desc()).limit(200).all()

    stats = {
        "total": Attempt.query.join(Exercise).filter(Exercise.kind == "exam").count(),
        "eliminated": Attempt.query.join(Exercise).filter(
            Exercise.kind == "exam", Attempt.status == "eliminated").count(),
        "in_progress": Attempt.query.join(Exercise).filter(
            Exercise.kind == "exam", Attempt.status == "in_progress").count(),
    }
    return render_template("admin/exams.html", attempts=attempts, status=status, stats=stats)


@bp.route("/examens/<int:attempt_id>/reaffecter", methods=["POST"])
@super_admin_required
def exam_reassign(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.exercise.kind != "exam":
        abort(400)

    attempt.status = "in_progress"
    attempt.tab_violations = 0
    attempt.elimination_reason = ""
    attempt.started_at = utcnow()
    attempt.submitted_at = None
    attempt.score = 0
    attempt.max_score = sum(q.points or 1 for q in attempt.exercise.questions)
    attempt.last_heartbeat = utcnow()
    attempt.reset_by = g.user.id
    attempt.reset_at = utcnow()
    for answer in list(attempt.answers):
        db.session.delete(answer)
    db.session.commit()

    log_audit("exam.reassigned", target=f"attempt={attempt.id}", details=f"utilisateur={attempt.user.username}")
    flash(f"Examen réaffecté à {attempt.user.full_name or attempt.user.username}. "
          "La sanction ne concernait que cet apprenant.", "success")
    return redirect(url_for("admin.exams"))


# ---------------------------------------------------------------------------
# Messages des utilisateurs (super admin)
# ---------------------------------------------------------------------------
@bp.route("/messages-utilisateurs")
@super_admin_required
def user_messages():
    q = (request.args.get("q") or "").strip()
    room = request.args.get("room") or ""
    query = Message.query
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(func.lower(Message.body).like(like))
    if room:
        query = query.filter(Message.room == room)
    page = request.args.get("page", type=int) or 1
    pagination = paginate(query.order_by(Message.created_at.desc()), page, per_page=25)

    rooms = [r[0] for r in db.session.query(Message.room).distinct().limit(200).all()]
    return render_template(
        "admin/messages.html", pagination=pagination, messages=pagination.items,
        q=q, room=room, rooms=rooms,
    )


@bp.route("/messages-utilisateurs/<int:message_id>/masquer", methods=["POST"])
@super_admin_required
def message_hide(message_id: int):
    msg = db.session.get(Message, message_id) or abort(404)
    msg.deleted = True
    db.session.commit()
    log_audit("message.hidden", target=str(message_id))
    flash("Message masqué pour tous les utilisateurs.", "success")
    return redirect(url_for("admin.user_messages"))


# ---------------------------------------------------------------------------
# Journal d'audit, sessions, demandes
# ---------------------------------------------------------------------------
@bp.route("/journal")
@super_admin_required
def audit():
    action = request.args.get("action") or ""
    q = (request.args.get("q") or "").strip()
    page = request.args.get("page", type=int) or 1

    query = AuditLog.query
    if action:
        query = query.filter(AuditLog.action == action)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(or_(
            func.lower(AuditLog.actor_label).like(like),
            func.lower(AuditLog.target).like(like),
            func.lower(AuditLog.details).like(like),
        ))
    pagination = paginate(query.order_by(AuditLog.created_at.desc()), page, per_page=25)
    actions = [a[0] for a in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()]
    return render_template(
        "admin/audit.html", pagination=pagination, logs=pagination.items,
        action=action, q=q, actions=actions,
    )


@bp.route("/sessions")
@super_admin_required
def sessions():
    rows = (
        AuthSession.query.order_by(AuthSession.last_seen_at.desc()).limit(200).all()
    )
    active = [r for r in rows if r.is_valid]
    return render_template("admin/sessions.html", sessions=rows, active_count=len(active))


@bp.route("/sessions/<int:session_id>/revoquer", methods=["POST"])
@super_admin_required
def session_revoke(session_id: int):
    row = db.session.get(AuthSession, session_id) or abort(404)
    revoke_session(row)
    db.session.commit()
    log_audit("session.revoked", target=str(session_id), details=row.user.username if row.user else "")
    flash("Session révoquée.", "success")
    return redirect(url_for("admin.sessions"))


@bp.route("/demandes")
@super_admin_required
def reset_requests():
    items = PasswordResetRequest.query.order_by(PasswordResetRequest.created_at.desc()).limit(100).all()
    return render_template("admin/reset_requests.html", requests=items)


@bp.route("/demandes/<int:request_id>/approuver", methods=["POST"])
@super_admin_required
def reset_approve(request_id: int):
    row = db.session.get(PasswordResetRequest, request_id) or abort(404)
    if row.status == "pending":
        import hashlib, secrets
        token = secrets.token_urlsafe(32)
        row.status = "approved"
        row.token_hash = hashlib.sha256(token.encode()).hexdigest()
        row.expires_at = utcnow() + timedelta(hours=24)
        row.handled_by = g.user.id
        db.session.commit()
        log_audit("password_reset.approved", target=row.user.username)

        from ..mailer import send_email
        link = url_for("auth.reset_password", token=token, _external=True)
        send_email(row.user.email, "TIC MASTER — lien de réinitialisation",
                   f"Voici votre lien sécurisé (valable 24 h) : {link}")

        items = PasswordResetRequest.query.order_by(PasswordResetRequest.created_at.desc()).limit(100).all()
        return render_template(
            "admin/reset_requests.html", requests=items, reset_link=link,
            reset_for=row.user.username,
        )
    flash("Cette demande a déjà été traitée.", "info")
    return redirect(url_for("admin.reset_requests"))


@bp.route("/demandes/<int:request_id>/rejeter", methods=["POST"])
@super_admin_required
def reset_reject(request_id: int):
    row = db.session.get(PasswordResetRequest, request_id) or abort(404)
    row.status = "rejected"
    row.handled_by = g.user.id
    db.session.commit()
    log_audit("password_reset.rejected", target=row.user.username if row.user else "")
    flash("Demande rejetée.", "success")
    return redirect(url_for("admin.reset_requests"))


# ---------------------------------------------------------------------------
# Validation des battles (solo et groupe) — admin et super admin
# ---------------------------------------------------------------------------
@bp.route("/battles")
@admin_required
def battles():
    """Demandes de battle déposées par les apprenants."""
    pending = (
        BattleRoom.query.filter_by(status="pending")
        .order_by(BattleRoom.created_at.asc())
        .all()
    )
    active = (
        BattleRoom.query.filter(BattleRoom.status.in_(["lobby", "running"]))
        .order_by(BattleRoom.created_at.desc())
        .limit(25)
        .all()
    )
    history = (
        BattleRoom.query.filter(BattleRoom.status.in_(["finished", "refused"]))
        .order_by(BattleRoom.created_at.desc())
        .limit(25)
        .all()
    )
    return render_template("admin/battles.html", pending=pending, active=active, history=history)


@bp.route("/battles/<int:battle_id>/accepter", methods=["POST"])
@admin_required
def battle_accept(battle_id: int):
    room = db.session.get(BattleRoom, battle_id) or abort(404)
    if room.status != "pending":
        flash("Cette demande a déjà été traitée.", "info")
        return redirect(url_for("admin.battles"))
    room.status = "lobby"
    db.session.commit()
    log_audit("battle.accepted", target=room.code, details=f"par={g.user.username}")
    flash(f"Battle « {room.name} » acceptée : les joueurs peuvent démarrer.", "success")
    return redirect(url_for("admin.battles"))


@bp.route("/battles/<int:battle_id>/refuser", methods=["POST"])
@admin_required
def battle_refuse(battle_id: int):
    room = db.session.get(BattleRoom, battle_id) or abort(404)
    if room.status != "pending":
        flash("Cette demande a déjà été traitée.", "info")
        return redirect(url_for("admin.battles"))
    room.status = "refused"
    db.session.commit()
    log_audit("battle.refused", target=room.code, details=f"par={g.user.username}")
    flash(f"Battle « {room.name} » refusée.", "info")
    return redirect(url_for("admin.battles"))


# ---------------------------------------------------------------------------
# Paramètres et sauvegardes
# ---------------------------------------------------------------------------
@bp.route("/parametres", methods=["GET", "POST"])
@super_admin_required
def settings():
    if request.method == "POST":
        section = request.form.get("section", "general")

        if section == "maintenance":
            wanted = request.form.get("maintenance_mode") == "1"
            was_active = maintenance.active()
            message = (request.form.get("maintenance_message") or "").strip()[:600]
            return_at = (request.form.get("maintenance_return_at") or "").strip()[:120]

            if wanted and not was_active:
                maintenance.enable(message, return_at)
                log_audit("maintenance.enabled", details=return_at or "sans heure de retour")
                flash("Mise à jour du site activée : les utilisateurs voient désormais la page d'attente.", "success")
            elif wanted and was_active:
                Setting.set("maintenance_message", message)
                Setting.set("maintenance_return_at", return_at)
                db.session.commit()
                log_audit("maintenance.updated")
                flash("Message de mise à jour actualisé.", "success")
            elif was_active:
                maintenance.disable()
                log_audit("maintenance.disabled")
                flash("Site de nouveau accessible : la mise à jour est terminée.", "success")
            else:
                Setting.set("maintenance_message", message)
                Setting.set("maintenance_return_at", return_at)
                db.session.commit()
                flash("Message de mise à jour enregistré (maintenance inactive).", "info")
            return redirect(url_for("admin.settings", onglet="maintenance"))

        for key in ("site_tagline", "support_email", "welcome_message"):
            if key in request.form:
                Setting.set(key, (request.form.get(key) or "").strip()[:1000])

        # Conservation des données : vide, 0 ou « illimite » = aucune limite
        if "retention_days" in request.form:
            raw = (request.form.get("retention_days") or "").strip().lower()
            raw = raw.replace("é", "e").replace("è", "e")
            if raw in ("", "0", "illimite", "illimitee", "illimité", "infini", "infinity", "none"):
                Setting.set("retention_days", "0")
            else:
                digits = "".join(ch for ch in raw if ch.isdigit())
                Setting.set("retention_days", str(min(int(digits), 36500)) if digits else "0")
        db.session.commit()
        log_audit("settings.updated")
        flash("Paramètres enregistrés.", "success")
        return redirect(url_for("admin.settings", onglet="general"))

    values = {
        "site_tagline": Setting.get("site_tagline", current_app.config.get("SITE_TAGLINE", "")),
        "support_email": Setting.get("support_email", ""),
        "welcome_message": Setting.get("welcome_message", ""),
        "retention_days": Setting.get("retention_days", "0"),
        "maintenance_mode": maintenance.active(),
        "maintenance_message": Setting.get("maintenance_message", ""),
        "maintenance_return_at": Setting.get("maintenance_return_at", ""),
        "maintenance_since": maintenance.state()["since"],
    }
    return render_template(
        "admin/settings.html", values=values, onglet=request.args.get("onglet", "general")
    )


@bp.route("/maintenance/basculer", methods=["POST"])
@super_admin_required
def maintenance_toggle():
    """Interrupteur rapide (bandeau d'alerte de l'administration)."""
    if maintenance.active():
        maintenance.disable()
        log_audit("maintenance.disabled", details="bascule rapide")
        flash("Site de nouveau accessible : la mise à jour est terminée.", "success")
    else:
        message = Setting.get("maintenance_message", "")
        return_at = Setting.get("maintenance_return_at", "")
        maintenance.enable(message, return_at)
        log_audit("maintenance.enabled", details="bascule rapide")
        flash("Mise à jour activée : les utilisateurs voient la page d'attente.", "success")
    target = request.form.get("next") or url_for("admin.settings", onglet="maintenance")
    return redirect(target)


@bp.route("/apercu-maintenance")
@super_admin_required
def maintenance_preview():
    """Aperçu de la page d'attente, même quand la maintenance est inactive."""
    st = maintenance.state()
    info = {
        "active": True,
        "message": st["message"],
        "return_at": st["return_at"],
        "since": st["since"],
    }
    return render_template("errors/maintenance.html", info=info, requested_path="/")


# ---------------------------------------------------------------------------
# Scolarité : notes et statistiques (super administrateur)
# ---------------------------------------------------------------------------
@bp.route("/notes")
@super_admin_required
def grades():
    q = (request.args.get("q") or "").strip()
    sort = request.args.get("tri", "moyenne")
    rows = student_rows(search=q, sort=sort)
    graded = [r for r in rows if r["average"] is not None]

    summary = {
        "students": len(rows),
        "graded": len(graded),
        "average": round(sum(r["average"] for r in graded) / len(graded), 1) if graded else 0,
        "best": graded[0] if graded else None,
        "success_rate": round(sum(1 for r in graded if r["average"] >= 50) * 100 / len(graded)) if graded else 0,
        "at_risk": sum(1 for r in graded if r["average"] < 50),
        "no_activity": sum(1 for r in rows if r["attempts"] == 0),
        "eliminated": sum(r["eliminated"] for r in rows),
    }
    summary["note"] = note20(summary["average"])

    return render_template(
        "admin/grades.html", rows=rows, q=q, sort=sort, summary=summary,
        mention_for=mention_for, note20=note20,
    )


@bp.route("/notes/export.csv")
@super_admin_required
def grades_export():
    rows = student_rows(sort="moyenne")
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "rang", "identifiant", "nom_complet", "statut", "progression_%", "exercices",
        "moyenne_exercices_%", "examens", "moyenne_examens_%", "moyenne_generale_%",
        "note_sur_20", "mention", "eliminations", "derniere_activite",
    ])
    for row in rows:
        label = mention_for(row["note"])[0] if row["note"] is not None else "Non noté"
        writer.writerow([
            row["rank"] or "", row["user"].username, row["user"].full_name or "",
            row["user"].status, row["progress"], row["exercises"],
            row["avg_exos"] if row["avg_exos"] is not None else "",
            row["exams"], row["avg_exams"] if row["avg_exams"] is not None else "",
            row["average"] if row["average"] is not None else "",
            row["note"] if row["note"] is not None else "",
            label, row["eliminated"],
            row["last_activity"].strftime("%Y-%m-%d %H:%M") if row["last_activity"] else "",
        ])
    log_audit("grades.exported", details=f"{len(rows)} apprenants")
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=ticmaster-notes.csv"},
    )


@bp.route("/notes/<int:user_id>")
@super_admin_required
def student_sheet(user_id: int):
    report = build_student_report(user_id)
    if report is None:
        abort(404)
    log_audit("grades.viewed", target=report["user"].username)
    return render_template(
        "admin/student_sheet.html", r=report, mention_for=mention_for, note20=note20,
    )


@bp.route("/statistiques")
@super_admin_required
def statistics():
    overview = class_overview()
    return render_template("admin/statistics.html", o=overview, mention_for=mention_for)


@bp.route("/sauvegardes")
@super_admin_required
def backups():
    import os
    from pathlib import Path
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    db_url = uri.split("@")[-1] if "@" in uri else uri
    uploads = Path(current_app.config["UPLOAD_FOLDER"])
    files = list(uploads.glob("*")) if uploads.exists() else []
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    db_size = None
    if uri.startswith("sqlite"):
        path = uri.replace("sqlite:///", "")
        if os.path.exists(path):
            db_size = os.path.getsize(path)

    return render_template(
        "admin/backups.html", db_url=db_url, db_size=db_size,
        upload_count=len(files), upload_size=total_size,
    )


@bp.route("/sauvegardes/export.json")
@super_admin_required
def backup_export():
    """Export JSON des données (hors secrets) — sauvegarde portable."""
    users = [{
        "username": u.username, "full_name": u.full_name, "email": u.email,
        "role": u.role, "status": u.status, "created_at": u.created_at.isoformat(),
    } for u in User.query.all()]

    modules = []
    for m in Module.query.order_by(Module.order_index).all():
        modules.append({
            "title": m.title, "slug": m.slug, "summary": m.summary, "status": m.status,
            "lessons": [{"title": l.title, "content": l.content, "published": l.published} for l in m.lessons],
            "exercises": [{
                "title": e.title, "kind": e.kind, "term": e.term,
                "questions": [{
                    "text": q.text,
                    "options": [{"text": o.text, "correct": o.is_correct} for o in q.options],
                    "explanation": q.explanation,
                } for q in e.questions],
            } for e in m.exercises],
        })

    payload = {
        "app": "TIC MASTER",
        "exported_at": utcnow().isoformat(),
        "users": users,
        "modules": modules,
        "announcements": [{"title": a.title, "body": a.body} for a in Announcement.query.all()],
    }
    log_audit("backup.exported")
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=ticmaster-sauvegarde.json"},
    )
