# -*- coding: utf-8 -*-
"""Examens trimestriels surveillés — anti-fraude.

Règle : quitter l'onglet d'examen (changement d'onglet, navigation hors examen,
perte du plein écran, coupure de battement de cœur) = tentative de fraude.
Au premier écart, la tentative est éliminée et enregistrée.
Seul le SUPER ADMINISTRATEUR peut réaffecter l'examen à l'apprenant éliminé.
"""
from __future__ import annotations

from datetime import timedelta

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for,
)

from ..extensions import db
from ..models import Attempt, Exercise, utcnow, ROLE_SUPER_ADMIN
from ..security.core import login_required, log_audit

bp = Blueprint("exam", __name__)


@bp.before_request
def _teachers_have_no_exam():
    """Le super administrateur est professeur : aucun examen à passer.

    Contrôle fait côté serveur (masquer le menu ne suffit pas).
    """
    user = getattr(g, "user", None)
    if user is None or not user.is_admin:
        return None
    if request.method == "GET":
        # Le professeur ne compose pas : il corrige et surveille.
        if user.is_super_admin:
            flash("Votre rôle de professeur ne passe pas d'examen : voici les notes des élèves.", "info")
            return redirect(url_for("admin.grades"))
        flash("Votre rôle de professeur ne passe pas d'examen : voici la gestion des examens.", "info")
        return redirect(url_for("admin.exams"))
    abort(403)


# Préfixes qui ne constituent JAMAIS une sortie d'onglet (fichiers techniques, API, santé)
EXAM_PATHS_EXEMPT = (
    "/examens",
    "/api/",
    "/static/",
    "/auth/",
    "/fichiers/",
    "/sante",
    "/manifest.webmanifest",
    "/service-worker.js",
    "/favicon.ico",
)

HEARTBEAT_GAP_SECONDS = 45


def _active_exam_attempt(user_id: int) -> Attempt | None:
    return (
        Attempt.query.join(Exercise, Attempt.exercise_id == Exercise.id)
        .filter(
            Attempt.user_id == user_id,
            Attempt.status == "in_progress",
            Exercise.kind == "exam",
        )
        .order_by(Attempt.started_at.desc())
        .first()
    )


def _remaining_seconds(attempt: Attempt) -> int:
    duration = (attempt.exercise.duration_minutes or 20) * 60
    elapsed = int((utcnow() - attempt.started_at).total_seconds())
    return max(0, duration - elapsed)


def register_violation(attempt: Attempt, reason: str) -> dict:
    """Enregistre une sortie d'onglet. Élimine au-delà du seuil configuré."""
    if attempt.status != "in_progress":
        return {
            "ok": True, "eliminated": attempt.status == "eliminated",
            "status": attempt.status, "violations": attempt.tab_violations or 0,
            "limit": attempt.exercise.max_tab_violations or 1, "remaining": 0,
        }

    attempt.tab_violations = (attempt.tab_violations or 0) + 1
    limit = attempt.exercise.max_tab_violations or 1
    eliminated = attempt.tab_violations >= limit

    if eliminated:
        attempt.status = "eliminated"
        attempt.elimination_reason = reason[:255]
        attempt.submitted_at = utcnow()

    db.session.commit()
    log_audit(
        "exam.violation",
        target=f"attempt={attempt.id}",
        details=f"raison={reason}; violations={attempt.tab_violations}/{limit}; éliminé={eliminated}",
    )
    return {
        "ok": True,
        "eliminated": eliminated,
        "status": attempt.status,
        "violations": attempt.tab_violations,
        "limit": limit,
        "remaining": max(0, limit - attempt.tab_violations),
        "message": "Tentative de fraude enregistrée." if eliminated else "Avertissement enregistré.",
    }


@bp.before_app_request
def _guard_exam_navigation():
    """Toute navigation HTML hors de l'espace examen pendant une épreuve = fraude."""
    if request.method != "GET":
        return None
    if request.path.startswith(EXAM_PATHS_EXEMPT):
        return None
    if not request.accept_mimetypes.accept_html:
        return None

    user = g.get("user")
    if not user:
        return None

    attempt = _active_exam_attempt(user.id)
    if not attempt:
        return None

    result = register_violation(attempt, "Sortie de l'onglet Examen (navigation hors examen)")
    if result["eliminated"]:
        flash("Vous avez quitté l'onglet Examen : votre tentative a été éliminée pour fraude.", "danger")
        return redirect(url_for("exam.exam_result", attempt_id=attempt.id))
    flash("Avertissement : vous avez quitté l'examen. Une nouvelle sortie entraînera votre élimination.", "warning")
    return redirect(url_for("exam.take_exam", attempt_id=attempt.id))


# ---------------------------------------------------------------------------
# Liste des examens
# ---------------------------------------------------------------------------
@bp.route("/examens")
@login_required
def index():
    if _active_exam_attempt(g.user.id):
        attempt = _active_exam_attempt(g.user.id)
        return redirect(url_for("exam.take_exam", attempt_id=attempt.id))

    exams = (
        Exercise.query.filter_by(kind="exam", published=True)
        .order_by(Exercise.term, Exercise.id)
        .all()
    )
    history = {}
    for ex in exams:
        attempts = (
            Attempt.query.filter_by(user_id=g.user.id, exercise_id=ex.id)
            .order_by(Attempt.started_at.desc()).all()
        )
        history[ex.id] = attempts

    return render_template("user/exams.html", exams=exams, history=history)


@bp.route("/examens/<int:exercise_id>/commencer", methods=["POST"])
@login_required
def start(exercise_id: int):
    exercise = db.session.get(Exercise, exercise_id) or abort(404)
    if exercise.kind != "exam" or not exercise.published:
        abort(404)
    if not exercise.questions:
        flash("Cet examen n'est pas encore prêt.", "warning")
        return redirect(url_for("exam.index"))

    existing = (
        Attempt.query.filter_by(user_id=g.user.id, exercise_id=exercise.id)
        .order_by(Attempt.started_at.desc()).first()
    )
    if existing and existing.status == "eliminated":
        flash(
            "Vous avez été éliminé de cet examen pour tentative de fraude. "
            "Seul le super administrateur peut réaffecter cette épreuve.",
            "danger",
        )
        return redirect(url_for("exam.index"))
    if existing and existing.status == "submitted":
        flash("Vous avez déjà passé cet examen.", "info")
        return redirect(url_for("exam.exam_result", attempt_id=existing.id))
    if existing and existing.status == "in_progress":
        return redirect(url_for("exam.take_exam", attempt_id=existing.id))

    attempt = Attempt(
        user_id=g.user.id,
        exercise_id=exercise.id,
        status="in_progress",
        max_score=sum(q.points or 1 for q in exercise.questions),
        last_heartbeat=utcnow(),
    )
    db.session.add(attempt)
    db.session.commit()
    log_audit("exam.started", target=f"exercise={exercise.id},attempt={attempt.id}")
    flash("Examen démarré. Ne quittez surtout pas cet onglet : toute sortie entraîne l'élimination.", "warning")
    return redirect(url_for("exam.take_exam", attempt_id=attempt.id))


@bp.route("/examens/passer/<int:attempt_id>")
@login_required
def take_exam(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.user_id != g.user.id:
        abort(403)
    if attempt.exercise.kind != "exam":
        return redirect(url_for("learning.take_exercise", attempt_id=attempt.id))
    if attempt.status == "eliminated":
        return redirect(url_for("exam.exam_result", attempt_id=attempt.id))
    if attempt.status != "in_progress":
        return redirect(url_for("exam.exam_result", attempt_id=attempt.id))

    remaining = _remaining_seconds(attempt)
    if remaining <= 0:
        from .learning import grade_attempt
        grade_attempt(attempt, {})
        log_audit("exam.timeout", target=f"attempt={attempt.id}")
        flash("Le temps imparti est écoulé. Votre copie a été corrigée automatiquement.", "info")
        return redirect(url_for("exam.exam_result", attempt_id=attempt.id))

    return render_template(
        "user/exam_take.html",
        attempt=attempt,
        exercise=attempt.exercise,
        questions=attempt.exercise.questions,
        remaining=remaining,
        limit=attempt.exercise.max_tab_violations or 1,
    )


# ---------------------------------------------------------------------------
# API de surveillance (JSON)
# ---------------------------------------------------------------------------
@bp.route("/api/exam/<int:attempt_id>/violation", methods=["POST"])
@login_required
def api_violation(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.user_id != g.user.id:
        return jsonify({"ok": False, "error": "Accès refusé."}), 403

    payload = request.get_json(silent=True) or {}
    reason = (payload.get("reason") or request.args.get("reason") or "Sortie de l'onglet")[:120]
    result = register_violation(attempt, f"Sortie de l'onglet Examen ({reason})")
    return jsonify(result)


@bp.route("/api/exam/<int:attempt_id>/heartbeat", methods=["POST"])
@login_required
def api_heartbeat(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.user_id != g.user.id:
        return jsonify({"ok": False, "error": "Accès refusé."}), 403
    if attempt.status != "in_progress":
        return jsonify({"ok": True, "status": attempt.status, "redirect": url_for("exam.exam_result", attempt_id=attempt.id)})

    now = utcnow()
    gap = (now - attempt.last_heartbeat).total_seconds() if attempt.last_heartbeat else 0
    result = {"ok": True, "status": attempt.status, "remaining": _remaining_seconds(attempt)}

    if gap > HEARTBEAT_GAP_SECONDS:
        # Onglet fermé, appareil verrouillé ou connexion interrompue
        violation = register_violation(attempt, "Absence de battement de cœur pendant l'examen")
        result.update({
            "eliminated": violation["eliminated"],
            "violations": violation["violations"],
            "suspicious_gap": int(gap),
        })
        if violation["eliminated"]:
            result["redirect"] = url_for("exam.exam_result", attempt_id=attempt.id)

    attempt.last_heartbeat = now
    db.session.commit()

    if _remaining_seconds(attempt) <= 0:
        from .learning import grade_attempt
        grade_attempt(attempt, {})
        result.update({"timeout": True, "redirect": url_for("exam.exam_result", attempt_id=attempt.id)})
    return jsonify(result)


# ---------------------------------------------------------------------------
# Soumission et résultat
# ---------------------------------------------------------------------------
@bp.route("/examens/passer/<int:attempt_id>/soumettre", methods=["POST"])
@login_required
def submit(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.user_id != g.user.id:
        abort(403)
    if attempt.status != "in_progress":
        return redirect(url_for("exam.exam_result", attempt_id=attempt.id))

    from .learning import grade_attempt
    grade_attempt(attempt, request.form)
    log_audit("exam.submitted", target=f"attempt={attempt.id}",
              details=f"score={attempt.score}/{attempt.max_score}")
    flash("Examen soumis et corrigé.", "success")

    # « Note publiée » : l'élève est prévenu dès la correction
    from ..notifications import notify
    note = round(attempt.score * 20 / attempt.max_score, 1) if attempt.max_score else 0
    notify(
        attempt.user_id, "note", "Votre examen est corrigé",
        f"{attempt.exercise.title if attempt.exercise else 'Examen'} : "
        f"{attempt.score}/{attempt.max_score} ({note}/20).",
        url_for("exam.exam_result", attempt_id=attempt.id), icon="award",
        dedupe_key=f"note:attempt:{attempt.id}",
    )
    return redirect(url_for("exam.exam_result", attempt_id=attempt.id))


@bp.route("/examens/resultat/<int:attempt_id>")
@login_required
def exam_result(attempt_id: int):
    attempt = db.session.get(Attempt, attempt_id) or abort(404)
    if attempt.user_id != g.user.id and not g.user.is_admin:
        abort(403)
    answers = {a.question_id: a for a in attempt.answers}
    return render_template(
        "user/exam_result.html", attempt=attempt, exercise=attempt.exercise, answers=answers
    )
