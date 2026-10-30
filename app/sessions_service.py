# -*- coding: utf-8 -*-
"""Exploration, nettoyage et révocation des sessions — TIC MASTER #by_Myazirzk.

L'administration a besoin de trois choses, et rien de plus :

1. **voir** les sessions avec des filtres utiles (personne, appareil, état, date) ;
2. **comprendre** ce qui est anormal (script automatisé, appareil inhabituel) ;
3. **agir** : fermer une session, fermer toutes celles d'une personne, nettoyer
   les sessions mortes.

Tout est en lecture seule sauf `purge_stale_sessions()` et `revoke_*()`.
Aucune fonction de ce module ne renvoie ni ne manipule un jeton en clair.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .extensions import db
from .models import AuditLog, AuthSession, User, utcnow
from .presence import (
    STATE_EXPIRED, STATE_IDLE, STATE_ONLINE, STATE_REVOKED, _local_day_start,
    agent_info, device_fingerprint, is_bot, session_dict, session_state,
)

#: Nombre maximum de lignes examinées pour un affichage filtré.
SCAN_LIMIT = 1500

DEVICE_FILTERS = {
    "mobile": "Téléphones",
    "tablet": "Tablettes",
    "desktop": "Ordinateurs",
    "bot": "Scripts et robots",
    "unknown": "Non identifiés",
}

STATE_FILTERS = {
    STATE_ONLINE: "En ligne",
    STATE_IDLE: "Inactive",
    STATE_EXPIRED: "Expirée",
    STATE_REVOKED: "Révoquée",
}

ACTIVITY_FILTERS = {
    "today": "Aujourd'hui",
    "24h": "24 dernières heures",
    "7d": "7 derniers jours",
    "30d": "30 derniers jours",
}


def _since_date(texte: str):
    """« 2026-10-30 » → date de début (tolérant)."""
    texte = (texte or "").strip()
    for motif in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texte, motif)
        except ValueError:
            continue
    return None


def _local_to_utc(moment: datetime) -> datetime:
    from flask import current_app
    offset = float(current_app.config.get("TZ_OFFSET", 3))
    return moment - timedelta(hours=offset)


#: Nombre minimum de sessions pour parler d'« habitude » d'appareil. En dessous,
#: on ne signale rien : deux connexions différentes ne font pas une anomalie.
HABITUDE_MINIMUM = 3


def suspicious_reason(row: AuthSession, habitude: dict | None = None,
                      current_id: int | None = None) -> str:
    """Pourquoi cette session mérite l'attention de l'administration.

    * **script automatisé** : l'en-tête est celui d'un robot connu ;
    * **appareil inhabituel** : la personne se connecte d'habitude depuis un
      autre type d'appareil (au moins ``HABITUDE_MINIMUM`` sessions connues).

    Rien n'est jamais fermé automatiquement : on signale, l'administration agit.
    La session courante de l'administrateur n'est pas signalée (bruit inutile).
    """
    if is_bot(row.user_agent):
        return "script automatisé"
    if habitude and (not current_id or row.id != current_id):
        reference = habitude.get(row.user_id)
        if reference:
            empreinte, occurrences = reference
            if occurrences >= HABITUDE_MINIMUM and device_fingerprint(row.user_agent) != empreinte:
                return "appareil inhabituel"
    return ""


def _dominantes(rows: list[AuthSession]) -> dict:
    """Appareil le plus fréquent par personne, **hors scripts**.

    Les connexions automatisées (vérifications, captures) ne doivent pas
    fabriquer une fausse « habitude » et faire passer un vrai navigateur pour
    un appareil inhabituel.
    """
    compteurs: dict[int, dict[str, int]] = {}
    for row in rows:
        if is_bot(row.user_agent):
            continue
        empreinte = device_fingerprint(row.user_agent)
        compteurs.setdefault(row.user_id, {})
        compteurs[row.user_id][empreinte] = compteurs[row.user_id].get(empreinte, 0) + 1
    resultat = {}
    for uid, valeurs in compteurs.items():
        empreinte = max(valeurs, key=valeurs.get)
        resultat[uid] = (empreinte, valeurs[empreinte])
    return resultat


def list_sessions(*, q: str = "", device: str = "", state: str = "", since: str = "",
                  activity: str = "", sort: str = "recent", page: int = 1,
                  per_page: int = 40, current_id: int | None = None,
                  scan_limit: int = SCAN_LIMIT) -> dict:
    """Liste filtrée de sessions + informations de pagination.

    Les filtres « personne » et « date » sont appliqués en SQL ; l'appareil et
    l'état sont calculés à partir de l'en-tête et des dates, donc en Python.
    On examine au plus ``scan_limit`` sessions : l'affichage reste instantané
    même avec des milliers de lignes en base.
    """
    q = (q or "").strip()
    requete = AuthSession.query

    if q:
        like = f"%{q.lower()}%"
        requete = (requete.join(User, User.id == AuthSession.user_id)
                   .filter(db.or_(db.func.lower(User.username).like(like),
                                  db.func.lower(User.full_name).like(like),
                                  db.func.lower(User.pseudo).like(like))))
    date_min = _since_date(since)
    if date_min:
        requete = requete.filter(AuthSession.created_at >= _local_to_utc(date_min))
    if activity in ACTIVITY_FILTERS:
        jours = {"today": 0, "24h": 1, "7d": 7, "30d": 30}[activity]
        if jours == 0:
            requete = requete.filter(AuthSession.last_seen_at >= _local_day_start())
        else:
            requete = requete.filter(AuthSession.last_seen_at >= utcnow() - timedelta(days=jours))

    if sort == "oldest":
        requete = requete.order_by(AuthSession.created_at.asc())
    elif sort == "user":
        requete = requete.order_by(AuthSession.user_id.asc(), AuthSession.last_seen_at.desc())
    elif sort == "activity":
        requete = requete.order_by(AuthSession.last_seen_at.desc())
    else:
        requete = requete.order_by(AuthSession.created_at.desc())

    rows = requete.limit(scan_limit).all()
    habitude = _dominantes(rows)

    fiches = []
    for row in rows:
        etat = session_state(row)
        if device and agent_info(row.user_agent)["kind"] != device:
            continue
        if state and etat != state:
            continue
        fiche = session_dict(row, current_id)
        fiche["reason"] = suspicious_reason(row, habitude, current_id)
        fiche["suspicious"] = bool(fiche["reason"])
        fiche["row"] = row
        fiches.append(fiche)

    total = len(fiches)
    per_page = max(1, int(per_page))
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(1, int(page)), pages)
    debut = (page - 1) * per_page
    return {
        "items": fiches[debut:debut + per_page],
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "scanned": len(rows),
        "truncated": len(rows) >= scan_limit,
    }


def matching_sessions(*, state: str = "", device: str = "", q: str = "",
                      suspicious_only: bool = False) -> list[AuthSession]:
    """Sessions (objets complets) correspondant aux filtres — pour les actions."""
    resultat = list_sessions(q=q, device=device, state=state, per_page=SCAN_LIMIT)
    if not suspicious_only:
        return [fiche["row"] for fiche in resultat["items"]]
    return [fiche["row"] for fiche in resultat["items"] if fiche["suspicious"]]


def purge_stale_sessions(days: int | None = None) -> int:
    """Supprime définitivement les sessions mortes au-delà de la rétention.

    * une session **révoquée** dont la révocation date de plus de ``days`` jours ;
    * une session **expirée** depuis plus de ``days`` jours.

    Les sessions ouvertes et les sessions récentes ne sont **jamais** touchées.
    Retourne le nombre de lignes supprimées.
    """
    if days is None:
        from .settings_service import session_retention_days
        days = session_retention_days()
    if not days or days <= 0:
        return 0
    limite = utcnow() - timedelta(days=days)

    revoquees = (AuthSession.query
                 .filter(AuthSession.revoked_at.isnot(None), AuthSession.revoked_at < limite)
                 .all())
    expirees = (AuthSession.query
                .filter(AuthSession.revoked_at.is_(None), AuthSession.expires_at < limite)
                .all())
    lignes = revoquees + expirees
    for row in lignes:
        db.session.delete(row)
    if lignes:
        db.session.commit()
    return len(lignes)


#: Horodatage du dernier nettoyage automatique (mémoire du processus).
_LAST_PURGE = {"at": None}


def maybe_purge(min_interval_seconds: int = 3600) -> int:
    """Nettoyage opportuniste, au plus une fois par heure et par processus.

    Appelé à l'ouverture des pages d'administration : aucune tâche planifiée
    n'est nécessaire, et les sessions ouvertes ne sont jamais concernées.
    """
    maintenant = utcnow()
    dernier = _LAST_PURGE["at"]
    if dernier and (maintenant - dernier).total_seconds() < min_interval_seconds:
        return 0
    _LAST_PURGE["at"] = maintenant
    try:
        return purge_stale_sessions()
    except Exception:
        db.session.rollback()
        return 0


def count_stale_sessions(days: int | None = None) -> int:
    """Combien de sessions seraient supprimées par le nettoyage ?"""
    if days is None:
        from .settings_service import session_retention_days
        days = session_retention_days()
    if not days or days <= 0:
        return 0
    limite = utcnow() - timedelta(days=days)
    a = AuthSession.query.filter(AuthSession.revoked_at.isnot(None),
                                 AuthSession.revoked_at < limite).count()
    b = AuthSession.query.filter(AuthSession.revoked_at.is_(None),
                                 AuthSession.expires_at < limite).count()
    return a + b


# ---------------------------------------------------------------------------
# Historique des connexions (journal d'audit)
# ---------------------------------------------------------------------------
HISTORY_ACTIONS = {
    "auth.login": "Connexion",
    "auth.logout": "Déconnexion",
    "auth.failed": "Mot de passe refusé",
    "auth.locked": "Compte verrouillé",
    "auth.rate_limited": "Trop d'essais",
    "auth.inactive": "Compte inactif",
    "session.revoked": "Session fermée par l'administration",
    "user.signed_out_everywhere": "Sessions fermées (administration)",
}


def connection_history(*, q: str = "", action: str = "", since: str = "",
                       page: int = 1, per_page: int = 50) -> dict:
    """Historique des connexions et événements de session (journal d'audit)."""
    requete = AuditLog.query.filter(AuditLog.action.in_(list(HISTORY_ACTIONS)))
    if action in HISTORY_ACTIONS:
        requete = requete.filter(AuditLog.action == action)
    if q:
        like = f"%{q.lower()}%"
        requete = requete.filter(db.or_(db.func.lower(AuditLog.target).like(like),
                                        db.func.lower(AuditLog.actor_label).like(like)))
    date_min = _since_date(since)
    if date_min:
        requete = requete.filter(AuditLog.created_at >= _local_to_utc(date_min))

    total = requete.count()
    per_page = max(1, int(per_page))
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(1, int(page)), pages)
    rows = (requete.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * per_page).limit(per_page).all())
    for row in rows:
        row.history_label = HISTORY_ACTIONS.get(row.action, row.action)
    debut_jour = _local_day_start()
    par_action = dict(
        db.session.query(AuditLog.action, db.func.count(AuditLog.id))
        .filter(AuditLog.action.in_(list(HISTORY_ACTIONS)),
                AuditLog.created_at >= debut_jour)
        .group_by(AuditLog.action).all())
    return {"items": rows, "total": total, "page": page, "pages": pages,
            "per_page": per_page, "actions": HISTORY_ACTIONS,
            "counts_by_action": {cle: par_action.get(cle, 0) for cle in HISTORY_ACTIONS}}
