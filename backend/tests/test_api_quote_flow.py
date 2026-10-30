"""End-to-end manual loop: intake, scope, quote, review, confirmation."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.core.config import get_settings


def _sign_in(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    response = client.post(
        "/api/session",
        json={"email": settings.seller_email, "password": settings.seller_password},
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def _intake(client: TestClient) -> tuple[str, dict[str, str]]:
    response = client.post(
        "/api/requirements",
        json={
            "client_name": "Maya Ortiz",
            "client_business": "Fern & Filter Coffee",
            "client_email": "maya@example.com",
            "message": "One page site with our menu and a link to our ordering tool.",
            "budget_minor": 50000,
            "deadline": (date.today() + timedelta(days=30)).isoformat(),
            "assets_ready": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["requirement_id"], {"X-Customer-Token": body["portal_token"]}


def _proposal(client: TestClient, requirement_id: str, headers: dict, **overrides) -> dict:
    payload = {
        "label": "One-page launch",
        "pages": 1,
        "addon_codes": ["external_order_link"],
        "requested_features": ["landing_pages"],
        "assets_ready": True,
    }
    payload.update(overrides)
    response = client.post(
        f"/api/requirements/{requirement_id}/proposals", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_full_manual_quote_flow(client: TestClient, seller, rules) -> None:
    headers = _sign_in(client)
    requirement_id, portal_headers = _intake(client)

    feasible = _proposal(client, requirement_id, headers)
    assert feasible["feasible"] is True
    assert feasible["total_minor"] == 50000

    infeasible = _proposal(
        client,
        requirement_id,
        headers,
        label="Two pages plus copywriting",
        pages=2,
        addon_codes=["copywriting"],
    )
    assert infeasible["feasible"] is False
    assert infeasible["total_minor"] == 75000

    third = client.post(
        f"/api/requirements/{requirement_id}/proposals",
        json={"label": "Third idea", "pages": 1},
        headers=headers,
    )
    assert third.status_code == 409
    assert third.json()["code"] == "proposal_limit"

    portal = client.get("/api/portal", headers=portal_headers)
    assert portal.status_code == 200
    assert len(portal.json()["proposals"]) == 2
    assert portal.json()["quotes"] == []

    rejected_selection = client.post(
        f"/api/portal/proposals/{infeasible['id']}/select", headers=portal_headers
    )
    assert rejected_selection.status_code == 409

    selected = client.post(
        f"/api/portal/proposals/{feasible['id']}/select", headers=portal_headers
    )
    assert selected.status_code == 200
    assert selected.json()["selected_at"] is not None

    blocked_quote = client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": infeasible["id"]},
        headers=headers,
    )
    assert blocked_quote.status_code == 409

    created = client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": feasible["id"], "scope_summary": "One page, external ordering"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    quote = created.json()
    assert quote["status"] == "DRAFT"
    assert quote["total_minor"] == 50000
    assert quote["quote_number"] == 1
    codes = [item["code"] for item in quote["items"]]
    assert "base_page" in codes
    assert "exclusion" in codes
    assert any(item["included"] is False for item in quote["items"])

    premature = client.post(f"/api/portal/quotes/{quote['id']}/confirm", headers=portal_headers)
    assert premature.status_code == 409
    assert premature.json()["code"] == "invalid_transition"

    reviewed = client.post(f"/api/quotes/{quote['id']}/review", headers=headers)
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "REVIEWED"

    confirmed = client.post(f"/api/portal/quotes/{quote['id']}/confirm", headers=portal_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "CONFIRMED"

    again = client.post(f"/api/portal/quotes/{quote['id']}/confirm", headers=portal_headers)
    assert again.status_code == 409

    seller_view = client.get(f"/api/quotes/{quote['id']}")
    assert seller_view.status_code == 200
    assert seller_view.json()["status"] == "CONFIRMED"
    assert seller_view.json()["confirmed_at"] is not None


def test_new_revision_supersedes_the_open_draft(client: TestClient, seller, rules) -> None:
    headers = _sign_in(client)
    requirement_id, portal_headers = _intake(client)
    proposal = _proposal(client, requirement_id, headers)

    quote = client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=headers,
    ).json()

    appended = client.post(
        "/api/portal/messages",
        json={"body": "We also need a contact form.", "expected_revision": 1},
        headers=portal_headers,
    )
    assert appended.status_code == 201
    assert appended.json()["revision"] == 2

    stale = client.post(
        "/api/portal/messages",
        json={"body": "And a blog?", "expected_revision": 1},
        headers=portal_headers,
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "revision_conflict"

    view = client.get("/api/portal", headers=portal_headers).json()
    superseded = next(item for item in view["quotes"] if item["id"] == quote["id"])
    assert superseded["status"] == "SUPERSEDED"
    assert view["requirement"]["revision"] == 2
