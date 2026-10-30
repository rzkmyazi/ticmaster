# -*- coding: utf-8 -*-
"""Mise à niveau automatique du schéma (sans outil de migration externe).

`db.create_all()` crée les tables manquantes mais **n'ajoute jamais une
colonne** à une table existante. Ce module complète donc le schéma des bases
déjà en service (PostgreSQL sur Render, SQLite sur PythonAnywhere) :

* création des tables absentes (fil d'actualité, réactions, commentaires) ;
* ajout des colonnes manquantes sur `users` (dossier scolaire de l'élève).

Les opérations sont idempotentes : relancer l'application ne change rien.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from .extensions import db

#: Colonnes ajoutées après la première mise en production : nom → type SQL.
USER_COLUMNS = {
    "last_name": "VARCHAR(80)",
    "first_name": "VARCHAR(80)",
    "pseudo": "VARCHAR(64)",
    "class_number": "INTEGER",
    "study_level": "VARCHAR(60)",
    "gender": "VARCHAR(12)",
    "class_group": "INTEGER",
    "avatar_filename": "VARCHAR(255)",
    "avatar_data": "BLOB",          # traduit en BYTEA sur PostgreSQL (voir _type_sql)
}


#: Colonnes ajoutées aux autres tables (messages : remise et transfert).
TABLE_COLUMNS = {
    "messages": {
        "delivered_at": "DATETIME",
        "forwarded_from_id": "INTEGER",
    },
    # V2.2 : déduplication des notifications (une annonce = une notification).
    "notifications": {
        "dedupe_key": "VARCHAR(120)",
    },
}


def _type_sql(sql_type: str) -> str:
    """Adapte un type générique au moteur en service (SQLite / PostgreSQL)."""
    if sql_type == "BLOB" and db.engine.dialect.name != "sqlite":
        return "BYTEA"
    if sql_type == "DATETIME" and db.engine.dialect.name != "sqlite":
        return "TIMESTAMP"
    return sql_type


def ensure_schema(app=None) -> list[str]:
    """Crée les tables manquantes et ajoute les colonnes absentes.

    Retourne la liste des modifications appliquées (vide si tout était à jour).
    """
    applied: list[str] = []
    db.create_all()

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        return applied

    existing = {column["name"] for column in inspector.get_columns("users")}
    for name, sql_type in USER_COLUMNS.items():
        if name in existing:
            continue
        try:
            db.session.execute(text(f"ALTER TABLE users ADD COLUMN {name} {_type_sql(sql_type)}"))
            db.session.commit()
            applied.append(name)
        except Exception:  # colonne ajoutée par un autre worker : on ignore
            db.session.rollback()

    # Autres tables modifiées après la mise en production
    for table, columns in TABLE_COLUMNS.items():
        if table not in tables:
            continue
        presentes = {column["name"] for column in inspector.get_columns(table)}
        for name, sql_type in columns.items():
            if name in presentes:
                continue
            try:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {_type_sql(sql_type)}"))
                db.session.commit()
                applied.append(f"{table}.{name}")
            except Exception:
                db.session.rollback()
    return applied


# ---------------------------------------------------------------------------
# Index de performance (vague 15) — sessions nombreuses, requêtes rapides
# ---------------------------------------------------------------------------
#: Index ajoutés après coup : (table, colonne). `IF NOT EXISTS` est accepté par
#: SQLite et PostgreSQL, l'opération est donc sans risque et rejouable.
EXTRA_INDEXES = (
    ("auth_sessions", "last_seen_at"),
    ("auth_sessions", "expires_at"),
    ("auth_sessions", "revoked_at"),
    ("audit_logs", "created_at"),
    ("notifications", "dedupe_key"),
)


def ensure_indexes() -> list[str]:
    """Crée les index manquants sur les tables les plus sollicitées."""
    applied: list[str] = []
    moteur = db.engine.dialect.name
    for table, colonne in EXTRA_INDEXES:
        nom = f"ix_{table}_{colonne}"
        try:
            if moteur == "postgresql":
                db.session.execute(text(
                    f'CREATE INDEX IF NOT EXISTS "{nom}" ON {table} ({colonne})'))
            else:
                db.session.execute(text(
                    f'CREATE INDEX IF NOT EXISTS "{nom}" ON {table} ({colonne})'))
            db.session.commit()
            applied.append(nom)
        except Exception:            # index déjà présent / droits limités
            db.session.rollback()
    return applied
