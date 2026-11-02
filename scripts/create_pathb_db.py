"""Create (or reuse) the isolated ``scopebridge_pathb`` database.

The demo database itself is never modified; this only adds a new database on the
same PostgreSQL server. The printed URL is captured by the PowerShell wrapper.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

import psycopg  # noqa: E402

from app.core.config import get_settings  # noqa: E402

DB_NAME = "scopebridge_pathb"


def main() -> None:
    base_url = get_settings().database_url
    parts = urlsplit(base_url)
    admin_dsn = urlunsplit(parts._replace(path="/postgres")).replace(
        "postgresql+psycopg://", "postgresql://"
    )
    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            if cursor.fetchone() is None:
                cursor.execute(f'CREATE DATABASE "{DB_NAME}"')

    pathb_url = urlunsplit(parts._replace(path=f"/{DB_NAME}"))
    print(pathb_url)


if __name__ == "__main__":
    main()
