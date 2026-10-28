# -*- coding: utf-8 -*-
"""Messagerie interne et battles de connaissances."""
from __future__ import annotations

import random
import secrets
import string
from datetime import timedelta

from flask import (
    Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for,
)
from sqlalchemy import func, or_

from ..extensions import db
from ..models import (
    BattleMember, BattleRoom, Exercise, Message, Option, Question, User, utcnow, STATUS_ACTIVE,
)
from ..security.core import login_required, log_audit

bp = Blueprint("social", __name__)

QUESTION_SECONDS = 20
BATTLE_QUESTIONS = 5


# ---------------------------------------------------------------------------
# Messagerie
# ---------------------------------------------------------------------------
def _dm_room(a: int, b: int) -> str:
    low, high = sorted((a, b))
    return f"dm:{low}:{high}"


def _can_access_room(user: User, room: str) -> bool:
    if room == "general":
        return True
    if not room.startswith("dm:"):
        return False
    parts = room.split(":")
    if len(parts) != 3 or not all(p.isdigit() for p in parts[1:]):
        return False
    return user.id in (int(parts[1]), int(parts[2]))


def _conversations_for(user: User):
    """Liste des conversations privées de l'utilisateur avec aperçu."""
    rows = (
        Message.query.filter(
            Message.room.like("dm:%"),
            or_(Message.sender_id == user.id, Message.recipient_id == user.id),
            Message.deleted.is_(False),
        )
        .order_by(Message.created_at.desc())
        .limit(300)
        .all()
    )
    seen, out = set(), []
    for msg in rows:
        if msg.room in seen:
            continue
        seen.add(msg.room)
        other_id = msg.recipient_id if msg.sender_id == user.id else msg.sender_id
        other = db.session.get(User, other_id) if other_id else None
        if other:
            out.append({"user": other, "last": msg})
    return out


@bp.route("/messages")
@login_required
def messages():
    room = request.args.get("room") or "general"
    if not _can_access_room(g.user, room):
        room = "general"

    conversations = _conversations_for(g.user)
    contacts = (
        User.query.filter(User.status == STATUS_ACTIVE, User.id != g.user.id)
        .order_by(User.full_name.asc())
        .limit(100)
        .all()
    )
    title = "Salon général"
    if room.startswith("dm:"):
        _, a, b = room.split(":")
        other_id = int(b) if int(a) == g.user.id else int(a)
        other = db.session.get(User, other_id)
        title = other.full_name or other.username if other else "Conversation"

    return render_template(
        "user/messages.html",
        room=room,
        title=title,
        conversations=conversations,
        contacts=contacts,
    )


@bp.route("/api/messages")
@login_required
def api_messages():
    room = request.args.get("room") or "general"
    if not _can_access_room(g.user, room):
        return jsonify({"ok": False, "error": "Conversation non autorisée."}), 403

    after = request.args.get("after", type=int) or 0
    query = Message.query.filter_by(room=room, deleted=False)
    if after:
        query = query.filter(Message.id > after)
    rows = query.order_by(Message.id.asc()).limit(120).all()

    return jsonify({
        "ok": True,
        "room": room,
        "messages": [
            {
                "id": m.id,
                "body": m.body,
                "at": m.created_at.isoformat(timespec="minutes"),
                "mine": m.sender_id == g.user.id,
                "sender": {
                    "id": m.sender_id,
                    "name": (m.sender.full_name or m.sender.username) if m.sender else "Inconnu",
                    "initials": m.sender.initials if m.sender else "??",
                    "role": m.sender.role if m.sender else "user",
                },
            }
            for m in rows
        ],
    })


@bp.route("/api/messages", methods=["POST"])
@login_required
def api_send_message():
    payload = request.get_json(silent=True) or request.form
    body = (payload.get("body") or "").strip()
    room = (payload.get("room") or "general").strip()

    if not body:
        return jsonify({"ok": False, "error": "Message vide."}), 400
    if len(body) > 2000:
        return jsonify({"ok": False, "error": "Message trop long (2000 caractères maximum)."}), 400

    # Anti-spam : 20 messages / minute
    from ..security.core import limiter
    if limiter.hit(f"msg:{g.user.id}", 20, 60):
        return jsonify({"ok": False, "error": "Vous envoyez des messages trop rapidement."}), 429

    recipient_id = None
    if room.startswith("dm:"):
        if not _can_access_room(g.user, room):
            return jsonify({"ok": False, "error": "Conversation non autorisée."}), 403
        _, a, b = room.split(":")
        recipient_id = int(b) if int(a) == g.user.id else int(a)
    elif room != "general":
        return jsonify({"ok": False, "error": "Salon inconnu."}), 400

    msg = Message(sender_id=g.user.id, room=room, recipient_id=recipient_id, body=body)
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        "ok": True,
        "message": {
            "id": msg.id,
            "body": msg.body,
            "at": msg.created_at.isoformat(timespec="minutes"),
            "mine": True,
            "sender": {
                "id": g.user.id,
                "name": g.user.full_name or g.user.username,
                "initials": g.user.initials,
                "role": g.user.role,
            },
        },
    }), 201


# ---------------------------------------------------------------------------
# Battle
# ---------------------------------------------------------------------------
def _new_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        if not BattleRoom.query.filter_by(code=code).first():
            return code


def _question_pool(limit: int = 40):
    rows = (
        Question.query.join(Exercise, Question.exercise_id == Exercise.id)
        .filter(Exercise.published.is_(True))
        .order_by(func.random())
        .limit(limit)
        .all()
    )
    return [q for q in rows if len(q.options) >= 2]


def _advance_if_needed(room: BattleRoom) -> None:
    """Avancement autoritaire côté serveur : impossible à accélérer depuis le client."""
    if room.status != "running" or not room.question_started_at:
        return
    qids = room.qids()
    now = utcnow()
    changed = False
    while room.status == "running" and (now - room.question_started_at).total_seconds() >= QUESTION_SECONDS:
        room.current_index += 1
        room.question_started_at = room.question_started_at + timedelta(seconds=QUESTION_SECONDS)
        changed = True
        if room.current_index >= len(qids):
            room.status = "finished"
            room.finished_at = now
            break
    if changed:
        db.session.commit()


def _room_state(room: BattleRoom) -> dict:
    _advance_if_needed(room)
    qids = room.qids()
    member = BattleMember.query.filter_by(room_id=room.id, user_id=g.user.id).first()

    question = None
    seconds_left = 0
    if room.status == "running" and room.current_index < len(qids):
        question = db.session.get(Question, qids[room.current_index])
        if room.question_started_at:
            elapsed = (utcnow() - room.question_started_at).total_seconds()
            seconds_left = max(0, int(QUESTION_SECONDS - elapsed))

    members = []
    for m in room.members:
        answered = m.answered_index >= room.current_index
        members.append({
            "id": m.user_id,
            "name": (m.user.full_name or m.user.username) if m.user else "?",
            "initials": m.user.initials if m.user else "?",
            "score": m.score,
            "answered": answered,
            "is_me": m.user_id == g.user.id,
        })

    payload = {
        "ok": True,
        "room": {
            "id": room.id,
            "code": room.code,
            "name": room.name,
            "mode": room.mode,
            "status": room.status,
            "is_owner": room.owner_id == g.user.id,
        },
        "members": sorted(members, key=lambda x: -x["score"]),
        "index": room.current_index,
        "count": len(qids),
        "seconds_left": seconds_left,
        "my_answered": bool(member and member.answered_index >= room.current_index),
    }

    if question and room.status == "running":
        payload["question"] = {
            "id": question.id,
            "text": question.text,
            "options": [{"id": o.id, "text": o.text} for o in question.options],
        }

    if room.status == "finished":
        # Correction finale
        corrections = []
        for qid in qids:
            q = db.session.get(Question, qid)
            if not q:
                continue
            correct = q.correct_option
            corrections.append({
                "text": q.text,
                "correct": correct.text if correct else "",
                "explanation": q.explanation or "",
            })
        payload["corrections"] = corrections
        payload["ranking"] = sorted(members, key=lambda x: -x["score"])
    return payload


@bp.route("/battle")
@login_required
def battle_home():
    my_rooms = (
        BattleRoom.query.join(BattleMember, BattleMember.room_id == BattleRoom.id)
        .filter(BattleMember.user_id == g.user.id)
        .order_by(BattleRoom.created_at.desc())
        .limit(12)
        .all()
    )
    open_rooms = (
        BattleRoom.query.filter(BattleRoom.status.in_(["lobby", "running"]))
        .order_by(BattleRoom.created_at.desc())
        .limit(12)
        .all()
    )
    return render_template("user/battle.html", my_rooms=my_rooms, open_rooms=open_rooms)


@bp.route("/battle/<code>")
@login_required
def battle_room(code: str):
    room = BattleRoom.query.filter_by(code=code.upper()).first_or_404()
    member = BattleMember.query.filter_by(room_id=room.id, user_id=g.user.id).first()
    if not member and room.mode == "solo":
        abort(403)
    return render_template("user/battle_room.html", room=room, is_member=bool(member))


@bp.route("/api/battle/create", methods=["POST"])
@login_required
def api_create_battle():
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode") if payload.get("mode") in ("solo", "group") else "solo"
    name = (payload.get("name") or "").strip()[:120]

    # Un seul battle actif à la fois par utilisateur
    active = (
        BattleRoom.query.join(BattleMember, BattleMember.room_id == BattleRoom.id)
        .filter(BattleMember.user_id == g.user.id, BattleRoom.status.in_(["lobby", "running"]))
        .first()
    )
    if active:
        return jsonify({"ok": True, "code": active.code, "existing": True})

    pool = _question_pool()
    if len(pool) < BATTLE_QUESTIONS:
        return jsonify({"ok": False, "error": "Pas assez de questions disponibles pour lancer une battle."}), 400

    picked = random.sample(pool, BATTLE_QUESTIONS)
    if mode == "solo":
        # Règle : le nom du battle solo est le nom de l'utilisateur
        name = g.user.full_name or g.user.username
    elif not name:
        name = f"Groupe de {g.user.full_name or g.user.username}"

    room = BattleRoom(
        name=name[:120],
        mode=mode,
        code=_new_code(),
        owner_id=g.user.id,
        status="lobby",
        question_count=len(picked),
        question_ids=",".join(str(q.id) for q in picked),
    )
    db.session.add(room)
    db.session.flush()
    db.session.add(BattleMember(room_id=room.id, user_id=g.user.id))
    db.session.commit()
    log_audit("battle.created", target=room.code, details=f"mode={mode}")
    return jsonify({"ok": True, "code": room.code}), 201


@bp.route("/api/battle/join", methods=["POST"])
@login_required
def api_join_battle():
    payload = request.get_json(silent=True) or {}
    code = (payload.get("code") or "").strip().upper()
    room = BattleRoom.query.filter_by(code=code).first()
    if not room:
        return jsonify({"ok": False, "error": "Aucune battle ne correspond à ce code."}), 404
    if room.status == "finished":
        return jsonify({"ok": False, "error": "Cette battle est déjà terminée."}), 400
    if room.mode == "solo" and room.owner_id != g.user.id:
        return jsonify({"ok": False, "error": "Une battle solo est strictement personnelle."}), 403

    member = BattleMember.query.filter_by(room_id=room.id, user_id=g.user.id).first()
    if not member:
        db.session.add(BattleMember(room_id=room.id, user_id=g.user.id))
        db.session.commit()
        log_audit("battle.joined", target=room.code)
    return jsonify({"ok": True, "code": room.code})


@bp.route("/api/battle/rename", methods=["POST"])
@login_required
def api_rename_battle():
    payload = request.get_json(silent=True) or {}
    code = (payload.get("code") or "").strip().upper()
    name = (payload.get("name") or "").strip()[:120]
    room = BattleRoom.query.filter_by(code=code).first_or_404()

    if room.mode == "solo":
        return jsonify({"ok": False, "error": "Le nom d'une battle solo est celui de l'utilisateur."}), 400
    if not name:
        return jsonify({"ok": False, "error": "Le nom du groupe ne peut pas être vide."}), 400

    member = BattleMember.query.filter_by(room_id=room.id, user_id=g.user.id).first()
    if not member:
        return jsonify({"ok": False, "error": "Vous ne participez pas à cette battle."}), 403
    if room.owner_id != g.user.id:
        return jsonify({"ok": False, "error": "Seul le créateur peut renommer le groupe."}), 403

    room.name = name
    db.session.commit()
    log_audit("battle.renamed", target=room.code, details=name)
    return jsonify({"ok": True, "name": room.name})


@bp.route("/api/battle/start", methods=["POST"])
@login_required
def api_start_battle():
    payload = request.get_json(silent=True) or {}
    room = BattleRoom.query.filter_by(code=(payload.get("code") or "").strip().upper()).first_or_404()
    if room.owner_id != g.user.id:
        return jsonify({"ok": False, "error": "Seul le créateur peut lancer la battle."}), 403
    if room.status != "lobby":
        return jsonify({"ok": False, "error": "La battle a déjà démarré."}), 400

    room.status = "running"
    room.current_index = 0
    room.question_started_at = utcnow()
    for member in room.members:
        member.score = 0
        member.answered_index = -1
    db.session.commit()
    log_audit("battle.started", target=room.code)
    return jsonify({"ok": True})


@bp.route("/api/battle/state")
@login_required
def api_battle_state():
    code = (request.args.get("code") or "").upper()
    room = BattleRoom.query.filter_by(code=code).first_or_404()
    if not BattleMember.query.filter_by(room_id=room.id, user_id=g.user.id).first():
        return jsonify({"ok": False, "error": "Vous ne participez pas à cette battle."}), 403
    return jsonify(_room_state(room))


@bp.route("/api/battle/answer", methods=["POST"])
@login_required
def api_battle_answer():
    payload = request.get_json(silent=True) or {}
    room = BattleRoom.query.filter_by(code=(payload.get("code") or "").strip().upper()).first_or_404()
    option_id = payload.get("option_id")

    member = BattleMember.query.filter_by(room_id=room.id, user_id=g.user.id).first()
    if not member:
        return jsonify({"ok": False, "error": "Vous ne participez pas à cette battle."}), 403

    _advance_if_needed(room)
    if room.status != "running":
        return jsonify({"ok": False, "error": "La battle n'est pas en cours."}), 400
    if member.answered_index >= room.current_index:
        return jsonify({"ok": False, "error": "Vous avez déjà répondu à cette question."}), 400

    qids = room.qids()
    if room.current_index >= len(qids):
        return jsonify({"ok": False, "error": "Plus de questions."}), 400

    question = db.session.get(Question, qids[room.current_index])
    option = db.session.get(Option, int(option_id)) if option_id else None
    if not question or not option or option.question_id != question.id:
        return jsonify({"ok": False, "error": "Réponse invalide."}), 400

    correct = bool(option.is_correct)
    if correct:
        member.score = (member.score or 0) + 1
    member.answered_index = room.current_index
    member.last_answer_correct = correct
    db.session.commit()

    return jsonify({"ok": True, "correct": correct, "score": member.score})
