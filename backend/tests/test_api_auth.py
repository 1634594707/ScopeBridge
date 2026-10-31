"""Identity boundary: sessions, roles, CSRF and ownership."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from helpers import (
    CLIENT_EMAIL,
    CLIENT_PASSWORD,
    client_browser,
    create_brief,
    seller_browser,
)

from app.accounts.models import User
from app.core.config import get_settings
from app.core.security import hash_password
from app.requirements.schemas import IntakeRequest
from app.requirements.service import create_requirement


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
    body = client.get("/api/session").json()
    assert body["account"]["role"] == "SELLER"
    response = client.delete("/api/session", headers=headers)
    assert response.status_code == 204
    assert client.get("/api/session").status_code == 401


def test_client_registration_and_round_trip(client: TestClient) -> None:
    response = client.post(
        "/api/clients",
        json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD,
            "display_name": "Maya Ortiz",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["account"]["role"] == "CLIENT"

    duplicate = client.post(
        "/api/clients",
        json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD,
            "display_name": "Maya Again",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "email_already_registered"

    signed_in = client.post(
        "/api/client-session",
        json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD},
    )
    assert signed_in.status_code == 200
    assert signed_in.json()["account"]["role"] == "CLIENT"
    assert client.get("/api/session").json()["account"]["role"] == "CLIENT"

    headers = {"X-CSRF-Token": signed_in.json()["csrf_token"]}
    assert client.delete("/api/session", headers=headers).status_code == 204
    assert client.get("/api/session").status_code == 401


def test_a_role_cannot_sign_in_through_the_other_role(client: TestClient, seller) -> None:
    seller_email = get_settings().seller_email
    client_response = client.post(
        "/api/client-session",
        json={"email": seller_email, "password": get_settings().seller_password},
    )
    assert client_response.status_code == 401

    client_browser(email=CLIENT_EMAIL)
    seller_response = client.post(
        "/api/session",
        json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD},
    )
    assert seller_response.status_code == 401


def test_writes_without_csrf_are_forbidden(client: TestClient, seller) -> None:
    browser, _ = client_browser()
    response = browser.post(
        "/api/requirements",
        json={
            "client_name": "Maya Ortiz",
            "message": "We need a one page site with our menu and an order button.",
            "budget_minor": 50000,
            "deadline": "2030-01-01",
            "assets_ready": True,
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_anonymous_intake_is_unauthorized(client: TestClient) -> None:
    response = client.post(
        "/api/requirements",
        json={
            "client_name": "Maya Ortiz",
            "message": "We need a one page site with our menu and an order button.",
            "budget_minor": 50000,
            "deadline": "2030-01-01",
            "assets_ready": True,
        },
    )
    assert response.status_code == 401


def test_portal_requires_a_client_session(client: TestClient) -> None:
    response = client.get(f"/api/portal/{uuid4()}")
    assert response.status_code == 401


def test_a_client_cannot_touch_another_clients_brief(client: TestClient, seller) -> None:
    browser_a, headers_a = client_browser(email="client-a@example.com")
    brief_id = create_brief(browser_a, headers_a)

    browser_b, headers_b = client_browser(email="client-b@example.com")
    response = browser_b.get(f"/api/portal/{brief_id}")
    assert response.status_code == 403

    message = browser_b.post(
        f"/api/portal/{brief_id}/messages",
        json={"body": "Hello?", "expected_revision": 1},
        headers=headers_b,
    )
    assert message.status_code == 403


def test_a_client_cannot_use_seller_endpoints(client: TestClient, seller) -> None:
    browser, headers = client_browser()
    brief_id = create_brief(browser, headers)

    assert browser.get("/api/requirements").status_code == 403
    assert browser.get(f"/api/requirements/{brief_id}").status_code == 403
    assert (
        browser.post(
            f"/api/requirements/{brief_id}/proposals",
            json={"label": "Sneaky", "pages": 1},
            headers=headers,
        ).status_code
        == 403
    )


def test_a_seller_cannot_use_client_endpoints(client: TestClient, seller) -> None:
    browser, seller_headers = seller_browser()
    assert browser.get("/api/portal/briefs").status_code == 403
    response = browser.post(
        "/api/requirements",
        json={
            "client_name": "Maya Ortiz",
            "message": "We need a one page site with our menu and an order button.",
            "budget_minor": 50000,
            "deadline": "2030-01-01",
            "assets_ready": True,
        },
        headers=seller_headers,
    )
    assert response.status_code == 403


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
    requirement = create_requirement(
        db,
        IntakeRequest(
            client_name="Maya Ortiz",
            message="We need a one page site with our menu and an order button.",
            budget_minor=50000,
            deadline="2030-01-01",
            assets_ready=True,
        ),
        other.id,
        None,
    )

    _sign_in(client)
    response = client.get(f"/api/requirements/{requirement.id}")
    assert response.status_code == 403


def test_seller_deletes_an_unpaid_brief(client: TestClient, seller) -> None:
    browser, headers = client_browser()
    brief_id = create_brief(browser, headers)

    seller_browser_client, seller_headers = seller_browser()
    response = seller_browser_client.delete(
        f"/api/requirements/{brief_id}", headers=seller_headers
    )
    assert response.status_code == 204
    assert (
        seller_browser_client.get(f"/api/requirements/{brief_id}").status_code == 404
    )


def test_anonymous_cannot_delete_a_brief(client: TestClient, seller) -> None:
    response = client.delete(f"/api/requirements/{uuid4()}")
    assert response.status_code == 401


def test_unknown_requirement_returns_404(client: TestClient, seller) -> None:
    _sign_in(client)
    response = client.get(f"/api/requirements/{uuid4()}")
    assert response.status_code == 404
