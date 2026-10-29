# -*- coding: utf-8 -*-
"""Notifications : API temps réel + page d'historique — TIC MASTER #by_Myazirzk."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, render_template, request
from sqlalchemy import func

from .. import notifications as service
from ..extensions import db
from ..models import Notification
from ..security.core import login_required

bp = Blueprint("notifications", __name__)

#: Nombre de notifications renvoyées au panneau déroulant.
PANEL_LIMIT = 8


@bp.route("/api/notifications")
@login_required
def api_list():
    """État courant : compteur, dernières notifications, nouveautés depuis `since`."""
    user = g.user
    # « since » absent = premier chargement (aucune bannière) ;
    # « since=0 » est valide et signifie « tout est nouveau ».
    brut = request.args.get("since")
    since = int(brut) if brut is not None and brut.isdigit() else None

    items = service.recent(user, PANEL_LIMIT)
    dernier = (
        db.session.query(func.max(Notification.id))
        .filter(Notification.user_id == user.id)
        .scalar()
    )
    latest = int(dernier or 0)

    nouveautes = []
    if since is not None:
        rows = (
            Notification.query.filter(
                Notification.user_id == user.id, Notification.id > since
            )
            .order_by(Notification.id.asc())
            .limit(6)
            .all()
        )
        nouveautes = [service.as_dict(row) for row in rows]

    return jsonify({
        "ok": True,
        "count": service.unread_count(user),
        "latest_id": latest,
        "items": [service.as_dict(row) for row in items],
        "new": nouveautes,
    })


@bp.route("/api/notifications/<int:notification_id>/lue", methods=["POST"])
@login_required
def api_mark_read(notification_id: int):
    touched = service.mark_read(g.user, notification_id)
    return jsonify({"ok": True, "touched": touched, "count": service.unread_count(g.user)})


@bp.route("/api/notifications/tout-lire", methods=["POST"])
@login_required
def api_mark_all_read():
    touched = service.mark_read(g.user)
    return jsonify({"ok": True, "touched": touched, "count": 0})


@bp.route("/notifications")
@login_required
def index():
    """Historique complet, groupé par jour."""
    rows = (
        Notification.query.filter_by(user_id=g.user.id)
        .order_by(Notification.created_at.desc())
        .limit(120)
        .all()
    )
    groupes: list[tuple[str, list[Notification]]] = []
    for row in rows:
        jour = row.created_at.strftime("%d/%m/%Y") if row.created_at else "—"
        if not groupes or groupes[-1][0] != jour:
            groupes.append((jour, []))
        groupes[-1][1].append(row)

    return render_template(
        "user/notifications.html",
        groupes=groupes,
        total=len(rows),
        non_lues=service.unread_count(g.user),
    )


@bp.route("/notifications/tout-lire", methods=["POST"])
@login_required
def mark_all_and_back():
    """Lien direct depuis la page (sans JavaScript)."""
    service.mark_read(g.user)
    return render_template(
        "user/notifications.html",
        groupes=[], total=0, non_lues=0, tout_lu=True,
    )


@bp.route("/api/notifications/ping")
@login_required
def api_ping():
    """Réponse minimale (le panneau n'a pas besoin de plus)."""
    db.session.commit()  # clôt proprement la lecture éventuelle
    return jsonify({"ok": True, "count": service.unread_count(g.user)})
