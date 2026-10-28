# -*- coding: utf-8 -*-
"""Hachage des mots de passe.

Argon2id est utilisé en priorité (recommandation OWASP 2024).
Si la bibliothèque argon2-cffi n'est pas disponible sur l'hébergeur,
on bascule automatiquement sur scrypt (Werkzeug) — jamais de texte clair.
"""
from __future__ import annotations

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError

    _ph = PasswordHasher(
        time_cost=3,        # itérations
        memory_cost=65536,  # 64 MiB
        parallelism=4,
        hash_len=32,
        salt_len=16,
    )
    ARGON2_AVAILABLE = True
except Exception:  # pragma: no cover
    ARGON2_AVAILABLE = False
    _ph = None

from werkzeug.security import generate_password_hash, check_password_hash

_PREFIXES = ("$argon2id$", "$argon2i$", "$argon2d$")


def hash_password(raw: str) -> str:
    if ARGON2_AVAILABLE:
        return _ph.hash(raw)
    return generate_password_hash(raw, method="scrypt")


def verify_password(stored: str, raw: str) -> tuple[bool, bool]:
    """Retourne (ok, needs_rehash)."""
    if not stored or not raw:
        return False, False
    if stored.startswith(_PREFIXES):
        if not ARGON2_AVAILABLE:
            return False, False
        try:
            ok = _ph.verify(stored, raw)
            return bool(ok), _ph.check_needs_rehash(stored)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False, False
        except Exception:
            return False, False
    try:
        ok = check_password_hash(stored, raw)
        return bool(ok), True  # migrer vers Argon2id à la prochaine connexion
    except Exception:
        return False, False


def needs_rehash(stored: str) -> bool:
    return ARGON2_AVAILABLE and stored.startswith(_PREFIXES) and _ph.check_needs_rehash(stored)
