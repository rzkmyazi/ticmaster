# -*- coding: utf-8 -*-
"""Notifications — TIC MASTER #by_Myazirzk.

Un seul point d'entrée, `notify()`, utilisé par les messages, les battles, les
annonces, les examens corrigés et les actions d'administration. Les
notifications sont stockées en base (une ligne par destinataire) : elles
survivent au redémarrage du serveur et sont propres à chaque compte.

Règles appliquées ici :

* **texte propre** — tout titre ou message passe par `text_safety.clean_text` :
  aucune balise HTML, aucun script, jamais de code affiché (V2.2) ;
* **pas de doublon** — une même annonce ou un même événement ne crée qu'une
  notification par personne (`dedupe_key`) ;
* **propriété stricte** — une notification ne peut être lue, marquée ou
  supprimée que par son destinataire.

Le navigateur interroge `GET /api/notifications` toutes les 25 secondes (pause
automatique quand l'onglet est en arrière-plan) et affiche : un compteur sur la
cloche, une bannière discrète pour chaque nouveauté, et un panneau déroulant.
"""
from __future__ import annotations

from datetime import timedelta

from flask import url_for

from .extensions import db
from .models import Notification, User, utcnow, STATUS_ACTIVE
from .text_safety import clean_text, clean_title, looks_like_markup

#: Libellés et icônes par type (utilisés par l'API et les gabarits).
KINDS = {
    "message": {"label": "Message", "icon": "message"},
    "battle": {"label": "Battle", "icon": "zap"},
    "annonce": {"label": "Annonce", "icon": "megaphone"},
    "note": {"label": "Note", "icon": "award"},
    "compte": {"label": "Compte", "icon": "shield"},
    "system": {"label": "Système", "icon": "info"},
}

#: Durée de conservation des notifications déjà lues.
RETENTION_DAYS = 45

#: Nombre maximal de notifications conservées par personne.
MAX_PER_USER = 200

#: Fenêtre de déduplication par défaut (en heures) quand aucun identifiant
#: d'événement n'est fourni : deux titres identiques rapprochés ne produisent
#: qu'une seule notification.
DEDUPE_HOURS = 12

#: Message affiché à la place d'un contenu qui n'était que du balisage.
CONTENU_RETIRE = "Contenu retiré : cette notification ne contenait pas de texte lisible."


def default_icon(kind: str) -> str:
    return KINDS.get(kind, KINDS["system"])["icon"]


def _prune(user_id: int) -> None:
    """Ménage léger : les lues anciennes partent, on garde les 200 dernières."""
    limite = utcnow() - timedelta(days=RETENTION_DAYS)
    Notification.query.filter(
        Notification.user_id == user_id,
        Notification.read_at.isnot(None),
        Notification.read_at < limite,
    ).delete(synchronize_session=False)

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


def _deja_envoyee(user_id: int, kind: str, cle: str, fenetre_heures: float | None) -> bool:
    """Une notification identique existe-t-elle déjà pour cette personne ?"""
    if not cle:
        return False
    query = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.kind == kind,
        Notification.dedupe_key == cle,
    )
    if fenetre_heures:
        query = query.filter(
            Notification.created_at >= utcnow() - timedelta(hours=fenetre_heures)
        )
    return db.session.query(query.exists()).scalar()


def notify(user_id: int | None,
           kind: str,
           title: str,
           body: str = "",
           url: str = "",
           actor=None,
           icon: str | None = None,
           commit: bool = True,
           dedupe_key: str = "",
           dedupe_hours: float | None = DEDUPE_HOURS) -> Notification | None:
    """Crée une notification pour `user_id` (jamais pour soi-même).

    `dedupe_key` identifie l'événement (par exemple ``annonce:42``) : si la
    personne a déjà reçu cette notification, rien n'est créé. Sans clé
    explicite, la déduplication se fait sur le titre pendant `dedupe_hours`.
    """
    if not user_id:
        return None

    actor_id = getattr(actor, "id", actor)
    if actor_id and int(actor_id) == int(user_id):
        return None

    kind = kind if kind in KINDS else "system"
    titre = clean_title(title, limit=120) or "Notification"
    corps = clean_text(body, limit=280, fallback=CONTENU_RETIRE if body else "")

    # `dedupe_hours=0` désactive la déduplication (événement qui peut se répéter).
    if dedupe_hours == 0:
        cle, fenetre = "", None
    elif dedupe_key:
        cle, fenetre = dedupe_key[:120], None
    else:
        cle, fenetre = f"auto:{kind}:{titre.lower()}"[:120], dedupe_hours

    if _deja_envoyee(int(user_id), kind, cle, fenetre):
        return None

    row = Notification(
        user_id=int(user_id),
        kind=kind,
        title=titre,
        body=corps,
        url=(url or "")[:255],
        icon=(icon or default_icon(kind))[:30],
        dedupe_key=cle,
        actor_id=int(actor_id) if actor_id else None,
    )
    db.session.add(row)
    _prune(int(user_id))
    if commit:
        db.session.commit()
    return row


def notify_many(user_ids, kind: str, title: str, body: str = "", url: str = "",
                actor=None, icon: str | None = None, dedupe_key: str = "",
                dedupe_hours: float | None = DEDUPE_HOURS) -> int:
    """Envoie la même notification à plusieurs personnes (annonce, battle…)."""
    envoyees = 0
    acteur = getattr(actor, "id", actor)
    for user_id in sorted(set(int(u) for u in user_ids if u)):
        if acteur and int(user_id) == int(acteur):
            continue
        cree = notify(user_id, kind, title, body, url, actor=actor, icon=icon,
                      commit=False, dedupe_key=dedupe_key, dedupe_hours=dedupe_hours)
        if cree is not None:
            envoyees += 1
    if envoyees:
        db.session.commit()
    return envoyees


def notify_staff(kind: str, title: str, body: str = "", url: str = "", actor=None,
                dedupe_key: str = "", dedupe_hours: float | None = DEDUPE_HOURS) -> int:
    """Prévient tous les administrateurs actifs (demandes à valider…)."""
    ids = [
        row.id for row in User.query.filter(
            User.status == STATUS_ACTIVE, User.role.in_(["super_admin", "admin"])
        ).all()
    ]
    return notify_many(ids, kind, title, body, url, actor=actor,
                       dedupe_key=dedupe_key, dedupe_hours=dedupe_hours)


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


def get_owned(user, notification_id: int) -> Notification | None:
    """Récupère **une** notification de la personne connectée, sinon rien.

    C'est le seul point d'accès utilisé par les routes de modification et de
    suppression : impossible de toucher la notification de quelqu'un d'autre,
    même en devinant son identifiant.
    """
    if user is None or not notification_id:
        return None
    return Notification.query.filter_by(id=int(notification_id), user_id=user.id).first()


def delete(user, notification_id: int) -> bool:
    """Supprime une notification appartenant à `user`. Vrai si supprimée."""
    row = get_owned(user, notification_id)
    if row is None:
        return False
    db.session.delete(row)
    db.session.commit()
    return True


def purge_read(user) -> int:
    """Supprime les notifications déjà lues de cet utilisateur."""
    if user is None:
        return 0
    supprimees = Notification.query.filter(
        Notification.user_id == user.id, Notification.read_at.isnot(None)
    ).delete(synchronize_session=False)
    if supprimees:
        db.session.commit()
    return int(supprimees or 0)


def safe_url(candidate: str) -> str:
    """N'accepte qu'un chemin interne (« /messages ») pour éviter toute redirection ouverte."""
    candidate = (candidate or "").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return url_for("notifications.index")
    return candidate


# ---------------------------------------------------------------------------
# Présentation
# ---------------------------------------------------------------------------
def date_label(moment) -> str:
    """« Aujourd'hui », « Hier » ou la date complète (fuseau de la plateforme)."""
    if not moment:
        return ""
    from flask import current_app, has_app_context

    offset = 3.0
    if has_app_context():
        offset = float(current_app.config.get("TZ_OFFSET", 3))
    local = moment + timedelta(hours=offset)
    aujourdhui = (utcnow() + timedelta(hours=offset)).date()
    jour = local.date()
    if jour == aujourdhui:
        return "Aujourd'hui"
    if jour == aujourdhui - timedelta(days=1):
        return "Hier"
    return local.strftime("%d/%m/%Y")


def time_label(moment) -> str:
    if not moment:
        return ""
    from flask import current_app, has_app_context

    offset = 3.0
    if has_app_context():
        offset = float(current_app.config.get("TZ_OFFSET", 3))
    return (moment + timedelta(hours=offset)).strftime("%H:%M")


def readable_title(row: Notification) -> str:
    return clean_title(row.title, limit=120)


def readable_body(row: Notification) -> str:
    """Corps nettoyé **à l'affichage** : les anciennes lignes sont assainies."""
    brut = row.body or ""
    if not brut:
        return ""
    texte = clean_text(brut, limit=280)
    if not texte and looks_like_markup(brut):
        return CONTENU_RETIRE
    return texte


def as_dict(row: Notification, unread_total: int | None = None) -> dict:
    """Forme JSON envoyée au navigateur (texte déjà nettoyé, jamais de HTML)."""
    corps = readable_body(row)
    return {
        "id": row.id,
        "kind": row.kind,
        "label": KINDS.get(row.kind, KINDS["system"])["label"],
        "title": readable_title(row),
        "body": corps,
        "body_retire": bool(corps == CONTENU_RETIRE),
        "url": safe_url(row.url),
        "icon": row.icon or default_icon(row.kind),
        "at": f"{date_label(row.created_at)} · {time_label(row.created_at)}".strip(" ·"),
        "date": date_label(row.created_at),
        "time": time_label(row.created_at),
        "iso": row.created_at.isoformat() if row.created_at else "",
        "read": row.is_read,
        "actor": (row.actor.full_name or row.actor.username) if row.actor else "",
    }


# ---------------------------------------------------------------------------
# Réparation des notifications déjà en base (V2.2)
# ---------------------------------------------------------------------------
def sanitize_rows(limit: int = 800) -> int:
    """Nettoie les notifications enregistrées avant la V2.2.

    L'affichage est déjà protégé (`readable_body`), mais on corrige aussi la
    base pour que l'historique soit propre partout, y compris dans les exports.
    Aucune ligne n'est supprimée : seul le texte est assaini.
    """
    from sqlalchemy import or_

    lignes = (
        Notification.query.filter(
            or_(
                Notification.title.like("%<%"),
                Notification.title.like("%&%"),
                Notification.body.like("%<%"),
                Notification.body.like("%&%"),
            )
        )
        .limit(limit)
        .all()
    )
    corrigees = 0
    for row in lignes:
        titre = clean_title(row.title or "", limit=120)
        corps = clean_text(row.body or "", limit=280)
        if not corps and looks_like_markup(row.body or ""):
            corps = CONTENU_RETIRE
        if titre != (row.title or "") or corps != (row.body or ""):
            row.title = titre or "Notification"
            row.body = corps
            corrigees += 1
    if corrigees:
        db.session.commit()
    return corrigees


# ---------------------------------------------------------------------------
# Doublons historiques (action explicite du super administrateur)
# ---------------------------------------------------------------------------
def stats() -> dict:
    """Photographie rapide de la table (affichée dans /admin/parametres)."""
    from sqlalchemy import func

    total = Notification.query.count()
    non_lues = Notification.query.filter(Notification.read_at.is_(None)).count()
    groupes = (
        db.session.query(func.count(Notification.id))
        .group_by(Notification.user_id, Notification.kind,
                  Notification.title, Notification.body)
        .having(func.count(Notification.id) > 1)
        .all()
    )
    en_trop = sum(int(row[0]) - 1 for row in groupes)
    return {"total": total, "non_lues": non_lues,
            "groupes": len(groupes), "en_trop": en_trop}


def dedupe_notifications(kind: str | None = "annonce") -> int:
    """Fusionne les notifications strictement identiques d'une même personne.

    Seule la plus récente est conservée. `kind=None` traite tous les types ;
    par défaut, uniquement les annonces (deux messages identiques envoyés à
    deux moments différents restent deux notifications).
    Action réservée au super administrateur, jamais automatique.
    """
    query = Notification.query
    if kind:
        query = query.filter(Notification.kind == kind)
    rows = query.order_by(Notification.created_at.desc(), Notification.id.desc()).all()

    vues: set[tuple] = set()
    supprimees = 0
    for row in rows:
        cle = (row.user_id, row.kind, row.title, row.body)
        if cle in vues:
            db.session.delete(row)
            supprimees += 1
        else:
            vues.add(cle)
    if supprimees:
        db.session.commit()
    return supprimees
