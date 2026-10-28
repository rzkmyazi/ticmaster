# -*- coding: utf-8 -*-
"""
Configuration de TIC MASTER #by_Myazirzk
Toutes les valeurs sensibles proviennent de variables d'environnement (.env).
Aucun secret n'est codé en dur en production.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _database_uri() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        instance = BASE_DIR / "instance"
        instance.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{instance / 'ticmaster.db'}"
    # Render/Heroku fournissent parfois "postgres://" (non supporté par SQLAlchemy 2)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    # SQLAlchemy 2.1 utilise psycopg (v3) par défaut ; on force le pilote psycopg2,
    # seul présent dans requirements.txt (évite « No module named 'psycopg' »).
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


class Config:
    # --- Sécurité de base -------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me-please")
    ENV_NAME = os.environ.get("FLASK_ENV", "production")

    # --- Base de données --------------------------------------------------
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Crée automatiquement les tables manquantes au démarrage (idempotent)
    AUTO_CREATE_SCHEMA = os.environ.get("AUTO_CREATE_SCHEMA", "1") not in ("0", "false", "False")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Cookies / sessions ----------------------------------------------
    SESSION_COOKIE_NAME = "tic_session"
    AUTH_COOKIE_NAME = os.environ.get("AUTH_COOKIE_NAME", "tic_auth")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    AUTH_SESSION_HOURS = int(os.environ.get("AUTH_SESSION_HOURS", "8"))

    # --- Anti brute-force -------------------------------------------------
    LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_LOCK_MINUTES = int(os.environ.get("LOGIN_LOCK_MINUTES", "15"))
    LOGIN_IP_MAX_ATTEMPTS = int(os.environ.get("LOGIN_IP_MAX_ATTEMPTS", "12"))
    LOGIN_IP_WINDOW_MINUTES = int(os.environ.get("LOGIN_IP_WINDOW_MINUTES", "10"))

    # --- Uploads ----------------------------------------------------------
    UPLOAD_FOLDER = str(Path(os.environ.get("UPLOAD_FOLDER", BASE_DIR / "instance" / "uploads")))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_MB", "30")) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {
        "png", "jpg", "jpeg", "gif", "webp", "svg",
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "txt", "csv", "zip", "mp4", "webm", "mp3",
    }

    # --- Messagerie / e-mail (optionnel) ----------------------------------
    MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "0") == "1"
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "no-reply@ticmaster.local")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1") == "1"

    # --- Divers -----------------------------------------------------------
    SITE_NAME = os.environ.get("SITE_NAME", "TIC MASTER")
    SITE_TAGLINE = os.environ.get("SITE_TAGLINE", "Plateforme de formation aux Technologies de l'Information et de la Communication")
    SUPER_ADMIN_USERNAME = os.environ.get("SUPER_ADMIN_USERNAME", "Myazirzk")
    PRESENCE_ONLINE_SECONDS = int(os.environ.get("PRESENCE_ONLINE_SECONDS", "120"))
    TIMEZONE_LABEL = os.environ.get("TIMEZONE_LABEL", "UTC")


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1") == "1"
