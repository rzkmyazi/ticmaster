# -*- coding: utf-8 -*-
"""Mode « mise à jour du site » — TIC MASTER #by_Myazirzk.

Le super administrateur peut fermer temporairement la plateforme depuis
*Administration → Paramètres → Mise à jour du site*.

Tant que la maintenance est active :
  • les visiteurs et les apprenants reçoivent une page d'attente soignée (HTTP 503) ;
  • les administrateurs et le super administrateur conservent l'accès complet ;
  • un examen déjà commencé peut être terminé (aucune élimination injuste) ;
  • les fichiers techniques (CSS, JS, images, /sante) restent servis.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import g, request

from .extensions import db
from .models import Attempt, Exercise, Setting

KEY_ON = "maintenance_mode"
KEY_MESSAGE = "maintenance_message"
KEY_RETURN = "maintenance_return_at"
KEY_SINCE = "maintenance_since"

DEFAULT_MESSAGE = (
    "Nous modernisons TIC MASTER : nouveaux modules, exercices enrichis et "
    "améliorations de la plateforme. Tout sera de nouveau en ligne très vite — "
    "merci de votre patience."
)

#: Chemins toujours accessibles, même pendant la maintenance.
EXEMPT_PREFIXES = (
    "/static/",
    "/sante",
    "/fichiers/",
    "/favicon.ico",
    "/manifest.webmanifest",
    "/service-worker.js",
    "/auth/connexion",
    "/auth/deconnexion",
    "/admin",
)


def state() -> dict:
    """État courant de la maintenance (calculé une fois par requête)."""
    cached = getattr(g, "_maintenance_state", None)
    if cached is not None:
        return cached

    data = {
        "active": False,
        "message": DEFAULT_MESSAGE,
        "return_at": "",
        "since": None,
        "since_label": "",
    }
    try:
        data["active"] = Setting.get(KEY_ON, "0") == "1"
        if data["active"]:
            data["message"] = (Setting.get(KEY_MESSAGE, "") or "").strip() or DEFAULT_MESSAGE
            data["return_at"] = (Setting.get(KEY_RETURN, "") or "").strip()
            raw = (Setting.get(KEY_SINCE, "") or "").strip()
            if raw:
                try:
                    data["since"] = datetime.fromisoformat(raw)
                except ValueError:
                    data["since"] = None
    except Exception:  # base indisponible : on ne bloque jamais le site par erreur
        db.session.rollback()
        data["active"] = False

    g._maintenance_state = data
    return data


def active() -> bool:
    return state()["active"]


def _active_exam_running(user) -> bool:
    """Vrai si l'apprenant a un examen en cours (on le laisse terminer)."""
    if user is None:
        return False
    try:
        return (
            Attempt.query.join(Exercise, Attempt.exercise_id == Exercise.id)
            .filter(
                Attempt.user_id == user.id,
                Attempt.status == "in_progress",
                Exercise.kind == "exam",
            )
            .first()
            is not None
        )
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return False


def blocks(path: str, user) -> bool:
    """La requête doit-elle être remplacée par la page de maintenance ?"""
    if not state()["active"]:
        return False
    if user is not None and getattr(user, "is_admin", False):
        return False
    if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
        return False
    if path.startswith("/examens") and _active_exam_running(user):
        return False
    return True


def enable(message: str = "", return_at: str = "", author: str = "") -> None:
    """Active la maintenance (idempotent : ne réécrit pas la date de début)."""
    Setting.set(KEY_ON, "1")
    if message:
        Setting.set(KEY_MESSAGE, message.strip()[:600])
    Setting.set(KEY_RETURN, (return_at or "").strip()[:120])
    if Setting.get(KEY_SINCE, "") == "":
        Setting.set(KEY_SINCE, datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"))
    db.session.commit()


def disable() -> None:
    Setting.set(KEY_ON, "0")
    Setting.set(KEY_SINCE, "")
    db.session.commit()


def status_for_api() -> dict:
    st = state()
    return {
        "active": st["active"],
        "message": st["message"],
        "return_at": st["return_at"],
    }
