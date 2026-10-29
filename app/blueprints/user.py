# -*- coding: utf-8 -*-
"""Espace apprenant : tableau de bord, profil, présence, annonces, historique."""
from __future__ import annotations

from pathlib import Path

from flask import (
    Blueprint, abort, current_app, flash, g, make_response, redirect, render_template,
    request, send_from_directory, url_for,
)
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Announcement, Attempt, Exercise, Lesson, LessonProgress, Module, User,
    utcnow, STATUS_ACTIVE,
)
from ..security.core import login_required, log_audit
from ..utils import IMAGE_EXTENSIONS, is_real_image, save_upload

bp = Blueprint("user", __name__)


def module_progress(user_id: int, module: Module) -> dict:
    """Progression d'un utilisateur sur un module (leçons publiées uniquement)."""
    lessons = module.published_lessons
    total = len(lessons)
    if not total:
        return {"done": 0, "total": 0, "percent": 0}
    done_ids = {
        p.lesson_id
        for p in LessonProgress.query.filter(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id.in_([l.id for l in lessons]),
        ).all()
    }
    done = len(done_ids)
    return {"done": done, "total": total, "percent": round(done * 100 / total), "done_ids": done_ids}


def _global_progress(user_id: int) -> dict:
    modules = Module.query.filter_by(status="published").all()
    total = sum(len(m.published_lessons) for m in modules)
    lesson_ids = [l.id for m in modules for l in m.published_lessons]
    done = 0
    if lesson_ids:
        done = LessonProgress.query.filter(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id.in_(lesson_ids),
        ).count()
    return {
        "done": done,
        "total": total,
        "percent": round(done * 100 / total) if total else 0,
        "modules_total": len(modules),
    }


@bp.route("/espace")
@login_required
def dashboard():
    user = g.user
    if user.is_admin:
        # Le personnel enseigne : pas de tableau de bord d'élève.
        return redirect(url_for("admin.dashboard"))
    global_progress = _global_progress(user.id)

    # Modules en cours (leçon suivante à travailler)
    continue_list = []
    for module in Module.query.filter_by(status="published").order_by(Module.order_index).all():
        prog = module_progress(user.id, module)
        if prog["total"] and prog["done"] < prog["total"]:
            next_lesson = next(
                (l for l in module.published_lessons if l.id not in prog["done_ids"]), None
            )
            continue_list.append({"module": module, "progress": prog, "next_lesson": next_lesson})
    continue_list = continue_list[:4]

    attempts = (
        Attempt.query.filter_by(user_id=user.id)
        .order_by(Attempt.started_at.desc())
        .limit(6)
        .all()
    )
    submitted = [a for a in Attempt.query.filter_by(user_id=user.id, status="submitted").all()]
    average = round(sum(a.percentage for a in submitted) / len(submitted)) if submitted else 0
    completed_modules = sum(
        1 for m in Module.query.filter_by(status="published").all()
        if (p := module_progress(user.id, m))["total"] and p["done"] == p["total"]
    )

    stats = {
        "progress": global_progress,
        "average": average,
        "attempts": len(submitted),
        "exams": Exercise.query.filter_by(kind="exam", published=True).count(),
        "completed_modules": completed_modules,
    }

    announcements = (
        Announcement.query.filter_by(published=True).order_by(Announcement.created_at.desc()).limit(3).all()
    )
    online_count = User.query.filter(
        User.status == STATUS_ACTIVE,
        User.last_seen_at >= utcnow().replace(microsecond=0) - __import__("datetime").timedelta(
            seconds=current_app.config.get("PRESENCE_ONLINE_SECONDS", 120)
        ),
    ).count()

    next_exam = (
        Exercise.query.filter_by(kind="exam", published=True).order_by(Exercise.id.asc()).first()
    )

    return render_template(
        "user/dashboard.html",
        stats=stats,
        continue_list=continue_list,
        attempts=attempts,
        announcements=announcements,
        online_count=online_count,
        next_exam=next_exam,
    )


@bp.route("/utilisateurs-en-ligne")
@login_required
def online_users():
    window = current_app.config.get("PRESENCE_ONLINE_SECONDS", 120)
    threshold = utcnow() - __import__("datetime").timedelta(seconds=window)
    q = (request.args.get("q") or "").strip()

    query = User.query.filter(User.status == STATUS_ACTIVE)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            db.or_(func.lower(User.username).like(like), func.lower(User.full_name).like(like))
        )
    people = query.order_by(User.last_seen_at.desc().nullslast()).limit(200).all()
    online = [p for p in people if p.last_seen_at and p.last_seen_at >= threshold]
    offline = [p for p in people if not (p.last_seen_at and p.last_seen_at >= threshold)]

    return render_template(
        "user/online_users.html", online=online, offline=offline, q=q, window=window
    )


@bp.route("/annonces")
@login_required
def announcements():
    items = Announcement.query.filter_by(published=True).order_by(Announcement.created_at.desc()).all()
    return render_template("user/announcements.html", items=items)


@bp.route("/historique")
@login_required
def history():
    kind = request.args.get("type") or ""
    query = Attempt.query.filter_by(user_id=g.user.id)
    if kind in ("exercise", "exam"):
        query = query.join(Exercise, Attempt.exercise_id == Exercise.id).filter(Exercise.kind == kind)
    attempts = query.order_by(Attempt.started_at.desc()).limit(200).all()

    logs = []
    return render_template("user/history.html", attempts=attempts, kind=kind, logs=logs)


def _delete_avatar_file(user) -> None:
    """Supprime le fichier de la photo de profil (sans toucher au reste)."""
    name = (user.avatar_filename or "").strip()
    if not name:
        return
    try:
        (Path(current_app.config["UPLOAD_FOLDER"]) / name).unlink(missing_ok=True)
    except OSError:
        pass
    user.avatar_filename = ""
    user.avatar_data = None


@bp.route("/mon-profil/photo", methods=["POST"])
@login_required
def avatar_upload():
    """Change la photo de profil depuis la galerie du téléphone."""
    user = g.user

    if request.form.get("action") == "remove":
        _delete_avatar_file(user)
        db.session.commit()
        log_audit("avatar.removed", target=user.username)
        flash("Photo de profil supprimée.", "info")
        return redirect(url_for("user.profile") + "#infos")

    upload = request.files.get("photo")
    if not upload or not upload.filename:
        flash("Choisissez une image dans votre galerie.", "danger")
        return redirect(url_for("user.profile") + "#infos")

    name = upload.filename
    ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
    if ext not in IMAGE_EXTENSIONS:
        flash("Format non pris en charge : utilisez une image PNG, JPG, GIF ou WEBP.", "danger")
        return redirect(url_for("user.profile") + "#infos")
    if not is_real_image(upload.stream):
        flash("Ce fichier n'est pas une image valide.", "danger")
        return redirect(url_for("user.profile") + "#infos")

    stored, original, size = save_upload(upload)
    if not stored:
        flash("L'envoi de la photo a échoué.", "danger")
        return redirect(url_for("user.profile") + "#infos")

    # Copie en base : sur un hébergeur au disque éphémère (Render), la photo
    # survivrait sinon quelques minutes seulement.
    octets = b""
    try:
        octets = (Path(current_app.config["UPLOAD_FOLDER"]) / stored).read_bytes()
    except OSError:
        octets = b""

    _delete_avatar_file(user)
    user.avatar_filename = stored
    user.avatar_data = octets or None
    db.session.commit()
    log_audit("avatar.updated", target=user.username, details=f"{original} ({size} octets)")
    flash("Photo de profil mise à jour.", "success")
    return redirect(url_for("user.profile") + "#infos")


_AVATAR_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                 "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"}


def _initiales_svg(user) -> str:
    """Photo par défaut : les initiales, aux couleurs du compte (aucune image cassée)."""
    lettres = (user.initials or "?")[:2]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
        f'<rect width="64" height="64" rx="18" fill="{user.avatar_color or "#22d3ee"}"/>'
        '<text x="32" y="41" font-family="Inter,Segoe UI,sans-serif" font-size="26" '
        f'font-weight="700" fill="#04121f" text-anchor="middle">{lettres}</text></svg>'
    )


@bp.route("/avatar/<path:filename>")
@login_required
def avatar(filename: str):
    """Sert une photo de profil (authentification obligatoire)."""
    if "/" in filename or "\\" in filename or filename.startswith("."):
        abort(404)
    user = User.query.filter_by(avatar_filename=filename).first()
    if user is None:
        abort(404)

    dossier = Path(current_app.config["UPLOAD_FOLDER"])
    if (dossier / filename).exists():
        return send_from_directory(dossier, filename, as_attachment=False)

    # Fichier absent du disque (redéploiement) : la copie en base prend le relais
    if user.avatar_data:
        ext = filename.rsplit(".", 1)[-1].lower()
        response = make_response(user.avatar_data)
        response.headers["Content-Type"] = _AVATAR_TYPES.get(ext, "application/octet-stream")
        response.headers["Cache-Control"] = "private, max-age=86400"
        return response

    # Plus d'image du tout : initiales dessinées, jamais d'image cassée
    response = make_response(_initiales_svg(user))
    response.headers["Content-Type"] = "image/svg+xml"
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@bp.route("/mon-profil", methods=["GET", "POST"])
@login_required
def profile():
    user = g.user
    error = None
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()[:160]
        email = (request.form.get("email") or "").strip().lower()[:190]
        bio = (request.form.get("bio") or "").strip()[:1000]

        if len(full_name) < 2:
            error = "Le nom complet doit contenir au moins 2 caractères."
        elif email and ("@" not in email or "." not in email.split("@")[-1]):
            error = "L'adresse e-mail n'est pas valide."
        elif email and User.query.filter(User.email == email, User.id != user.id).first():
            error = "Cette adresse e-mail est déjà utilisée par un autre compte."
        else:
            user.full_name = full_name
            user.email = email or None
            user.bio = bio
            db.session.commit()
            log_audit("profile.updated", target=user.username)
            flash("Profil mis à jour.", "success")
            return redirect(url_for("user.profile"))

    # Statistiques personnelles
    submitted = Attempt.query.filter_by(user_id=user.id, status="submitted").all()
    passed = sum(1 for a in submitted if a.passed)
    best = max([a.percentage for a in submitted], default=0)

    # Fil d'actualité du profil (les 30 dernières publications)
    from ..models import Post

    posts = (
        Post.query.filter_by(deleted=False)
        .order_by(Post.created_at.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "user/profile.html",
        user=user,
        posts=posts,
        error=error,
        stats={
            "attempts": len(submitted),
            "passed": passed,
            "best": best,
            "progress": _global_progress(user.id),
        },
    )
