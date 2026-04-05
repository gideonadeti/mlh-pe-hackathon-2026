import os
from pathlib import Path

from peewee import DatabaseProxy, Model, PostgresqlDatabase

db = DatabaseProxy()

# Serialize DDL when several processes start at once (Gunicorn workers, Compose replicas).
_DDL_LOCK_K1 = 0x4D4C4850
_DDL_LOCK_K2 = 0x43544142


def ensure_tables() -> None:
    """Create application tables if missing (idempotent). Safe under concurrent startup."""
    from app.models import Event, Url, User

    db.connect(reuse_if_open=True)
    try:
        db.execute_sql("SELECT pg_advisory_lock(%s, %s)", (_DDL_LOCK_K1, _DDL_LOCK_K2))
        try:
            db.create_tables([User, Url, Event], safe=True)
        finally:
            db.execute_sql(
                "SELECT pg_advisory_unlock(%s, %s)", (_DDL_LOCK_K1, _DDL_LOCK_K2)
            )
    finally:
        if not db.is_closed():
            db.close()


class BaseModel(Model):
    class Meta:
        database = db


def _database_password() -> str:
    path = os.environ.get("DATABASE_PASSWORD_FILE")
    if path:
        p = Path(path)
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()
    return os.environ.get("DATABASE_PASSWORD", "postgres")


def init_db(app):
    database = PostgresqlDatabase(
        os.environ.get("DATABASE_NAME", "hackathon_db"),
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        user=os.environ.get("DATABASE_USER", "postgres"),
        password=_database_password(),
    )
    db.initialize(database)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()
