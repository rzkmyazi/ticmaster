# -*- coding: utf-8 -*-
"""Réglages de session pilotés par l'administration — TIC MASTER #by_Myazirzk.

Ces valeurs sont modifiables depuis *Administration → Paramètres* sans
redémarrage du serveur : elles sont lues à chaque connexion.
"""
from __future__ import annotations

from .extensions import db
from .models import Setting

#: Nombre d'appareils autorisés en même temps pour un même compte.
#: 0 = illimité (valeur par défaut), 1 = un seul appareil, N = N appareils.
KEY_MAX_DEVICES = "max_devices"
DEFAULT_MAX_DEVICES = 0
HARD_MAX_DEVICES = 20


def max_devices() -> int:
    """Nombre d'appareils simultanés autorisés par compte (0 = illimité)."""
    brut = (Setting.get(KEY_MAX_DEVICES, str(DEFAULT_MAX_DEVICES)) or "").strip()
    if not brut.isdigit():
        return DEFAULT_MAX_DEVICES
    return max(0, min(int(brut), HARD_MAX_DEVICES))


def set_max_devices(value: int) -> int:
    value = max(0, min(int(value), HARD_MAX_DEVICES))
    Setting.set(KEY_MAX_DEVICES, str(value))
    db.session.commit()
    return value


def max_devices_label(value: int | None = None) -> str:
    value = max_devices() if value is None else value
    if value == 0:
        return "Illimité (aucune limite d'appareils)"
    if value == 1:
        return "Un seul appareil à la fois"
    return f"{value} appareils en même temps"


# ---------------------------------------------------------------------------
# Durée de vie et rétention des sessions
# ---------------------------------------------------------------------------
#: Durée de validité d'une connexion (heures). 8 h par défaut ; 30 jours si
#: « Se souvenir de moi » est coché (plafond ci-dessous).
KEY_SESSION_HOURS = "session_hours"
DEFAULT_SESSION_HOURS = 8
MIN_SESSION_HOURS = 1
MAX_SESSION_HOURS = 720          # 30 jours


def session_hours() -> int:
    """Durée de validité d'une session, en heures."""
    brut = (Setting.get(KEY_SESSION_HOURS, str(DEFAULT_SESSION_HOURS)) or "").strip()
    if not brut.isdigit():
        return DEFAULT_SESSION_HOURS
    return max(MIN_SESSION_HOURS, min(int(brut), MAX_SESSION_HOURS))


def set_session_hours(value: int) -> int:
    value = max(MIN_SESSION_HOURS, min(int(value), MAX_SESSION_HOURS))
    Setting.set(KEY_SESSION_HOURS, str(value))
    db.session.commit()
    return value


def session_hours_label(value: int | None = None) -> str:
    value = session_hours() if value is None else value
    if value % 24 == 0 and value >= 24:
        jours = value // 24
        return f"{jours} jour{'s' if jours > 1 else ''}"
    return f"{value} h"


#: Nombre de jours pendant lesquels une session fermée reste consultable
#: dans l'historique. 0 = conservation illimitée (aucun nettoyage).
KEY_SESSION_RETENTION = "session_retention_days"
DEFAULT_SESSION_RETENTION = 30
MAX_SESSION_RETENTION = 365


def session_retention_days() -> int:
    brut = (Setting.get(KEY_SESSION_RETENTION, str(DEFAULT_SESSION_RETENTION)) or "").strip()
    if not brut.isdigit():
        return DEFAULT_SESSION_RETENTION
    return max(0, min(int(brut), MAX_SESSION_RETENTION))


def set_session_retention_days(value: int) -> int:
    value = max(0, min(int(value), MAX_SESSION_RETENTION))
    Setting.set(KEY_SESSION_RETENTION, str(value))
    db.session.commit()
    return value


def session_retention_label(value: int | None = None) -> str:
    value = session_retention_days() if value is None else value
    if value == 0:
        return "Conservation illimitée"
    return f"{value} jour{'s' if value > 1 else ''} puis nettoyage"
