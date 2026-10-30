"""Test harness.

Tests run against a dedicated `<database>_test` PostgreSQL database created from
DATABASE_URL, so a demo run never touches test data and the other way round.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings

_base = get_settings()
_parts = urlsplit(_base.database_url)
TEST_DB_NAME = (_parts.path.lstrip("/") or "scopebridge") + "_test"
os.environ["DATABASE_URL"] = urlunsplit(_parts._replace(path="/" + TEST_DB_NAME))
get_settings.cache_clear()

from app.accounts import models as accounts_models  # noqa: E402,F401
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.proposals import models as proposals_models  # noqa: E402,F401
from app.quotes import models as quotes_models  # noqa: E402,F401
from app.requirements import models as requirements_models  # noqa: E402,F401
from app.service_rules import models as service_rules_models  # noqa: E402,F401


def _ensure_database() -> None:
    admin_url = urlunsplit(_parts._replace(path="/postgres")).replace(
        "postgresql+psycopg://", "postgresql://"
    )
    with (
        psycopg.connect(admin_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,))
        if cursor.fetchone() is None:
            cursor.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    _ensure_database()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    yield
    names = ", ".join(f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables))
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db() -> Iterator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seller(db) -> object:
    from app.accounts.service import ensure_seller
    from app.core.config import get_settings as settings

    current = settings()
    return ensure_seller(
        db,
        email=current.seller_email,
        password=current.seller_password,
        display_name="ScopeBridge Studio",
    )


@pytest.fixture
def rules(db) -> object:
    from app.service_rules.service import ensure_default_rules

    return ensure_default_rules(db)
