# -*- coding: utf-8 -*-
"""Présence et sessions — TIC MASTER #by_Myazirzk.

Chaque connexion ouvre **sa propre** session serveur (jeton aléatoire, haché
SHA-256 en base). Deux personnes, ou deux appareils d'une même personne, ne
partagent donc jamais de session : ce module résume simplement cet état pour
l'administration (qui est en ligne, depuis quel appareil, depuis quand).

Rien ici ne modifie les autres sessions : les fonctions de lecture sont
purement documentaires, seules `revoke_session()` / `revoke_all_sessions()`
ferment volontairement une session.
"""
from __future__ import annotations

import re
from datetime import timedelta

from flask import current_app

from .extensions import db
from .models import AuthSession, User, utcnow, STATUS_ACTIVE


# ---------------------------------------------------------------------------
# Appareil utilisé
# ---------------------------------------------------------------------------
_NAVIGATEURS = (
    ("Edg", "Edge"),
    ("OPR", "Opera"),
    ("SamsungBrowser", "Samsung Internet"),
    ("Firefox", "Firefox"),
    ("CriOS", "Chrome"),
    ("Chrome", "Chrome"),
    ("Safari", "Safari"),
)

_SYSTEMES = (
    ("Windows NT", "Windows"),
    ("Android", "Android"),
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Mac OS X", "Mac"),
    ("CrOS", "ChromeOS"),
    ("Linux", "Linux"),
)


def device_label(user_agent: str | None, limit: int = 60) -> str:
    """Transforme l'en-tête du navigateur en libellé lisible.

    « Mozilla/5.0 (Linux; Android 13) … Chrome/120 » → « Android · Chrome ».
    """
    ua = (user_agent or "").strip()
    if not ua:
        return "Appareil inconnu"
    if ua.startswith("python-requests") or ua.startswith("curl") or not ua.startswith("Mozilla"):
        return "Robot / script"

    systeme = next((libelle for motif, libelle in _SYSTEMES if motif in ua), "")
    navigateur = next((libelle for motif, libelle in _NAVIGATEURS if motif in ua), "")

    # Safari est le navigateur de secours des navigateurs iOS : on garde iOS seul
    if systeme in ("iPhone", "iPad") and (not navigateur or navigateur == "Chrome"):
        navigateur = "Safari" if "CriOS" not in ua else "Chrome"

    if systeme in ("Windows", "Mac") and not navigateur:
        navigateur = "Navigateur"

    libelle = " · ".join(part for part in (systeme, navigateur) if part)
    return (libelle or "Appareil")[:limit]


def device_kind(user_agent: str | None) -> str:
    """Famille d'appareil, utilisée pour l'icône."""
    ua = user_agent or ""
    if any(mot in ua for mot in ("iPhone", "Android", "Mobile")):
        return "mobile"
    if "iPad" in ua or "Tablet" in ua:
        return "tablet"
    return "desktop"


# ---------------------------------------------------------------------------
# Qui est en ligne ?
# ---------------------------------------------------------------------------
def online_seconds() -> int:
    return int(current_app.config.get("PRESENCE_ONLINE_SECONDS", 120))


def online_threshold():
    return utcnow() - timedelta(seconds=online_seconds())


def valid_sessions(limit: int = 500) -> list[AuthSession]:
    """Sessions encore ouvertes, la plus récente d'abord."""
    rows = (
        AuthSession.query.filter(AuthSession.revoked_at.is_(None))
        .order_by(AuthSession.last_seen_at.desc())
        .limit(limit)
        .all()
    )
    return [row for row in rows if row.is_valid]


def online_sessions(limit: int = 500) -> list[AuthSession]:
    """Sessions dont le porteur a donné signe de vie récemment."""
    seuil = online_threshold()
    return [row for row in valid_sessions(limit) if row.last_seen_at and row.last_seen_at >= seuil]


def online_users(limit: int = 200) -> list[User]:
    """Comptes distincts actuellement connectés (un utilisateur = une entrée)."""
    seuil = online_threshold()
    rows = (
        User.query.filter(User.last_seen_at.isnot(None), User.last_seen_at >= seuil,
                          User.status == STATUS_ACTIVE)
        .order_by(User.last_seen_at.desc())
        .limit(limit)
        .all()
    )
    return rows


def counts() -> dict:
    """Photo instantanée affichée dans le tableau de bord."""
    seuil = online_threshold()
    sessions = valid_sessions()
    en_ligne = [row for row in sessions if row.last_seen_at and row.last_seen_at >= seuil]
    return {
        "online_users": len({row.user_id for row in en_ligne}),
        "online_sessions": len(en_ligne),
        "open_sessions": len(sessions),
        "accounts": User.query.filter_by(status=STATUS_ACTIVE).count(),
        "window": online_seconds(),
    }


def session_dict(row: AuthSession) -> dict:
    """Forme JSON d'une session (jamais le jeton : illisible par construction)."""
    user = row.user
    return {
        "id": row.id,
        "user_id": row.user_id,
        "name": (user.full_name or user.username) if user else "Compte supprimé",
        "username": user.username if user else "",
        "initials": user.initials if user else "??",
        "role": user.role if user else "user",
        "device": device_label(row.user_agent),
        "kind": device_kind(row.user_agent),
        "ip": row.ip or "—",
        "created_at": row.created_at.isoformat(timespec="seconds") if row.created_at else "",
        "last_seen_at": row.last_seen_at.isoformat(timespec="seconds") if row.last_seen_at else "",
        "online": bool(row.last_seen_at and row.last_seen_at >= online_threshold()),
        "current": bool(getattr(row, "id", None)),
    }


def snapshot() -> dict:
    """Tout ce qu'il faut pour rafraîchir le tableau de bord en direct."""
    seuil = online_threshold()
    lignes = []
    for row in valid_sessions():
        if not row.last_seen_at or row.last_seen_at < seuil:
            continue
        lignes.append(session_dict(row))
    return {"counts": counts(), "sessions": lignes}
