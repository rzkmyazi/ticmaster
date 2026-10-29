# -*- coding: utf-8 -*-
"""Parcours pédagogique : catalogue, leçons, exercices, résultats, ressources."""
from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request,
    send_from_directory, url_for, jsonify,
)
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Answer, Attempt, Category, Exercise, Lesson, LessonProgress, Module, Option,
    Question, Resource, utcnow,
)
from ..security.core import login_required, log_audit
from .user import module_progress

bp = Blueprint("learning", __name__)


# ---------------------------------------------------------------------------
# Catalogue et leçons
# ---------------------------------------------------------------------------
@bp.route("/cours")
@login_required
def catalog():
    # Un professeur ne suit pas les cours : il les gère.
    if g.user.is_admin:
        flash("Espace professeur : vos cours se gèrent dans « Modules & leçons ».", "info")
        return redirect(url_for("admin.modules"))
    q = (request.args.get("q") or "").strip()
    cat = (request.args.get("cat") or "").strip()

    query = Module.query.filter_by(status="published")
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(db.or_(func.lower(Module.title).like(like),
                                    func.lower(Module.summary).like(like)))
    if cat:
        category = Category.query.filter_by(slug=cat).first()
        if category:
            query = query.filter(Module.category_id == category.id)

    modules = query.order_by(Module.order_index).all()
    progresses = {m.id: module_progress(g.user.id, m) for m in modules}
    categories = Category.query.order_by(Category.order_index).all()

    return render_template(
        "user/catalog.html",
        modules=modules, progresses=progresses, categories=categories, q=q, cat=cat,
    )


@bp.route("/cours/<slug>")
@login_required
def module_detail(slug: str):
    module = Module.query.filter_by(slug=slug).first_or_404()
    if module.status != "published" and not g.user.is_admin:
        abort(404)

    prog = module_progress(g.user.id, module)
    exercises = [e for e in module.exercises if e.published]
    best = {}
    for ex in exercises:
        attempt = (
            Attempt.query.filter_by(user_id=g.user.id, exercise_id=ex.id, status="submitted")
            .order_by(Attempt.score.desc())
            .first()
        )
        best[ex.id] = attempt
    return render_template(
        "user/module.html", module=module, module_progress=prog, exercises=exercises, best=best
    )


@bp.route("/cours/<slug>/lecon/<int:lesson_id>")
@login_required
def lesson(slug: str, lesson_id: int):
    module = Module.query.filter_by(slug=slug).first_or_404()
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson or lesson.module_id != module.id:
        abort(404)
    if not lesson.published and not g.user.is_admin:
        abort(404)

    done = LessonProgress.query.filter_by(user_id=g.user.id, lesson_id=lesson.id).first() is not None
    idx = module.lessons.index(lesson)
    prev_lesson = module.lessons[idx - 1] if idx > 0 else None
    next_lesson = module.lessons[idx + 1] if idx + 1 < len(module.lessons) else None

    return render_template(
        "user/lesson.html",
        module=module, lesson=lesson, module_progress=module_progress(g.user.id, module),
        done=done, prev_lesson=prev_lesson, next_lesson=next_lesson,
    )


@bp.route("/cours/<slug>/lecon/<int:lesson_id>/terminer", methods=["POST"])
@login_required
def complete_lesson(slug: str, lesson_id: int):
    module = Module.query.filter_by(slug=slug).first_or_404()
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson or lesson.module_id != module.id:
        abort(404)

    existing = LessonProgress.query.filter_by(user_id=g.user.id, lesson_id=lesson.id).first()
    if not existing:
        db.session.add(LessonProgress(user_id=g.user.id, lesson_id=lesson.id))
        db.session.commit()
        log_audit("lesson.completed", target=f"{module.slug}/{lesson.id}")

    idx = module.lessons.index(lesson)
    if idx + 1 < len(module.lessons):
        flash("Leçon terminée. Continuez votre progression !", "success")
        return redirect(url_for("learning.lesson", slug=module.slug, lesson_id=module.lessons[idx + 1].id))
    flash("Bravo, vous avez terminé ce module !", "success")
    return redirect(url_for("learning.module_detail", slug=module.slug))


@bp.route("/ressources")
@login_required
def resources():
    modules = Module.query.filter_by(status="published").order_by(Module.order_index).all()
    return render_template("user/resources.html", modules=modules)


@bp.route("/fichiers/<path:filename>")
@login_required
def download(filename: str):
    """Téléchargement authentifié : les fichiers ne sont jamais servis publiquement."""
    if "/" in filename or "\\" in filename or filename.startswith("."):
        abort(404)
    resource = Resource.query.filter_by(filename=filename).first()
    if not resource:
        abort(404)
    log_audit("resource.download", target=filename)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], filename, as_attachment=True,
        download_name=resource.title or filename,
    )


# ---------------------------------------------------------------------------
# Exercices
# ---------------------------------------------------------------------------
@bp.route("/exercices")
@login_required
def exercises():
    # Un professeur ne passe pas d'exercice : il les crée et les corrige.
    if g.user.is_admin:
        flash("Espace professeur : les exercices se gèrent dans l'administration.", "info")
        return redirect(url_for("admin.exercises"))
    items = (
        Exercise.query.filter_by(published=True, kind="exercise")
        .order_by(Exercise.module_id, Exercise.id)
        .all()
    )
    best = {}
    last = {}
    for ex in items:
        submitted = (
            Attempt.query.filter_by(user_id=g.user.id, exercise_id=ex.id, status="submitted")
            .order_by(Attempt.score.desc())
            .all()
        )
        best[ex.id] = submitted[0] if submitted else None
        last[ex.id] = (
            Attempt.query.filter_by(user_id=g.user.id, exercise_id=ex.id)
            .order_by(Attempt.started_at.desc()).first()
        )
    return render_template("user/exercises.html", exercises=items, best=best, last=last)


@bp.route("/exercices/<int:exercise_id>")
@login_required
def exercise_detail(exercise_id: int):
    exercise = db.session.get(Exercise, exercise_id) or abort(404)
    if not exercise.published and not g.user.is_admin:
        abort(404)
    if exercise.kind == "exam":
        return redirect(url_for("exam.index"))

    attempts = (
        Attempt.query.filter_by(user_id=g.user.id, exercise_id=exercise.id)
        .order_by(Attempt.started_at.desc()).limit(10).all()
    )
    return render_template(
        "user/exercise_detail.html", exercise=exercise, attempts=attempts,
        question_count=len(exercise.questions),
    )


def _create_attempt(exercise: Exercise) -> Attempt:
    attempt = Attempt(
        user_id=g.user.id,
        exercise_id=exercise.id,
        status="in_progress",
        max_score=sum(q.points or 1 for q in exercise.questions),
        last_heartbeat=utcnow(),
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


@bp.route("/exercices/<int:exercise_id>/commencer", methods=["POST"])
@login_required
def start_exercise(exercise_id: int):
    exercise = db.session.get(Exercise, exercise_id) or abort(404)
    if not exercise.published or exercise.kind == "exam":
        abort(404)
    if not exercise.questions:
        flash("Cet exercice ne contient pas encore de question.", "warning")
        return redirect(url_for("learning.exercise_detail", exercise_id=exercise.id))

    attempt = (
        Attempt.query.filter_by(user_id=g.user.id, exercise_id=exercise.id, status="in_progress")
        .order_by(Attempt.started_at.desc()).first()
    )
    if not attempt:
        attempt = _create_attempt(exercise)
        log_audit("exercise.started", target=f"exercise={exercise.id},attempt={attempt.id}")
    return redirect(url_for("learning.take_exercise", attempt_id=attempt.id))


@bp.route("/exercices/tentative/<int:attempt_id>")
@login_required
def take_exercise(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.user_id != g.user.id and not g.user.is_admin:
        abort(403)
    if attempt.exercise.kind == "exam":
        return redirect(url_for("exam.take_exam", attempt_id=attempt.id))
    if attempt.status != "in_progress":
        return redirect(url_for("learning.result_detail", attempt_id=attempt.id))

    elapsed = int((utcnow() - attempt.started_at).total_seconds())
    remaining = max(0, attempt.exercise.duration_minutes * 60 - elapsed)

    questions = attempt.exercise.questions
    return render_template(
        "user/take_exercise.html", attempt=attempt, exercise=attempt.exercise,
        questions=questions, remaining=remaining,
    )


def grade_attempt(attempt: Attempt, form) -> None:
    """Corrige une tentative côté serveur. Les bonnes réponses ne quittent jamais le serveur avant correction."""
    exercise = attempt.exercise
    score = 0
    max_score = 0
    for question in exercise.questions:
        points = question.points or 1
        max_score += points
        raw = form.get(f"q_{question.id}")
        option_id = int(raw) if raw and str(raw).isdigit() else None
        option = db.session.get(Option, option_id) if option_id else None
        if option and option.question_id != question.id:
            option = None

        correct = bool(option and option.is_correct)
        awarded = points if correct else 0
        score += awarded

        existing = Answer.query.filter_by(attempt_id=attempt.id, question_id=question.id).first()
        if existing:
            existing.option_id = option.id if option else None
            existing.is_correct = correct
            existing.points_awarded = awarded
            existing.answered_at = utcnow()
        else:
            db.session.add(Answer(
                attempt_id=attempt.id, question_id=question.id,
                option_id=option.id if option else None,
                is_correct=correct, points_awarded=awarded,
            ))

    attempt.score = score
    attempt.max_score = max_score
    attempt.status = "submitted"
    attempt.submitted_at = utcnow()
    db.session.commit()


@bp.route("/exercices/tentative/<int:attempt_id>/soumettre", methods=["POST"])
@login_required
def submit_exercise(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.user_id != g.user.id:
        abort(403)
    if attempt.status != "in_progress":
        return redirect(url_for("learning.result_detail", attempt_id=attempt.id))

    grade_attempt(attempt, request.form)
    log_audit("exercise.submitted", target=f"attempt={attempt.id}",
              details=f"score={attempt.score}/{attempt.max_score}")
    flash(f"Exercice corrigé : {attempt.score}/{attempt.max_score} points.", "success")
    return redirect(url_for("learning.result_detail", attempt_id=attempt.id))


@bp.route("/resultats")
@login_required
def results():
    if g.user.is_admin:
        flash("Vos statistiques personnelles d'apprenant sont remplacées par celles de la classe.", "info")
        return redirect(url_for("admin.statistics"))
    attempts = (
        Attempt.query.filter_by(user_id=g.user.id, status="submitted")
        .order_by(Attempt.submitted_at.desc())
        .all()
    )
    average = round(sum(a.percentage for a in attempts) / len(attempts)) if attempts else 0
    passed = sum(1 for a in attempts if a.passed)
    return render_template(
        "user/results.html", attempts=attempts, average=average, passed=passed
    )


@bp.route("/resultats/<int:attempt_id>")
@login_required
def result_detail(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.user_id != g.user.id and not g.user.is_admin:
        abort(403)
    if attempt.status == "in_progress":
        return redirect(url_for("learning.take_exercise", attempt_id=attempt.id))

    answers = {a.question_id: a for a in attempt.answers}
    return render_template(
        "user/result_detail.html", attempt=attempt, exercise=attempt.exercise, answers=answers
    )
