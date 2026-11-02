"""Every API error, including health and unexpected failures, uses one envelope."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import get_db
from app.main import app


def _broken_db():
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise SQLAlchemyError("database details must not escape")

        def close(self):
            return None

    yield BrokenSession()


def test_health_database_failure_is_an_envelope(monkeypatch) -> None:
    app.dependency_overrides[get_db] = _broken_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    body = response.json()
    assert set(body) == {"code", "message"}
    assert body["code"] == "database_unavailable"
    assert "database details" not in response.text


def test_unexpected_exception_is_a_generic_envelope() -> None:
    def boom() -> None:
        raise RuntimeError("secret path C:\\private\\file.txt")

    app.add_api_route("/api/__review_boom", boom, methods=["GET"])
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/__review_boom")

    assert response.status_code == 500
    body = response.json()
    assert set(body) == {"code", "message"}
    assert body["code"] == "internal_error"
    assert "secret" not in response.text
    assert "Traceback" not in response.text
