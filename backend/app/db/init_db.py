from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401  (registers tables on Base.metadata)
from app.db.session import Base, get_engine, get_sessionmaker

LOCAL_USER_ID = "local-default-user-0000000000000"


def init_db() -> None:
    """Create tables and seed the single local-mode user.

    Migrations (Alembic) are planned for the PostgreSQL phase; for the SQLite
    MVP, create_all is sufficient and idempotent.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    with get_sessionmaker()() as session:
        ensure_local_user(session)


def ensure_local_user(session: Session) -> models.User:
    user = session.scalar(select(models.User).where(models.User.id == LOCAL_USER_ID))
    if user is None:
        user = models.User(id=LOCAL_USER_ID, display_name="Friend", preferred_language="en")
        session.add(user)
        session.commit()
    return user
