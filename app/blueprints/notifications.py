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
    non_lues = service.unread_count(user)
    total = Notification.query.filter_by(user_id=user.id).count()

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
        # Une notification déjà lue (marquée depuis un autre appareil) ne doit
        # pas réapparaître en bannière : c'est le rôle de `read`.
        nouveautes = [service.as_dict(row) for row in rows if not row.is_read]

    return jsonify({
        "ok": True,
        "count": non_lues,
        "unread": non_lues,
        "total": total,
        "latest_id": latest,
        "items": [service.as_dict(row) for row in items],
        "new": nouveautes,
    })


@bp.route("/api/notifications/<int:notification_id>/lue", methods=["POST"])
@login_required
def api_mark_read(notification_id: int):
    """Marque **sa propre** notification comme lue. Celle d'un autre : 404."""
    if service.get_owned(g.user, notification_id) is None:
        return jsonify({"ok": False, "error": "Notification introuvable."}), 404
    touched = service.mark_read(g.user, notification_id)
    return jsonify({"ok": True, "touched": touched, "count": service.unread_count(g.user)})


@bp.route("/api/notifications/tout-lire", methods=["POST"])
@login_required
def api_mark_all_read():
    touched = service.mark_read(g.user)
    return jsonify({"ok": True, "touched": touched, "count": 0})


@bp.route("/api/notifications/<int:notification_id>", methods=["DELETE", "POST"])
@login_required
def api_delete(notification_id: int):
    """Suppression individuelle : uniquement ses propres notifications."""
    if request.method == "POST" and not request.is_json:
        # Appel de formulaire (page historique) : on revient sur la page.
        from flask import flash
        ok = service.delete(g.user, notification_id)
        flash("Notification supprimée." if ok else "Notification introuvable.", 
              "success" if ok else "danger")
        return redirect(request.referrer or url_for("notifications.index"))

    ok = service.delete(g.user, notification_id)
    if not ok:
        return jsonify({"ok": False, "error": "Notification introuvable."}), 404
    return jsonify({"ok": True, "deleted": notification_id,
                    "count": service.unread_count(g.user)})


@bp.route("/notifications/<int:notification_id>/supprimer", methods=["POST"])
@login_required
def delete_one(notification_id: int):
    """Variante sans JavaScript (bouton de la page d'historique)."""
    from flask import flash
    ok = service.delete(g.user, notification_id)
    flash("Notification supprimée." if ok else "Notification introuvable.",
          "success" if ok else "danger")
    return redirect(request.referrer or url_for("notifications.index"))


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


@bp.route("/notifications/vider", methods=["POST"])
@login_required
def purge():
    """Retire de la liste les notifications déjà lues."""
    from flask import flash
    nombre = service.purge_read(g.user)
    flash(f"{nombre} notification(s) lue(s) supprimée(s)." if nombre
          else "Aucune notification lue à supprimer.", "success" if nombre else "info")
    return redirect(url_for("notifications.index"))


@bp.route("/api/notifications/ping")
@login_required
def api_ping():
    """Réponse minimale (le panneau n'a pas besoin de plus)."""
    db.session.commit()  # clôt proprement la lecture éventuelle
    return jsonify({"ok": True, "count": service.unread_count(g.user)})
