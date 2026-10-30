# -*- coding: utf-8 -*-
"""Coeur sécurité : sessions serveur, CSRF, rate limiting, décorateurs de rôle."""
from __future__ import annotations

import functools
import hashlib
import hmac
import ipaddress
import re
import secrets
from datetime import datetime, timedelta, timezone
from threading import Lock
from urllib.parse import urlparse

from flask import current_app, g, jsonify, redirect, request, session, url_for, abort

from ..extensions import db
from ..models import (
    AuthSession, User, AuditLog, utcnow,
    ROLE_ADMIN, ROLE_SUPER_ADMIN, STATUS_ACTIVE,
)

# ---------------------------------------------------------------------------
# Journalisation d'audit
# ---------------------------------------------------------------------------
def log_audit(action: str, target: str = "", details: str = "", actor: User | None = None) -> None:
    actor = actor or getattr(g, "user", None)
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_label=(actor.username if actor else "système"),
        action=action,
        target=str(target)[:190],
        details=str(details)[:4000],
        ip=client_ip(),
    )
    db.session.add(entry)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def client_ip() -> str:
    # Sur Render / Cloudflare, X-Forwarded-For contient l'IP réelle.
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return (request.remote_addr or "")[:64]


# ---------------------------------------------------------------------------
# CSRF (double protection : jeton aléatoire en session signée + vérification)
# ---------------------------------------------------------------------------
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf() -> bool:
    if request.method in CSRF_SAFE_METHODS:
        return True
    expected = session.get("csrf_token")
    if not expected:
        return False
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not sent:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            sent = payload.get("csrf_token")
    return bool(sent) and hmac.compare_digest(str(expected), str(sent))


# ---------------------------------------------------------------------------
# Rate limiting (mémoire du processus). En multi-workers, ajouter Redis.
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, list[float]] = {}
        self._lock = Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Enregistre une tentative. Retourne True si la limite est dépassée."""
        now = datetime.now(timezone.utc).timestamp()
        with self._lock:
            bucket = [t for t in self._events.get(key, []) if now - t < window_seconds]
            bucket.append(now)
            self._events[key] = bucket
            if len(self._events) > 5000:  # purge mémoire
                cutoff = now - 3600
                for k in list(self._events.keys()):
                    self._events[k] = [t for t in self._events[k] if t > cutoff]
                    if not self._events[k]:
                        self._events.pop(k, None)
            return len(bucket) > limit

    def blocked(self, key: str, limit: int, window_seconds: int) -> bool:
        """La clé a-t-elle dépassé sa limite ? (n'enregistre rien)"""
        return self.count(key, window_seconds) >= limit

    def count(self, key: str, window_seconds: int) -> int:
        now = datetime.now(timezone.utc).timestamp()
        with self._lock:
            return len([t for t in self._events.get(key, []) if now - t < window_seconds])

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)


limiter = RateLimiter()


# ---------------------------------------------------------------------------
# Sessions serveur
# ---------------------------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_auth_session(user: User, remember: bool = False) -> str:
    """Crée une session serveur révocable pour `user`.

    `remember=True` prolonge la session (30 jours par défaut) : le jeton reste
    aléatoire, haché en base, et peut être révoqué à tout moment.
    """
    token = secrets.token_urlsafe(32)
    if remember:
        hours = current_app.config.get("AUTH_REMEMBER_HOURS", 720)
    else:
        # durée choisie par l'administration (Paramètres → Sessions et appareils)
        try:
            from ..settings_service import session_hours
            hours = session_hours()
        except Exception:
            hours = current_app.config.get("AUTH_SESSION_HOURS", 8)
    row = AuthSession(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=utcnow() + timedelta(hours=hours),
        ip=client_ip(),
        user_agent=(request.user_agent.string or "")[:255],
    )
    db.session.add(row)
    user.last_login_at = utcnow()
    user.last_seen_at = utcnow()
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()

    # Règle de l'administrateur : nombre d'appareils simultanés par compte.
    # Elle ne touche JAMAIS les sessions des autres personnes.
    try:
        from ..settings_service import max_devices
        limite = max_devices()
        if limite:
            autres = [
                autre for autre in AuthSession.query.filter_by(user_id=user.id)
                .filter(AuthSession.revoked_at.is_(None))
                .order_by(AuthSession.created_at.desc())
                .all()
                if autre.id != row.id and autre.is_valid
            ]
            # on garde les plus récentes (celle-ci incluse), on ferme les plus anciennes
            for vieille in autres[limite - 1:]:
                vieille.revoked_at = utcnow()
            if any(a.revoked_at for a in autres[limite - 1:]):
                db.session.commit()
    except Exception:                       # une règle illisible ne bloque jamais la connexion
        db.session.rollback()
    return token


def load_current_user():
    """Charge l'utilisateur depuis le cookie de session serveur."""
    token = request.cookies.get(current_app.config.get("AUTH_COOKIE_NAME", "tic_auth"))
    if not token:
        # Autorise aussi l'en-tête pour les appels API (ex. mobile)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
    if not token:
        return None
    row = AuthSession.query.filter_by(token_hash=_hash_token(token)).first()
    if not row or not row.is_valid:
        return None
    user = db.session.get(User, row.user_id)
    if not user or user.status != STATUS_ACTIVE:
        return None
    now = utcnow()
    touched = False
    # Une écriture par minute au maximum et par session : avec plusieurs
    # centaines de personnes connectées, la base n'est pas saturée.
    if not row.last_seen_at or (now - row.last_seen_at).total_seconds() > 60:
        row.last_seen_at = now
        touched = True
    if not user.last_seen_at or (now - user.last_seen_at).total_seconds() > 60:
        user.last_seen_at = now
        touched = True
    if touched:
        db.session.commit()
    _watch_device_change(row)
    g.auth_session = row
    return user


#: Sessions déjà contrôlées pour un changement d'appareil (mémoire du processus).
_UA_CHECKED: set[int] = set()
_UA_CHECKED_MAX = 5000


def _watch_device_change(row: AuthSession) -> None:
    """Signale (une fois) une session utilisée depuis un autre appareil.

    Objectif : détecter un **vol de cookie**. On ne ferme pas la session
    automatiquement — un navigateur peut légitimement se mettre à jour et
    changer son en-tête. On journalise, l'administration décide.
    """
    try:
        from ..presence import device_fingerprint
        if row.id in _UA_CHECKED or row.user_agent is None:
            return
        if len(_UA_CHECKED) > _UA_CHECKED_MAX:
            _UA_CHECKED.clear()
        _UA_CHECKED.add(row.id)
        actuel = (request.user_agent.string or "").strip()
        if not actuel or not row.user_agent:
            return
        if device_fingerprint(actuel) != device_fingerprint(row.user_agent):
            db.session.add(AuditLog(
                actor_id=row.user_id, actor_label="système",
                action="session.device_changed", target=str(row.id),
                details=f"connexion={device_fingerprint(row.user_agent)} "
                        f"requete={device_fingerprint(actuel)}",
                ip=client_ip()))
            db.session.commit()
    except Exception:                     # jamais bloquant pour l'utilisateur
        db.session.rollback()


def revoke_session(row: AuthSession) -> None:
    row.revoked_at = utcnow()


def revoke_all_sessions(user: User, except_current: bool = False) -> int:
    current = getattr(g, "auth_session", None)
    count = 0
    for row in user.auth_sessions:
        if row.revoked_at is None:
            if except_current and current and row.id == current.id:
                continue
            row.revoked_at = utcnow()
            count += 1
    db.session.commit()
    return count


# ---------------------------------------------------------------------------
# Décorateurs d'autorisation (contrôle SERVEUR — le masquage UI ne suffit pas)
# ---------------------------------------------------------------------------
def login_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not getattr(g, "user", None):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Authentification requise."}), 401
            return redirect(url_for("auth.login", next=request.full_path if request.query_string else request.path))
        if g.user.must_change_password and not request.path.startswith(("/auth/", "/api/", "/static/")):
            return redirect(url_for("auth.change_password"))
        return view(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    def decorator(view):
        @functools.wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            if g.user.role not in roles:
                log_audit("access.denied", target=request.path, details=f"rôle={g.user.role}")
                if request.path.startswith("/api/"):
                    return jsonify({"ok": False, "error": "Accès refusé."}), 403
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


admin_required = roles_required(ROLE_SUPER_ADMIN, ROLE_ADMIN)
super_admin_required = roles_required(ROLE_SUPER_ADMIN)


def can_manage_user(actor: User, target: User) -> bool:
    """Un ADMIN ne peut pas toucher un SUPER_ADMIN ni un autre ADMIN."""
    if actor.is_super_admin:
        return True
    if target.id == actor.id:
        return False
    return target.role == "user"


def password_errors(password: str) -> list[str]:
    errors = []
    if len(password) < 10:
        errors.append("au moins 10 caractères")
    if not re.search(r"[A-Z]", password):
        errors.append("une majuscule")
    if not re.search(r"[a-z]", password):
        errors.append("une minuscule")
    if not re.search(r"\d", password):
        errors.append("un chiffre")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("un caractère spécial")
    return errors


PASSWORD_HINT = "10 caractères minimum, avec majuscule, minuscule, chiffre et caractère spécial."


def password_ok(password: str) -> bool:
    return not password_errors(password)


def safe_next_url(target: str | None) -> str | None:
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/"):
        return None
    return target


USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")


def normalize_identifier(value: str) -> str:
    """Forme « aplatie » d'un nom : sans accents, sans espaces ni ponctuation.

    « Rado Andria » → « radoandria » ; permet de retrouver un compte quel que
    soit l'orthographe tapée par l'élève.
    """
    import unicodedata
    norm = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", norm.lower())


def generate_username(full_name: str) -> str:
    """Identifiant lisible tiré du nom : « Kanto Rasoanaivo » → « kanto.rasoanaivo ».

    L'ancien format collait tout et coupait à 14 caractères
    (« kantorasoanaiv ») : l'élève ne reconnaissait pas son identifiant.
    """
    import unicodedata
    norm = unicodedata.normalize("NFKD", full_name or "").encode("ascii", "ignore").decode()
    mots = re.findall(r"[A-Za-z0-9]+", norm.lower())
    if not mots:
        return "utilisateur"
    if len(mots) == 1:
        base = mots[0][:20]
    else:
        base = f"{mots[0][:14]}.{mots[-1][:16]}"
    base = base.strip("._-")[:28] or "utilisateur"
    candidate = base
    i = 1
    while User.query.filter_by(username=candidate).first():
        i += 1
        candidate = f"{base}{i}"
    return candidate


def generate_password(length: int = 14) -> str:
    """Mot de passe temporaire fort, lisible, respectant la politique."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lower = "abcdefghijkmnopqrstuvwxyz"
    digits = "23456789"
    specials = "!@#$%*?"
    core = (
        secrets.choice(alphabet) + secrets.choice(lower) + secrets.choice(digits) + secrets.choice(specials)
        + "".join(secrets.choice(alphabet + lower + digits) for _ in range(length - 4))
    )
    chars = list(core)
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def valid_username(name: str) -> bool:
    return bool(USERNAME_RE.match(name or ""))
