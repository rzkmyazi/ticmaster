# -*- coding: utf-8 -*-
"""Scolarité — notes et statistiques des élèves (TIC MASTER #by_Myazirzk).

Ce module alimente l'espace « Chef d'établissement » du super administrateur :
  • `student_rows()`   — une ligne par apprenant (notes, progression, activité) ;
  • `student_report()` — le bulletin détaillé d'un apprenant ;
  • `class_overview()` — les statistiques de la classe entière.

Tous les calculs sont faits à partir des vraies tentatives enregistrées
(`Attempt`), jamais de valeurs simulées.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from .extensions import db
from .models import (
    Attempt, Exercise, Lesson, LessonProgress, Module, User, ROLE_USER, utcnow,
)

#: Mentions scolaires sur 20.
MENTIONS = (
    (16, "Excellent", "good"),
    (14, "Très bien", "good"),
    (12, "Bien", "mid"),
    (10, "Passable", "mid"),
    (0, "Insuffisant", "low"),
)


def note20(percent: float) -> float:
    """Convertit un pourcentage en note sur 20 (une décimale)."""
    return round((percent or 0) * 20 / 100, 1)


def mention(note: float) -> tuple[str, str]:
    for seuil, label, tone in MENTIONS:
        if note >= seuil:
            return label, tone
    return "Insuffisant", "low"


def tone_for(note: float) -> str:
    if note >= 14:
        return "good"
    if note >= 10:
        return "mid"
    return "low"


def _pct(score: int, maximum: int) -> float:
    if not maximum:
        return 0.0
    return score * 100.0 / maximum


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


# ---------------------------------------------------------------------------
# Chargement de base
# ---------------------------------------------------------------------------
def _learner_query():
    return User.query.filter(User.role == ROLE_USER)


def _attempts_by_user() -> tuple[dict, dict]:
    """Toutes les tentatives, regroupées par apprenant (2 requêtes au total)."""
    attempts = (
        Attempt.query.options(joinedload(Attempt.exercise))
        .order_by(Attempt.started_at.desc())
        .all()
    )
    by_user: dict[int, list[Attempt]] = defaultdict(list)
    for attempt in attempts:
        by_user[attempt.user_id].append(attempt)
    return dict(by_user), {}


def _lessons_done() -> tuple[dict[int, int], int]:
    rows = (
        db.session.query(LessonProgress.user_id, func.count(LessonProgress.id))
        .group_by(LessonProgress.user_id)
        .all()
    )
    done = {uid: int(count) for uid, count in rows}
    total = (
        db.session.query(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.status == "published", Lesson.published.is_(True))
        .scalar()
    ) or 0
    return done, int(total)


# ---------------------------------------------------------------------------
# Une ligne par élève
# ---------------------------------------------------------------------------
def student_rows(search: str = "", sort: str = "moyenne") -> list[dict]:
    learners = _learner_query().order_by(User.full_name, User.username).all()
    by_user, _ = _attempts_by_user()
    done_map, total_lessons = _lessons_done()

    rows = []
    for user in learners:
        attempts = by_user.get(user.id, [])
        submitted = [a for a in attempts if a.status == "submitted" and a.exercise]
        eliminated = [a for a in attempts if a.status == "eliminated"]
        exos = [a for a in submitted if a.exercise.kind != "exam"]
        exams = [a for a in submitted if a.exercise.kind == "exam"]

        def _avg(items):
            if not items:
                return None
            return sum(_pct(a.score, a.max_score) for a in items) / len(items)

        avg_exos = _avg(exos)
        avg_exams = _avg(exams)
        values = [v for v in (avg_exos, avg_exams) if v is not None]
        average = sum(values) / len(values) if values else None

        lessons_done = done_map.get(user.id, 0)
        progress = round(lessons_done * 100 / total_lessons) if total_lessons else 0
        last = max([a.started_at for a in attempts], default=None)
        if user.last_seen_at and (last is None or user.last_seen_at > last):
            last = user.last_seen_at

        rows.append({
            "user": user,
            "attempts": len(attempts),
            "submitted": len(submitted),
            "exercises": len(exos),
            "exams": len(exams),
            "eliminated": len(eliminated),
            "avg_exos": round(avg_exos, 1) if avg_exos is not None else None,
            "avg_exams": round(avg_exams, 1) if avg_exams is not None else None,
            "average": round(average, 1) if average is not None else None,
            "note": note20(average) if average is not None else None,
            "lessons_done": lessons_done,
            "lessons_total": total_lessons,
            "progress": progress,
            "last_activity": last,
            "passed": round(sum(1 for a in submitted if a.percentage >= (a.exercise.pass_score or 50)) or 0),
        })

    # classement (par moyenne décroissante, les élèves sans note à la fin)
    ranked = sorted(
        [r for r in rows if r["average"] is not None],
        key=lambda r: r["average"], reverse=True,
    )
    for index, row in enumerate(ranked, 1):
        row["rank"] = index
    for row in rows:
        row.setdefault("rank", None)

    if search:
        needle = search.strip().lower()
        rows = [
            r for r in rows
            if needle in (r["user"].full_name or "").lower()
            or needle in (r["user"].username or "").lower()
        ]

    keys = {
        "moyenne": lambda r: (r["average"] is None, -(r["average"] or 0)),
        "nom": lambda r: (r["user"].full_name or r["user"].username or "").lower(),
        "progression": lambda r: -r["progress"],
        "activite": lambda r: -(r["last_activity"].timestamp() if r["last_activity"] else 0),
        "note": lambda r: (r["average"] is None, -(r["average"] or 0)),
        "numero": lambda r: (r["user"].class_number is None, r["user"].class_number or 0),
        "groupe": lambda r: (r["user"].class_group is None, r["user"].class_group or 0,
                             r["user"].class_number or 0),
    }
    rows.sort(key=keys.get(sort, keys["moyenne"]))
    return rows


# ---------------------------------------------------------------------------
# Bulletin d'un élève
# ---------------------------------------------------------------------------
def student_report(user_id: int) -> dict | None:
    user = db.session.get(User, user_id)
    if user is None or user.role != ROLE_USER:
        return None

    attempts = (
        Attempt.query.options(joinedload(Attempt.exercise))
        .filter(Attempt.user_id == user.id)
        .order_by(Attempt.started_at.desc())
        .all()
    )
    submitted = [a for a in attempts if a.status == "submitted" and a.exercise]
    exos = [a for a in submitted if a.exercise.kind != "exam"]
    exams = [a for a in submitted if a.exercise.kind == "exam"]
    eliminated = [a for a in attempts if a.status == "eliminated"]
    running = [a for a in attempts if a.status == "in_progress"]

    avg_exos = (sum(_pct(a.score, a.max_score) for a in exos) / len(exos)) if exos else None
    avg_exams = (sum(_pct(a.score, a.max_score) for a in exams) / len(exams)) if exams else None
    values = [v for v in (avg_exos, avg_exams) if v is not None]
    average = (sum(values) / len(values)) if values else None

    done_map, total_lessons = _lessons_done()
    lessons_done = done_map.get(user.id, 0)

    # Détail par module
    modules = Module.query.filter_by(status="published").order_by(Module.order_index).all()
    done_lesson_ids = {
        p.lesson_id for p in LessonProgress.query.filter_by(user_id=user.id).all()
    }
    per_module = []
    for module in modules:
        lessons = module.published_lessons
        done = sum(1 for lesson in lessons if lesson.id in done_lesson_ids)
        mod_attempts = [a for a in submitted if a.exercise.module_id == module.id]
        mod_avg = (
            sum(_pct(a.score, a.max_score) for a in mod_attempts) / len(mod_attempts)
            if mod_attempts else None
        )
        per_module.append({
            "module": module,
            "lessons_done": done,
            "lessons_total": len(lessons),
            "progress": round(done * 100 / len(lessons)) if lessons else 0,
            "attempts": len(mod_attempts),
            "average": round(mod_avg, 1) if mod_avg is not None else None,
            "note": note20(mod_avg) if mod_avg is not None else None,
        })

    # Examens par trimestre
    terms = defaultdict(list)
    for a in exams:
        terms[a.exercise.term or "—"].append(a)
    per_term = []
    for term in sorted(terms):
        items = terms[term]
        avg = sum(_pct(a.score, a.max_score) for a in items) / len(items)
        per_term.append({"term": term, "count": len(items), "average": round(avg, 1),
                         "note": note20(avg)})

    # Rang dans la classe
    rank, total_students = None, 0
    for row in student_rows():
        if row["average"] is not None:
            total_students += 1
        if row["user"].id == user.id:
            rank = row["rank"]

    history = [
        {
            "attempt": a,
            "label": a.started_at.strftime("%d/%m"),
            "value": round(_pct(a.score, a.max_score)),
            "kind": a.exercise.kind,
        }
        for a in submitted[:12]
    ][::-1]

    label, tone = mention(note20(average)) if average is not None else ("Pas encore noté", "low")

    return {
        "user": user,
        "attempts": attempts,
        "submitted": submitted,
        "exercises": exos,
        "exams": exams,
        "eliminated": eliminated,
        "running": running,
        "avg_exos": round(avg_exos, 1) if avg_exos is not None else None,
        "avg_exams": round(avg_exams, 1) if avg_exams is not None else None,
        "average": round(average, 1) if average is not None else None,
        "note": note20(average) if average is not None else None,
        "mention": label,
        "tone": tone,
        "rank": rank,
        "class_size": total_students,
        "lessons_done": lessons_done,
        "lessons_total": total_lessons,
        "progress": round(lessons_done * 100 / total_lessons) if total_lessons else 0,
        "per_module": per_module,
        "per_term": per_term,
        "history": history,
        "passed": sum(1 for a in submitted if a.percentage >= (a.exercise.pass_score or 50)),
    }


# ---------------------------------------------------------------------------
# Statistiques de la classe
# ---------------------------------------------------------------------------
def class_overview() -> dict:
    rows = student_rows()
    graded = [r for r in rows if r["average"] is not None]
    averages = [r["average"] for r in graded]

    learners = len(rows)
    active = sum(1 for r in rows if r["user"].status == "active")

    by_user, _ = _attempts_by_user()
    all_attempts = [a for items in by_user.values() for a in items]
    submitted = [a for a in all_attempts if a.status == "submitted" and a.exercise]
    eliminated = [a for a in all_attempts if a.status == "eliminated"]

    global_avg = (sum(averages) / len(averages)) if averages else 0
    class_note = note20(global_avg)

    # Histogramme sur 20
    buckets = [
        {"label": "0–4", "min": 0, "max": 5, "count": 0},
        {"label": "5–9", "min": 5, "max": 10, "count": 0},
        {"label": "10–12", "min": 10, "max": 13, "count": 0},
        {"label": "13–15", "min": 13, "max": 16, "count": 0},
        {"label": "16–20", "min": 16, "max": 21, "count": 0},
    ]
    for row in graded:
        note = row["note"]
        for bucket in buckets:
            if bucket["min"] <= note < bucket["max"]:
                bucket["count"] += 1
                break
    max_bucket = max([b["count"] for b in buckets] + [1])

    # Répartition des mentions
    mentions = defaultdict(int)
    for row in graded:
        mentions[mention(row["note"])[0]] += 1
    mention_rows = [
        {"label": label, "count": mentions.get(label, 0), "tone": tone}
        for label, tone in (("Excellent", "good"), ("Très bien", "good"), ("Bien", "mid"),
                            ("Passable", "mid"), ("Insuffisant", "low"))
    ]

    # Par module
    modules = Module.query.filter_by(status="published").order_by(Module.order_index).all()
    done_map, total_lessons = _lessons_done()
    per_module = []
    for module in modules:
        mod_attempts = [a for a in submitted if a.exercise.module_id == module.id]
        avg = (sum(_pct(a.score, a.max_score) for a in mod_attempts) / len(mod_attempts)
               if mod_attempts else None)
        lessons = module.published_lessons
        possible = learners * len(lessons)
        per_module.append({
            "module": module,
            "attempts": len(mod_attempts),
            "average": round(avg, 1) if avg is not None else None,
            "note": note20(avg) if avg is not None else None,
            "completion": 0,
            "lessons": len(lessons),
            "_possible": possible,
        })
    # progression réelle par module
    module_ids = [m["module"].id for m in per_module]
    if module_ids:
        progresses = (
            db.session.query(Module.id, func.count(LessonProgress.id))
            .outerjoin(Lesson, Lesson.module_id == Module.id)
            .outerjoin(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .filter(Module.id.in_(module_ids), Lesson.published.is_(True))
            .group_by(Module.id)
            .all()
        )
        prog_map = {mid: int(count) for mid, count in progresses}
        for item in per_module:
            possible = item["_possible"]
            item["completion"] = round(prog_map.get(item["module"].id, 0) * 100 / possible) if possible else 0
            item.pop("_possible")

    # Exercices / examens les plus difficiles
    exercises = Exercise.query.filter_by(published=True).all()
    per_exercise = []
    for exercise in exercises:
        items = [a for a in submitted if a.exercise_id == exercise.id]
        if not items:
            continue
        avg = sum(_pct(a.score, a.max_score) for a in items) / len(items)
        per_exercise.append({
            "exercise": exercise,
            "attempts": len(items),
            "average": round(avg, 1),
            "note": note20(avg),
            "pass_rate": round(sum(1 for a in items if a.percentage >= (exercise.pass_score or 50)) * 100 / len(items)),
        })
    hardest = sorted(per_exercise, key=lambda x: x["average"])[:6]

    # Activité des 14 derniers jours
    today = utcnow().date()
    activity = []
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        count = sum(1 for a in all_attempts if a.started_at and a.started_at.date() == day)
        activity.append({"label": day.strftime("%d/%m"), "value": count})
    max_activity = max([a["value"] for a in activity] + [1])

    return {
        "learners": learners,
        "active": active,
        "graded": len(graded),
        "average": round(global_avg, 1),
        "note": class_note,
        "median": note20(_median(averages)),
        "success_rate": round(sum(1 for r in graded if r["average"] >= 50) * 100 / len(graded)) if graded else 0,
        "submitted": len(submitted),
        "eliminated": len(eliminated),
        "elimination_rate": round(len(eliminated) * 100 / len(all_attempts)) if all_attempts else 0,
        "progress": round(sum(r["progress"] for r in rows) / len(rows)) if rows else 0,
        "buckets": buckets,
        "max_bucket": max_bucket,
        "mentions": mention_rows,
        "per_module": per_module,
        "hardest": hardest,
        "activity": activity,
        "max_activity": max_activity,
        "top": graded[:5],
        "struggling": [r for r in sorted(graded, key=lambda r: r["average"]) if r["average"] < 50][:5],
        "inactive": [r for r in rows if r["last_activity"] is None][:6],
        "total_lessons": total_lessons,
    }
