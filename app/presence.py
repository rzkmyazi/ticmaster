# -*- coding: utf-8 -*-
"""Présence, appareils et états de session — TIC MASTER #by_Myazirzk.

Chaque connexion ouvre **sa propre** session serveur (jeton aléatoire, haché
SHA-256 en base). Deux personnes — ou deux appareils d'une même personne — ne
partagent donc jamais de session.

Ce module ne modifie rien : il **lit** l'état des sessions et le traduit en
informations lisibles pour l'administration (qui est en ligne, depuis quel
appareil, dans quel état). Seules `revoke_session()` / `revoke_all_sessions()`
(module `security.core`) ferment volontairement une session.

Vocabulaire (identique dans l'interface) :

===================  ==========================================================
État                 Signification
===================  ==========================================================
``en ligne``         session ouverte ET vue dans les ``PRESENCE_ONLINE_SECONDS``
``inactive``         session ouverte mais sans activité récente
``expirée``          durée de vie dépassée (le cookie ne vaut plus rien)
``révoquée``         fermée explicitement (déconnexion, administration, sécurité)
===================  ==========================================================
"""
from __future__ import annotations

import hashlib
import re
from datetime import timedelta

from flask import current_app

from .extensions import db
from .models import AuditLog, AuthSession, User, utcnow, STATUS_ACTIVE

# ---------------------------------------------------------------------------
# 1. Détection de l'appareil
# ---------------------------------------------------------------------------
#: Navigateurs, du plus spécifique au plus général (l'ordre compte).
_NAVIGATEURS = (
    ("Edg/", "Edge"),
    ("EdgA/", "Edge"),
    ("EdgiOS/", "Edge"),
    ("OPR/", "Opera"),
    ("OPiOS/", "Opera"),
    ("SamsungBrowser/", "Samsung Internet"),
    ("Vivaldi/", "Vivaldi"),
    ("YaBrowser/", "Yandex"),
    ("Firefox/", "Firefox"),
    ("FxiOS/", "Firefox"),
    ("CriOS/", "Chrome"),
    ("Chrome/", "Chrome"),
    ("Chromium/", "Chromium"),
    ("Safari/", "Safari"),
)

#: Systèmes d'exploitation reconnus (motif → libellé).
_SYSTEMES = (
    ("Windows NT 11", "Windows 11"),
    ("Windows NT 10", "Windows 10"),
    ("Windows NT 6.3", "Windows 8.1"),
    ("Windows NT 6.2", "Windows 8"),
    ("Windows NT 6.1", "Windows 7"),
    ("Windows", "Windows"),
    ("Android", "Android"),
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("iPod", "iPod"),
    ("Mac OS X", "macOS"),
    ("CrOS", "ChromeOS"),
    ("Ubuntu", "Linux (Ubuntu)"),
    ("Linux", "Linux"),
    ("FreeBSD", "FreeBSD"),
)

#: Robots et scripts réellement identifiables par leur en-tête.
#: Un simple navigateur inconnu n'est **pas** un robot.
_BOTS = (
    ("googlebot", "Googlebot"),
    ("bingbot", "Bingbot"),
    ("duckduckbot", "DuckDuckBot"),
    ("yandexbot", "Yandex"),
    ("baiduspider", "Baidu"),
    ("semrush", "Semrush"),
    ("ahrefs", "Ahrefs"),
    ("facebookexternalhit", "Facebook"),
    ("slackbot", "Slack"),
    ("telegrambot", "Telegram"),
    ("discordbot", "Discord"),
    ("uptimerobot", "UptimeRobot"),
    ("pingdom", "Pingdom"),
    ("statuscake", "StatusCake"),
    ("python-requests", "script Python"),
    ("python-urllib", "script Python"),
    ("aiohttp", "script Python"),
    ("httpx", "script Python"),
    ("curl/", "curl"),
    ("wget", "wget"),
    ("go-http-client", "sonde Go"),
    ("okhttp", "application Android"),
    ("axios", "script Node"),
    ("node-fetch", "script Node"),
    ("postmanruntime", "Postman"),
    ("insomnia", "Insomnia"),
    ("httpie", "HTTPie"),
    ("libwww-perl", "script Perl"),
    ("scrapy", "Scrapy"),
    ("headlesschrome", "Chrome headless"),
    ("phantomjs", "PhantomJS"),
    ("selenium", "Selenium"),
    ("puppeteer", "Puppeteer"),
    ("playwright", "Playwright"),
    ("apache-httpclient", "client Java"),
    ("java/", "client Java"),
)

_MODEL_ANDROID = re.compile(r"Android[^;]*;\s*([A-Za-z0-9_.\- ]+?)\s+Build/")
_VERSION_ANDROID = re.compile(r"Android\s+([0-9.]+)")


def agent_info(user_agent: str | None) -> dict:
    """Analyse un en-tête ``User-Agent`` et renvoie ses caractéristiques.

    Renvoie un dictionnaire ``{os, browser, kind, model, bot, label, raw}``.
    Aucune conclusion hâtive : un navigateur inconnu reste un **navigateur**
    (``kind = "desktop"``) ; seuls les en-têtes réellement automatisés sont
    classés ``kind = "bot"``.
    """
    ua = (user_agent or "").strip()
    minuscule = ua.lower()

    if not ua:
        return {"os": "", "browser": "", "kind": "unknown", "model": "",
                "bot": "", "label": "Appareil inconnu", "raw": ua}

    # --- robot / script ? (motifs explicites uniquement) ---
    robot = next((libelle for motif, libelle in _BOTS if motif in minuscule), "")
    if not robot and not ua.lower().startswith(("mozilla", "opera")):
        robot = "script"          # en-tête qui n'est pas celui d'un navigateur

    # --- système ---
    systeme = next((libelle for motif, libelle in _SYSTEMES if motif in ua), "")
    if systeme == "Android":
        version = _VERSION_ANDROID.search(ua)
        if version and version.group(1) and version.group(1) not in ("0",):
            systeme = f"Android {version.group(1)}"
    # --- navigateur ---
    navigateur = next((libelle for motif, libelle in _NAVIGATEURS if motif in ua), "")
    # Safari est le navigateur de secours d'iOS : on garde le nom exact
    if systeme in ("iPhone", "iPad", "iPod") and navigateur in ("", "Safari"):
        navigateur = "Chrome" if "CriOS" in ua else ("Firefox" if "FxiOS" in ua else "Safari")
    if not navigateur and ua.lower().startswith("mozilla"):
        navigateur = "navigateur non identifié"

    # --- modèle (souvent présent sur Android) ---
    modele = ""
    if "Android" in ua:
        trouvé = _MODEL_ANDROID.search(ua)
        if trouvé:
            modele = trouvé.group(1).strip()[:40]
            if modele.lower() in ("k", "wv", "mobile", "tablet"):
                modele = ""

    # --- famille d'appareil ---
    if robot:
        famille = "bot"
    elif any(mot in ua for mot in ("iPhone", "iPod", "Android")) and "Mobile" in ua:
        famille = "mobile"
    elif "iPad" in ua or "Tablet" in ua or ("Android" in ua and "Mobile" not in ua):
        famille = "tablet"
    elif systeme:
        famille = "desktop"
    else:
        famille = "unknown"       # navigateur inconnu mais pas un robot

    if robot:
        libelle = f"Script · {robot}" if robot not in ("script",) else "Script"
    else:
        parties = [p for p in (systeme, navigateur) if p]
        libelle = " · ".join(parties) or "Appareil inconnu"

    return {"os": systeme, "browser": navigateur, "kind": famille, "model": modele,
            "bot": robot, "label": libelle[:60], "raw": ua}


def device_label(user_agent: str | None, limit: int = 60) -> str:
    """Libellé lisible de l'appareil (« Android 13 · Chrome »)."""
    return (agent_info(user_agent)["label"] or "Appareil inconnu")[:limit]


def device_kind(user_agent: str | None) -> str:
    """Famille d'appareil : ``mobile``, ``tablet``, ``desktop``, ``bot``…"""
    return agent_info(user_agent)["kind"]


def is_bot(user_agent: str | None) -> bool:
    """Vrai **uniquement** pour un en-tête réellement automatisé."""
    return bool(agent_info(user_agent)["bot"])


def device_fingerprint(user_agent: str | None) -> str:
    """Empreinte courte (sans le jeton) : appareil + navigateur + système.

    Elle sert à repérer « même session, autre appareil » sans jamais stocker
    quoi que ce soit de réversible.
    """
    info = agent_info(user_agent)
    base = "|".join((info["os"], info["browser"], info["model"], info["kind"]))
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 2. États de session
# ---------------------------------------------------------------------------
STATE_ONLINE = "online"
STATE_IDLE = "idle"
STATE_EXPIRED = "expired"
STATE_REVOKED = "revoked"

STATE_LABELS = {
    STATE_ONLINE: "En ligne",
    STATE_IDLE: "Inactive",
    STATE_EXPIRED: "Expirée",
    STATE_REVOKED: "Révoquée",
}

STATE_HINTS = {
    STATE_ONLINE: "Activité dans la fenêtre de présence",
    STATE_IDLE: "Ouverte, mais sans activité récente",
    STATE_EXPIRED: "Durée de vie dépassée : le cookie ne vaut plus rien",
    STATE_REVOKED: "Fermée volontairement (déconnexion ou administration)",
}


def online_seconds() -> int:
    return int(current_app.config.get("PRESENCE_ONLINE_SECONDS", 120))


def online_threshold():
    """Date plancher : au-delà, on considère la session inactive."""
    return utcnow() - timedelta(seconds=online_seconds())


def session_state(row: AuthSession, now=None) -> str:
    """État lisible d'une session : en ligne, inactive, expirée ou révoquée."""
    now = now or utcnow()
    if row.revoked_at:
        return STATE_REVOKED
    if not row.expires_at or row.expires_at <= now:
        return STATE_EXPIRED
    if row.last_seen_at and row.last_seen_at >= now - timedelta(seconds=online_seconds()):
        return STATE_ONLINE
    return STATE_IDLE


# ---------------------------------------------------------------------------
# 3. Lectures d'ensemble
# ---------------------------------------------------------------------------
def _query_open():
    return AuthSession.query.filter(AuthSession.revoked_at.is_(None),
                                    AuthSession.expires_at > utcnow())


def valid_sessions(limit: int = 500) -> list[AuthSession]:
    """Sessions encore valables (ni expirées, ni révoquées)."""
    return _query_open().order_by(AuthSession.last_seen_at.desc()).limit(limit).all()


def online_sessions(limit: int = 500) -> list[AuthSession]:
    """Sessions dont le porteur a donné signe de vie récemment."""
    seuil = online_threshold()
    return (_query_open().filter(AuthSession.last_seen_at >= seuil)
            .order_by(AuthSession.last_seen_at.desc()).limit(limit).all())


def online_users(limit: int = 200) -> list[User]:
    """Comptes distincts actuellement connectés (un utilisateur = une entrée)."""
    seuil = online_threshold()
    return (User.query.filter(User.last_seen_at.isnot(None), User.last_seen_at >= seuil,
                              User.status == STATUS_ACTIVE)
            .order_by(User.last_seen_at.desc()).limit(limit).all())


def session_dict(row: AuthSession, current_id: int | None = None) -> dict:
    """Forme JSON d'une session — **jamais** le jeton, même haché."""
    user = row.user
    info = agent_info(row.user_agent)
    etat = session_state(row)
    return {
        "id": row.id,
        "user_id": row.user_id,
        "name": (user.full_name or user.username) if user else "Compte supprimé",
        "username": user.username if user else "",
        "initials": user.initials if user else "??",
        "role": user.role if user else "user",
        "device": info["label"],
        "os": info["os"],
        "browser": info["browser"],
        "model": info["model"],
        "kind": info["kind"],
        "bot": bool(info["bot"]),
        "ip": row.ip or "—",
        "created_at": row.created_at.isoformat(timespec="seconds") if row.created_at else "",
        "last_seen_at": row.last_seen_at.isoformat(timespec="seconds") if row.last_seen_at else "",
        "expires_at": row.expires_at.isoformat(timespec="seconds") if row.expires_at else "",
        "state": etat,
        "state_label": STATE_LABELS[etat],
        "online": etat == STATE_ONLINE,
        "current": bool(current_id and row.id == current_id),
    }


# ---------------------------------------------------------------------------
# 4. Statistiques
# ---------------------------------------------------------------------------
def _local_day_start():
    """Minuit local (fuseau de la plateforme), exprimé en UTC."""
    offset = float(current_app.config.get("TZ_OFFSET", 3))
    maintenant = utcnow() + timedelta(hours=offset)
    minuit = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    return minuit - timedelta(hours=offset)


def counts() -> dict:
    """Photo instantanée : tout ce qu'affiche le tableau de bord.

    Volontairement calculée en quelques requêtes agrégées : elle reste rapide
    même avec plusieurs milliers de sessions en base.
    """
    seuil = online_threshold()
    ouvertes = AuthSession.query.filter(AuthSession.revoked_at.is_(None),
                                        AuthSession.expires_at > utcnow())
    en_ligne_q = ouvertes.filter(AuthSession.last_seen_at >= seuil)

    en_ligne = en_ligne_q.count()
    total_ouvertes = ouvertes.count()
    expirees = AuthSession.query.filter(AuthSession.revoked_at.is_(None),
                                        AuthSession.expires_at <= utcnow()).count()
    revoquees = AuthSession.query.filter(AuthSession.revoked_at.isnot(None)).count()

    comptes_en_ligne = (db.session.query(AuthSession.user_id)
                        .filter(AuthSession.revoked_at.is_(None),
                                AuthSession.expires_at > utcnow(),
                                AuthSession.last_seen_at >= seuil)
                        .distinct().count())

    appareils = {device_fingerprint(row.user_agent)
                 for row in ouvertes.with_entities(AuthSession.user_agent).all()}
    aujourdhui = AuditLog.query.filter(AuditLog.action == "auth.login",
                                       AuditLog.created_at >= _local_day_start())
    connexions_jour = aujourdhui.count()
    # Un compte est identifiable par son identifiant (connexions suivies) ou par
    # le nom d'utilisateur journalisé : on ne compte jamais deux fois la même
    # personne, même si elle s'est connectée dix fois.
    paires = (db.session.query(AuditLog.actor_id, AuditLog.target)
              .filter(AuditLog.action == "auth.login",
                      AuditLog.created_at >= _local_day_start())
              .all())
    comptes_jour = len({f"{identifiant or ''}|{(cible or '').lower()}" for identifiant, cible in paires})

    return {
        # présence
        "online_users": comptes_en_ligne,
        "online_sessions": en_ligne,
        "idle_sessions": max(0, total_ouvertes - en_ligne),
        "open_sessions": total_ouvertes,
        "expired_sessions": expirees,
        "revoked_sessions": revoquees,
        "accounts": User.query.filter_by(status=STATUS_ACTIVE).count(),
        "devices": len(appareils),
        "connections_today": connexions_jour,
        "accounts_today": comptes_jour,
        "window": online_seconds(),
    }


def snapshot(current_id: int | None = None, limit: int = 300) -> dict:
    """Tout ce qu'il faut pour rafraîchir l'interface en direct."""
    lignes = [session_dict(row, current_id) for row in valid_sessions(limit)]
    return {
        "counts": counts(),
        "sessions": lignes,
        "generated_at": utcnow().isoformat(timespec="seconds"),
    }
