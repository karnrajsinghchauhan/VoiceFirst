"""SQLAlchemy engine, declarative base and session scope. Postgres in prod; SQLite in unit tests (D-005)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import DateTime, Engine, TypeDecorator, create_engine, event, text
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import ProductionConfigError


class UtcDateTime(TypeDecorator[datetime]):
    """Stores aware UTC datetimes and refuses naive ones; SQLite drops tzinfo otherwise."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime written to the database")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    pass


def make_engine(url: str, tenant_id: str) -> Engine:
    """One engine serves one tenant. On Postgres every connection declares its tenant, and
    row-level security (migration b2c3d4e5f6a7) filters every table by it. SQLite (unit
    tests only, D-005) has no RLS; isolation is proven on Postgres in tests/e2e."""
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    engine = create_engine(url, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _declare_tenant(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        with dbapi_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (tenant_id,))
        dbapi_conn.commit()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def transaction(factory: sessionmaker[Session]) -> Iterator[Session]:
    """One unit of work: commit on success, roll back and re-raise on any error."""
    session = factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def create_all(engine: Engine) -> None:
    # Importing the model modules registers their tables on Base.metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)


def assert_not_superuser(engine: Engine) -> None:
    """Superusers bypass row-level security, so production must never connect as one."""
    with engine.connect() as conn:
        is_super = conn.execute(
            text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        ).scalar_one()
    if is_super:
        raise ProductionConfigError("the database role is a superuser; RLS would not apply")
