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
