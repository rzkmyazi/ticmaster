from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """SQLite n'applique pas les clés étrangères sans ce réglage.

    Les tables déclarent ``ondelete="CASCADE"`` : en activant le PRAGMA, une
    suppression de compte efface réellement ses données liées (copies, battle,
    messages, publications…), exactement comme sur PostgreSQL en production.
    Sans cela, des lignes orphelines restaient en base après chaque suppression.
    """
    if dbapi_connection.__class__.__module__.split(".")[0] != "sqlite3":
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()
