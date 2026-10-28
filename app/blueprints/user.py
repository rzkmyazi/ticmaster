# -*- coding: utf-8 -*-
"""Espace apprenant : tableau de bord, profil, présence, annonces, historique."""
from __future__ import annotations

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Announcement, Attempt, Exercise, Lesson, LessonProgress, Module, User,
    utcnow, STATUS_ACTIVE,
)
from ..security.core import login_required, log_audit

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
    if user.is_super_admin:
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

    return render_template(
        "user/profile.html",
        user=user,
        error=error,
        stats={
            "attempts": len(submitted),
            "passed": passed,
            "best": best,
            "progress": _global_progress(user.id),
        },
    )
