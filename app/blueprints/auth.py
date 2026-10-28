# -*- coding: utf-8 -*-
"""Authentification : connexion, déconnexion, mots de passe."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for, make_response,
)

from ..extensions import db
from ..models import (
    User, PasswordResetRequest, utcnow, STATUS_ACTIVE,
)
from ..security.core import (
    client_ip, create_auth_session, limiter, log_audit, login_required,
    password_errors, password_ok, revoke_all_sessions, revoke_session, safe_next_url,
)
from ..security.hashing import hash_password, verify_password

bp = Blueprint("auth", __name__, url_prefix="/auth")

GENERIC_ERROR = "Identifiant ou mot de passe incorrect."
LOCKED_ERROR = "Compte temporairement verrouillé après plusieurs tentatives. Réessayez dans quelques minutes."

# Hash factice pour égaliser le temps de réponse quand le compte n'existe pas.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _find_user(identifier: str) -> User | None:
    identifier = (identifier or "").strip()
    if not identifier or len(identifier) > 190:
        return None
    user = User.query.filter(db.func.lower(User.username) == identifier.lower()).first()
    if not user and "@" in identifier:
        user = User.query.filter(db.func.lower(User.email) == identifier.lower()).first()
    return user


def _set_auth_cookie(response, token: str):
    hours = current_app.config.get("AUTH_SESSION_HOURS", 8)
    response.set_cookie(
        current_app.config.get("AUTH_COOKIE_NAME", "tic_auth"),
        token,
        max_age=hours * 3600,
        httponly=True,
        secure=bool(current_app.config.get("SESSION_COOKIE_SECURE")),
        samesite="Lax",
        path="/",
    )
    return response


@bp.route("/login")
def legacy_login():
    return redirect(url_for("auth.login"), code=301)


@bp.route("/connexion", methods=["GET", "POST"])
def login():
    if g.get("user"):
        return redirect(url_for("user.dashboard"))

    error = None
    identifier = ""

    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        password = request.form.get("password") or ""

        # --- 1. Limitation par adresse IP (anti-force brute distribué) ---
        ip_key = f"login:ip:{client_ip()}"
        window = current_app.config.get("LOGIN_IP_WINDOW_MINUTES", 10) * 60
        if limiter.hit(ip_key, current_app.config.get("LOGIN_IP_MAX_ATTEMPTS", 12), window):
            log_audit("auth.rate_limited", target=identifier[:60], details=f"ip={client_ip()}")
            return render_template(
                "errors/429.html",
                message="Trop de tentatives de connexion depuis cet appareil. Patientez quelques minutes.",
            ), 429

        if not identifier or not password:
            error = "Veuillez renseigner votre identifiant et votre mot de passe."
        else:
            user = _find_user(identifier)

            if not user:
                verify_password(_DUMMY_HASH, password)  # temps constant
                log_audit("auth.failed", target=identifier[:60], details="compte inconnu")
                error = GENERIC_ERROR
            elif user.is_locked():
                log_audit("auth.locked", target=user.username)
                error = LOCKED_ERROR
            else:
                ok, _ = verify_password(user.password_hash, password)
                if not ok:
                    user.failed_attempts = (user.failed_attempts or 0) + 1
                    if user.failed_attempts >= current_app.config.get("LOGIN_MAX_ATTEMPTS", 5):
                        user.locked_until = utcnow() + timedelta(
                            minutes=current_app.config.get("LOGIN_LOCK_MINUTES", 15)
                        )
                        user.failed_attempts = 0
                        log_audit("auth.locked", target=user.username, details="seuil atteint")
                    else:
                        log_audit("auth.failed", target=user.username,
                                  details=f"tentative {user.failed_attempts}")
                    db.session.commit()
                    error = GENERIC_ERROR
                elif user.status != STATUS_ACTIVE:
                    log_audit("auth.inactive", target=user.username, details=user.status)
                    error = GENERIC_ERROR
                else:
                    # --- 2. Succès : nouvelle session serveur + cookie ---
                    session.clear()
                    token = create_auth_session(user)
                    session["csrf_token"] = secrets.token_urlsafe(32)
                    log_audit("auth.login", target=user.username, details=f"rôle={user.role}")
                    limiter.reset(ip_key)

                    target = safe_next_url(request.args.get("next") or request.form.get("next"))
                    if not target:
                        target = url_for("admin.dashboard") if user.is_admin else url_for("user.dashboard")

                    response = make_response(redirect(target))
                    return _set_auth_cookie(response, token)

    return render_template(
        "auth/login.html",
        error=error,
        identifier=identifier,
        notice=request.args.get("notice"),
    )


@bp.route("/deconnexion", methods=["GET", "POST"])
def logout():
    row = getattr(g, "auth_session", None)
    if row:
        revoke_session(row)
        db.session.commit()
        log_audit("auth.logout", target=row.user.username if row.user else "")
    session.clear()
    response = make_response(redirect(url_for("public.index")))
    response.delete_cookie(current_app.config.get("AUTH_COOKIE_NAME", "tic_auth"), path="/")
    return response


# ---------------------------------------------------------------------------
# Mot de passe oublié
# ---------------------------------------------------------------------------
@bp.route("/mot-de-passe-oublie", methods=["GET", "POST"])
def forgot_password():
    sent = False
    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        key = f"forgot:ip:{client_ip()}"
        limiter.hit(key, 8, 3600)

        user = _find_user(identifier)
        if user and user.status == STATUS_ACTIVE:
            open_request = PasswordResetRequest.query.filter_by(user_id=user.id, status="pending").first()
            if not open_request:
                db.session.add(PasswordResetRequest(user_id=user.id, status="pending"))
                db.session.commit()
            log_audit("auth.forgot_requested", target=user.username)

            from ..mailer import send_email
            send_email(
                user.email,
                "TIC MASTER — demande de réinitialisation de mot de passe",
                "Votre demande a été transmise à l'administration. "
                "Un administrateur vous communiquera un lien de réinitialisation.",
            )
        else:
            log_audit("auth.forgot_unknown", target=identifier[:60])

        sent = True  # même réponse dans tous les cas (anti-énumération)

    return render_template("auth/forgot.html", sent=sent)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@bp.route("/reinitialiser/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    row = PasswordResetRequest.query.filter_by(token_hash=_token_hash(token)).first()
    valid = bool(row and row.status == "approved" and row.expires_at and row.expires_at > utcnow())
    error = None

    if request.method == "POST" and valid:
        password = request.form.get("password") or ""
        confirm = request.form.get("password_confirm") or ""
        if password != confirm:
            error = "Les deux mots de passe ne correspondent pas."
        elif not password_ok(password):
            error = "Mot de passe trop faible : " + ", ".join(password_errors(password)) + "."
        else:
            user = row.user
            user.set_password(password)
            user.must_change_password = False
            user.failed_attempts = 0
            user.locked_until = None
            row.status = "used"
            revoke_all_sessions(user)
            db.session.commit()
            log_audit("auth.password_reset", target=user.username)
            flash("Votre mot de passe a été réinitialisé. Vous pouvez vous connecter.", "success")
            return redirect(url_for("auth.login"))

    return render_template(
        "auth/reset.html", token=token, token_valid=valid, error=error
    )


# ---------------------------------------------------------------------------
# Changement de mot de passe (utilisateur connecté)
# ---------------------------------------------------------------------------
@bp.route("/changer-mot-de-passe", methods=["GET", "POST"])
@login_required
def change_password():
    error = None
    user = g.user

    if request.method == "POST":
        current = request.form.get("current_password") or ""
        new = request.form.get("new_password") or ""
        confirm = request.form.get("confirm_password") or request.form.get("new_password_confirm") or ""

        if not user.check_password(current):
            error = "Le mot de passe actuel est incorrect."
            log_audit("auth.password_change_failed", target=user.username)
        elif new != confirm:
            error = "Les deux mots de passe ne correspondent pas."
        elif current == new:
            error = "Le nouveau mot de passe doit être différent de l'ancien."
        elif not password_ok(new):
            error = "Mot de passe trop faible : " + ", ".join(password_errors(new)) + "."
        else:
            user.set_password(new)
            user.must_change_password = False
            user.failed_attempts = 0
            user.locked_until = None
            db.session.commit()
            log_audit("auth.password_changed", target=user.username)

            revoke_others = request.form.get("revoke_others") == "1"
            if revoke_others:
                try:
                    revoke_all_sessions(user, except_current=True)
                except Exception:  # pragma: no cover
                    pass
            flash("Votre mot de passe a été mis à jour.", "success")
            return redirect(url_for("admin.dashboard") if user.is_admin else url_for("user.dashboard"))

    return render_template("auth/change_password.html", error=error)
