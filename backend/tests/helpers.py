"""Shared test helpers: one TestClient per role so cookie jars never mix."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.core.config import get_settings

CLIENT_EMAIL = "client@example.com"
CLIENT_PASSWORD = "client-password-1"

_client_seq = 0


def seller_browser() -> tuple[TestClient, dict[str, str]]:
    """A TestClient signed in as the seeded seller, plus CSRF headers."""
    from app.main import app

    browser = TestClient(app)
    settings = get_settings()
    response = browser.post(
        "/api/session",
        json={"email": settings.seller_email, "password": settings.seller_password},
    )
    assert response.status_code == 200, response.text
    return browser, {"X-CSRF-Token": response.json()["csrf_token"]}


def client_browser(
    *, email: str | None = None, password: str = CLIENT_PASSWORD
) -> tuple[TestClient, dict[str, str]]:
    """A TestClient with a freshly registered client, plus CSRF headers.

    Each call without an explicit email registers a new unique address, so one
    test can walk several briefs as several clients.
    """
    global _client_seq
    from app.main import app

    if email is None:
        _client_seq += 1
        email = f"client-{_client_seq}@example.com"
    browser = TestClient(app)
    response = browser.post(
        "/api/clients",
        json={"email": email, "password": password, "display_name": "Maya Ortiz"},
    )
    assert response.status_code == 201, response.text
    return browser, {"X-CSRF-Token": response.json()["csrf_token"]}


def client_sign_in(browser: TestClient, email: str = CLIENT_EMAIL) -> dict[str, str]:
    response = browser.post(
        "/api/client-session",
        json={"email": email, "password": CLIENT_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def brief_payload(**overrides) -> dict:
    payload = {
        "client_name": "Maya Ortiz",
        "client_business": "Fern & Filter Coffee",
        "client_email": "maya@example.com",
        "message": "One page site with our menu and a link to our ordering tool.",
        "budget_minor": 50000,
        "deadline": (date.today() + timedelta(days=30)).isoformat(),
        "assets_ready": True,
    }
    payload.update(overrides)
    return payload


def create_brief(browser: TestClient, headers: dict[str, str], **overrides) -> str:
    """Submit a brief as the signed-in client; returns the requirement id."""
    response = browser.post(
        "/api/requirements", json=brief_payload(**overrides), headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["requirement_id"]


def confirm_test_clarification(requirement_id: str) -> None:
    """Create a confirmed AI clarification for tests that only exercise quotes."""
    from datetime import UTC, datetime
    from uuid import UUID

    from app.clarifications.models import RequirementClarification
    from app.core.db import SessionLocal
    from app.requirements.models import Requirement

    with SessionLocal() as db:
        requirement = db.get(Requirement, UUID(requirement_id))
        assert requirement is not None
        now = datetime.now(UTC)
        row = RequirementClarification(
            requirement_id=requirement.id,
            source_revision=requirement.revision,
            kind="AI",
            status="CONFIRMED",
            questions=[],
            unsupported_requests=[],
            answers="Test fixture confirmation.",
            acknowledged=True,
            acknowledged_unsupported=True,
            created_by=requirement.seller_id,
            confirmed_by=requirement.client_id,
            confirmed_at=now,
        )
        db.add(row)
        db.commit()
