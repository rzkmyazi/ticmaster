# -*- coding: utf-8 -*-
"""Fabrique d'application — TIC MASTER #by_Myazirzk."""
from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import (
    Flask, g, jsonify, make_response, redirect, render_template, request, session, url_for,
)
from werkzeug.exceptions import HTTPException

from .extensions import db
from .security.core import (
    csrf_token, load_current_user, validate_csrf, log_audit, client_ip,
)


def create_app(config_object: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    from config import Config, DevConfig, ProdConfig

    env = os.environ.get("FLASK_ENV", "production")
    if config_object == "dev" or (config_object is None and env == "development"):
        app.config.from_object(DevConfig)
    elif config_object == "testing":
        app.config.from_object(DevConfig)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
    else:
        app.config.from_object(ProdConfig)

    app.config.setdefault("SITE_NAME", "TIC MASTER")
    app.config.setdefault("TZ_OFFSET", float(os.environ.get("TZ_OFFSET", "3")))
    app.config.setdefault("PRESENCE_ONLINE_SECONDS", 120)
    app.config.setdefault("SITE_TAGLINE", "")

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    # Chemin absolu : indispensable pour send_from_directory (photos du fil)
    app.config["UPLOAD_FOLDER"] = str(Path(app.config["UPLOAD_FOLDER"]).resolve())
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    # ---------------- Schéma ----------------
    # Les nouvelles tables (fil d'actualité, réactions, commentaires) doivent
    # exister sur les bases déjà en service. `create_all` est idempotent : il ne
    # crée que les tables manquantes et ne touche jamais aux données existantes.
    if app.config.get("AUTO_CREATE_SCHEMA", True):
        try:
            with app.app_context():
                from .schema import ensure_schema

                applied = ensure_schema(app)
                if applied:
                    app.logger.info("Colonnes ajoutées à la base : %s", ", ".join(applied))
        except Exception:  # pragma: no cover - une base injoignable ne doit pas bloquer le boot
            app.logger.exception("Mise à niveau du schéma ignorée (base indisponible ?)")

    # ---------------- Hooks ----------------
    @app.before_request
    def _load_user_and_guard():
        g.csp_nonce = secrets.token_urlsafe(16)
        g.user = load_current_user()
        # Protection CSRF sur toutes les requêtes mutantes
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            if not validate_csrf():
                if request.path.startswith("/api/"):
                    return jsonify({"ok": False, "error": "Jeton CSRF invalide ou expiré. Rechargez la page."}), 400
                return render_template("errors/400.html", message="Jeton de sécurité invalide ou expiré. Merci de recharger la page."), 400
        # Mode « mise à jour du site » (les administrateurs ne sont jamais bloqués)
        from .maintenance import blocks as maintenance_blocks, state as maintenance_state

        maint = maintenance_state()
        if maint["active"] and maintenance_blocks(request.path, getattr(g, "user", None)):
            if request.path.startswith("/api/"):
                return jsonify({
                    "ok": False,
                    "error": "maintenance",
                    "message": maint["message"],
                }), 503
            response = make_response(
                render_template(
                    "errors/maintenance.html",
                    info=maint,
                    requested_path=request.path,
                ),
                503,
            )
            response.headers["Retry-After"] = "300"
            return response

        # Force le changement de mot de passe initial
        if getattr(g, "user", None) and g.user.must_change_password:
            allowed = ("/auth/", "/static/", "/deconnexion", "/a-propos")
            if not any(request.path.startswith(p) for p in allowed):
                if request.path.startswith("/api/"):
                    return jsonify({"ok": False, "error": "Changement de mot de passe requis."}), 428
                return redirect(url_for("auth.change_password"))

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            f"default-src 'self'; "
            f"img-src 'self' data: blob: https:; "
            f"media-src 'self' https:; "
            f"style-src 'self' 'unsafe-inline'; "
            f"script-src 'self' 'nonce-{getattr(g, 'csp_nonce', '')}'; "
            f"font-src 'self' data:; "
            f"connect-src 'self'; "
            f"frame-ancestors 'self'; "
            f"base-uri 'self'; "
            f"form-action 'self'",
        )
        if response.mimetype == "text/html":
            response.headers.setdefault("Cache-Control", "no-store, max-age=0")
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


    # ---------------- Blueprints ----------------
    from .blueprints.auth import bp as auth_bp
    from .blueprints.public import bp as public_bp
    from .blueprints.user import bp as user_bp
    from .blueprints.admin import bp as admin_bp
    from .blueprints.learning import bp as learning_bp
    from .blueprints.social import bp as social_bp
    from .blueprints.exam import bp as exam_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(exam_bp)

    # ---------------- Veille 24 h/24 ----------------
    # Sur PythonAnywhere (toujours en ligne) un fil discret appelle /sante de
    # Render toutes les 5 minutes : le service gratuit ne s'endort plus, le site
    # reste joignable à n'importe quelle heure. Ailleurs : aucun effet.
    from . import veille
    veille.start()

    # ---------------- Template helpers ----------------
    @app.context_processor
    def inject_globals():
        from .models import REACTION_KINDS, REACTION_LABELS, ROLE_LABELS
        from .utils import render_content, human_size

        def fmt_dt(value, fmt="%d/%m/%Y %H:%M"):
            if not value:
                return "—"
            offset = app.config.get("TZ_OFFSET", 0)
            return (value + timedelta(hours=offset)).strftime(fmt)

        def fmt_date(value):
            return fmt_dt(value, "%d/%m/%Y")

        def time_ago(value):
            if not value:
                return "jamais"
            from .models import utcnow
            delta = utcnow() - value
            s = int(delta.total_seconds())
            if s < 60:
                return "à l'instant"
            if s < 3600:
                return f"il y a {s // 60} min"
            if s < 86400:
                return f"il y a {s // 3600} h"
            if s < 2592000:
                return f"il y a {s // 86400} j"
            return fmt_date(value)

        from datetime import datetime as _dt

        from .maintenance import state as maintenance_state

        return dict(
            year=_dt.now().year,
            maintenance=maintenance_state(),
            csrf_token=csrf_token,
            csp_nonce=getattr(g, "csp_nonce", ""),
            current_user=g.get("user"),
            site_name=app.config["SITE_NAME"],
            site_tagline=app.config.get("SITE_TAGLINE", ""),
            role_labels=ROLE_LABELS,
            reaction_kinds=REACTION_KINDS,
            reaction_labels=REACTION_LABELS,
            fmt_dt=fmt_dt,
            fmt_date=fmt_date,
            time_ago=time_ago,
            veille=veille.etat(),
            is_admin_area=request.path.startswith(("/admin", "/gestion")),
            render_content=render_content,
            human_size=human_size,
        )

    # ---------------- Erreurs ----------------
    @app.errorhandler(400)
    def _400(e):
        return render_template("errors/400.html", message=getattr(e, "description", "")), 400

    @app.errorhandler(403)
    def _403(e):
        log_audit("security.forbidden", target=request.path, details=f"ip={client_ip()}")
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def _404(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def _413(e):
        return render_template("errors/400.html", message="Fichier trop volumineux (limite dépassée)."), 413

    @app.errorhandler(429)
    def _429(e):
        return render_template("errors/400.html", message="Trop de requêtes. Merci de patienter quelques instants."), 429

    @app.errorhandler(Exception)
    def _500(e):
        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Erreur serveur non gérée")
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.cli.command("init-db")
    def init_db_command():
        """Crée toutes les tables."""
        db.create_all()
        print("Base de données initialisée.")

    return app
