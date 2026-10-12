from __future__ import annotations

import logging

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401  (registers tables on Base.metadata)
from app.db.session import Base, get_engine, get_sessionmaker

LOCAL_USER_ID = "local-default-user-0000000000000"

log = logging.getLogger("sakhisahay.db")


def init_db() -> None:
    """Create tables, add any columns introduced since the DB was created, seed the local user.

    Alembic is planned for the PostgreSQL phase. For the SQLite MVP we use
    ``create_all`` (new tables) plus an additive column sync (new columns on
    existing tables). Nothing here drops or rewrites existing rows.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _sync_missing_columns(engine)
    with get_sessionmaker()() as session:
        ensure_local_user(session)


def _sync_missing_columns(engine: Engine) -> None:
    """ALTER TABLE ... ADD COLUMN for mapped columns that the live table lacks.

    ``create_all`` only creates missing *tables*; databases created before a
    model gained a column would otherwise fail on first query. Defaults come
    from the model's ``server_default`` (or NULL) so existing rows stay valid.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column.type.compile(engine.dialect)}'
                if column.server_default is not None:
                    ddl += f" DEFAULT {column.server_default.arg}"  # type: ignore[union-attr]
                if not column.nullable and column.server_default is None:
                    # SQLite cannot add a NOT NULL column without a default; keep it nullable
                    # at the storage level and let the ORM default fill new rows.
                    pass
                conn.execute(text(ddl))
                log.info("db migration: added column %s.%s", table.name, column.name)


def ensure_local_user(session: Session) -> models.User:
    user = session.scalar(select(models.User).where(models.User.id == LOCAL_USER_ID))
    if user is None:
        user = models.User(id=LOCAL_USER_ID, display_name="Friend", preferred_language="en")
        session.add(user)
        session.commit()
    return user
