"""Identity boundary: sessions, CSRF, portal tokens and ownership."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.accounts.models import User
from app.core.config import get_settings
from app.core.security import hash_password
from app.requirements.schemas import IntakeRequest
from app.requirements.service import create_requirement


def _intake_payload() -> dict:
    return {
        "client_name": "Maya Ortiz",
        "client_business": "Fern & Filter Coffee",
        "client_email": "maya@example.com",
        "message": "We need a one page site with our menu and an order button.",
        "budget_minor": 50000,
        "deadline": (date.today() + timedelta(days=30)).isoformat(),
        "assets_ready": True,
    }


def _sign_in(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    response = client.post(
        "/api/session",
        json={"email": settings.seller_email, "password": settings.seller_password},
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_sign_in_rejects_a_wrong_password(client: TestClient, seller) -> None:
    settings = get_settings()
    response = client.post(
        "/api/session",
        json={"email": settings.seller_email, "password": "not-the-password"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_repeated_failures_are_throttled(client: TestClient, seller) -> None:
    settings = get_settings()
    for _ in range(5):
        client.post(
            "/api/session",
            json={"email": settings.seller_email, "password": "wrong-password"},
        )
    response = client.post(
        "/api/session",
        json={"email": settings.seller_email, "password": settings.seller_password},
    )
    assert response.status_code == 429
    assert response.json()["code"] == "too_many_attempts"


def test_session_round_trip(client: TestClient, seller) -> None:
    headers = _sign_in(client)
    assert client.get("/api/session").status_code == 200
    response = client.delete("/api/session", headers=headers)
    assert response.status_code == 204
    assert client.get("/api/session").status_code == 401


def test_writes_without_csrf_are_forbidden(client: TestClient, seller) -> None:
    _sign_in(client)
    created = client.post("/api/requirements", json=_intake_payload())
    assert created.status_code == 201
    requirement_id = created.json()["requirement_id"]

    response = client.post(
        f"/api/requirements/{requirement_id}/messages",
        json={"body": "Any update?", "expected_revision": 1},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_portal_rejects_unknown_token(client: TestClient) -> None:
    response = client.get("/api/portal", headers={"X-Customer-Token": "not-a-real-token"})
    assert response.status_code == 401


def test_seller_cannot_read_another_sellers_requirement(
    client: TestClient, seller, db
) -> None:
    other = User(
        email="other@scopebridge.local",
        display_name="Other Studio",
        password_hash=hash_password("another-password"),
    )
    db.add(other)
    db.commit()
    requirement, _ = create_requirement(db, IntakeRequest(**_intake_payload()), other.id)

    _sign_in(client)
    response = client.get(f"/api/requirements/{requirement.id}")
    assert response.status_code == 403


def test_unknown_requirement_returns_404(client: TestClient, seller) -> None:
    _sign_in(client)
    response = client.get(f"/api/requirements/{uuid4()}")
    assert response.status_code == 404
