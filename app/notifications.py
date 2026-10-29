# -*- coding: utf-8 -*-
"""Notifications en temps réel — TIC MASTER #by_Myazirzk.

Un seul point d'entrée, `notify()`, utilisé par les messages, les battles, les
annonces, les examens corrigés et les actions d'administration. Les
notifications sont stockées en base (une ligne par destinataire) : elles
survivent au redémarrage du serveur et sont propres à chaque compte.

Le navigateur interroge `GET /api/notifications` toutes les 25 secondes
(pause automatique quand l'onglet est en arrière-plan) et affiche :
  • un compteur sur la cloche de la barre du haut,
  • une bannière discrète pour chaque nouveauté,
  • un panneau déroulant avec les dernières notifications.
"""
from __future__ import annotations

from datetime import timedelta

from flask import url_for

from .extensions import db
from .models import Notification, User, utcnow, STATUS_ACTIVE

#: Libellés et icônes par type (utilisés par l'API et les gabarits).
KINDS = {
    "message": {"label": "Message", "icon": "message"},
    "battle": {"label": "Battle", "icon": "zap"},
    "annonce": {"label": "Annonce", "icon": "bell"},
    "note": {"label": "Note", "icon": "award"},
    "compte": {"label": "Compte", "icon": "shield"},
    "system": {"label": "Système", "icon": "info"},
}

#: Durée de conservation des notifications déjà lues.
RETENTION_DAYS = 45

#: Nombre maximal de notifications conservées par personne.
MAX_PER_USER = 200


def _prune(user_id: int) -> None:
    """Ménage léger : les lues anciennes partent, on garde les 200 dernières."""
    limite = utcnow() - timedelta(days=RETENTION_DAYS)
    Notification.query.filter(
        Notification.user_id == user_id,
        Notification.read_at.isnot(None),
        Notification.read_at < limite,
    ).delete(synchronize_session=False)

    # Au-delà de 200 lignes, on supprime les plus anciennes déjà lues.
    total = Notification.query.filter_by(user_id=user_id).count()
    if total > MAX_PER_USER:
        vieilles = (
            Notification.query.filter(
                Notification.user_id == user_id, Notification.read_at.isnot(None)
            )
            .order_by(Notification.created_at.asc())
            .limit(total - MAX_PER_USER)
            .all()
        )
        for row in vieilles:
            db.session.delete(row)


def notify(user_id: int | None,
           kind: str,
           title: str,
           body: str = "",
           url: str = "",
           actor=None,
           icon: str | None = None,
           commit: bool = True) -> Notification | None:
    """Crée une notification pour `user_id`.

    `actor` peut être un utilisateur (objet ou identifiant). On n'envoie jamais
    de notification à soi-même. `commit=False` laisse l'appelant valider la
    transaction (utile quand plusieurs notifications sont créées d'un coup).
    """
    if not user_id:
        return None

    actor_id = getattr(actor, "id", actor)
    if actor_id and int(actor_id) == int(user_id):
        return None

    kind = kind if kind in KINDS else "system"
    row = Notification(
        user_id=int(user_id),
        kind=kind,
        title=(title or "")[:190],
        body=(body or "")[:400],
        url=(url or "")[:255],
        icon=(icon or KINDS[kind]["icon"])[:30],
        actor_id=int(actor_id) if actor_id else None,
    )
    db.session.add(row)
    _prune(int(user_id))
    if commit:
        db.session.commit()
    return row


def notify_many(user_ids, kind: str, title: str, body: str = "", url: str = "",
                actor=None, icon: str | None = None) -> int:
    """Envoie la même notification à plusieurs personnes (annonce, battle…)."""
    envoyees = 0
    acteur = getattr(actor, "id", actor)
    for user_id in set(int(u) for u in user_ids if u):
        if acteur and int(user_id) == int(acteur):
            continue
        notify(user_id, kind, title, body, url, actor=actor, icon=icon, commit=False)
        envoyees += 1
    if envoyees:
        db.session.commit()
    return envoyees


def notify_staff(kind: str, title: str, body: str = "", url: str = "", actor=None) -> int:
    """Prévient tous les administrateurs actifs (demandes à valider…)."""
    ids = [
        row.id for row in User.query.filter(
            User.status == STATUS_ACTIVE, User.role.in_(["super_admin", "admin"])
        ).all()
    ]
    return notify_many(ids, kind, title, body, url, actor=actor)


def unread_count(user) -> int:
    if user is None:
        return 0
    return Notification.query.filter_by(user_id=user.id, read_at=None).count()


def recent(user, limit: int = 8):
    """Dernières notifications, les non lues d'abord."""
    if user is None:
        return []
    return (
        Notification.query.filter_by(user_id=user.id)
        .order_by(Notification.read_at.isnot(None).asc(), Notification.id.desc())
        .limit(limit)
        .all()
    )


def mark_read(user, notification_id: int | None = None) -> int:
    """Marque une notification (ou toutes) comme lue. Retourne le nombre touché."""
    if user is None:
        return 0
    query = Notification.query.filter_by(user_id=user.id, read_at=None)
    if notification_id is not None:
        query = query.filter(Notification.id == notification_id)
    touched = 0
    now = utcnow()
    for row in query.all():
        row.read_at = now
        touched += 1
    if touched:
        db.session.commit()
    return touched


def safe_url(candidate: str) -> str:
    """N'accepte qu'un chemin interne (« /messages ») pour éviter toute redirection ouverte."""
    candidate = (candidate or "").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return url_for("notifications.index")
    return candidate


def as_dict(row: Notification) -> dict:
    """Forme JSON envoyée au navigateur."""
    return {
        "id": row.id,
        "kind": row.kind,
        "label": KINDS.get(row.kind, KINDS["system"])["label"],
        "title": row.title,
        "body": row.body,
        "url": safe_url(row.url),
        "icon": row.icon or KINDS.get(row.kind, KINDS["system"])["icon"],
        "at": row.created_at.strftime("%d/%m %H:%M") if row.created_at else "",
        "iso": row.created_at.isoformat() if row.created_at else "",
        "read": row.is_read,
        "actor": (row.actor.full_name or row.actor.username) if row.actor else "",
    }
