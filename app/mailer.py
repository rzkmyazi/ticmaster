# -*- coding: utf-8 -*-
"""Envoi d'e-mails optionnel (SMTP). Désactivé par défaut.

Sans configuration SMTP, la plateforme reste 100 % fonctionnelle : les demandes de
réinitialisation sont traitées par le super administrateur depuis son espace.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app


def mail_configured() -> bool:
    return bool(current_app.config.get("MAIL_ENABLED") and current_app.config.get("MAIL_SERVER"))


def send_email(to: str, subject: str, body: str) -> bool:
    """Retourne True si l'e-mail a été accepté par le serveur SMTP."""
    if not to or not mail_configured():
        return False
    cfg = current_app.config
    message = EmailMessage()
    message["From"] = cfg.get("MAIL_FROM", "no-reply@ticmaster.local")
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        if cfg.get("MAIL_USE_TLS", True):
            with smtplib.SMTP(cfg["MAIL_SERVER"], cfg.get("MAIL_PORT", 587), timeout=12) as smtp:
                smtp.starttls()
                if cfg.get("MAIL_USERNAME"):
                    smtp.login(cfg["MAIL_USERNAME"], cfg.get("MAIL_PASSWORD", ""))
                smtp.send_message(message)
        else:
            with smtplib.SMTP_SSL(cfg["MAIL_SERVER"], cfg.get("MAIL_PORT", 465), timeout=12) as smtp:
                if cfg.get("MAIL_USERNAME"):
                    smtp.login(cfg["MAIL_USERNAME"], cfg.get("MAIL_PASSWORD", ""))
                smtp.send_message(message)
        current_app.logger.info("E-mail envoyé à %s", to)
        return True
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning("Échec d'envoi d'e-mail : %s", exc)
        return False
