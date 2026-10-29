# -*- coding: utf-8 -*-
"""Notifications : API temps réel + page d'historique — TIC MASTER #by_Myazirzk."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, redirect, render_template, request, url_for
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
    # Un message privé atteint enfin un navigateur : on le marque « Reçu »
    from .social import mark_dm_delivered
    mark_dm_delivered(user)

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
    """Historique complet, groupé par jour et filtrable par type."""
    filtre = (request.args.get("type") or "").strip()
    if filtre and filtre not in service.KINDS:
        filtre = ""

    query = Notification.query.filter_by(user_id=g.user.id)
    if filtre:
        query = query.filter(Notification.kind == filtre)
    rows = query.order_by(Notification.created_at.desc()).limit(120).all()

    # Compteurs par type (pour les pastilles de filtre)
    compteurs = dict(
        db.session.query(Notification.kind, func.count(Notification.id))
        .filter(Notification.user_id == g.user.id)
        .group_by(Notification.kind)
        .all()
    )
    non_lues = dict(
        db.session.query(Notification.kind, func.count(Notification.id))
        .filter(Notification.user_id == g.user.id, Notification.read_at.is_(None))
        .group_by(Notification.kind)
        .all()
    )
    filtres = [
        {"kind": kind, "label": infos["label"], "icon": infos["icon"],
         "total": int(compteurs.get(kind, 0)), "unread": int(non_lues.get(kind, 0))}
        for kind, infos in service.KINDS.items()
        if compteurs.get(kind, 0)
    ]
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
        filtres=filtres,
        filtre=filtre,
    )


@bp.route("/notifications/tout-lire", methods=["POST"])
@login_required
def mark_all_and_back():
    """Lien direct depuis la page (sans JavaScript)."""
    service.mark_read(g.user)
    return redirect(url_for("notifications.index"))


@bp.route("/api/notifications/ping")
@login_required
def api_ping():
    """Réponse minimale (le panneau n'a pas besoin de plus)."""
    db.session.commit()  # clôt proprement la lecture éventuelle
    return jsonify({"ok": True, "count": service.unread_count(g.user)})
