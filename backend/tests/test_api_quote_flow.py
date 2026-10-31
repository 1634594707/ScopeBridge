"""End-to-end manual loop: intake, scope, quote, review, confirmation."""

from __future__ import annotations

from fastapi.testclient import TestClient
from helpers import client_browser, create_brief, seller_browser


def _proposal(
    browser: TestClient, requirement_id: str, headers: dict, **overrides
) -> dict:
    payload = {
        "label": "One-page launch",
        "pages": 1,
        "addon_codes": ["external_order_link"],
        "requested_features": ["landing_pages"],
        "assets_ready": True,
    }
    payload.update(overrides)
    response = browser.post(
        f"/api/requirements/{requirement_id}/proposals", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_full_manual_quote_flow(seller, rules) -> None:
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)

    feasible = _proposal(seller_client, requirement_id, seller_headers)
    assert feasible["feasible"] is True
    assert feasible["total_minor"] == 50000

    infeasible = _proposal(
        seller_client,
        requirement_id,
        seller_headers,
        label="Two pages plus copywriting",
        pages=2,
        addon_codes=["copywriting"],
    )
    assert infeasible["feasible"] is False
    assert infeasible["total_minor"] == 75000

    third = seller_client.post(
        f"/api/requirements/{requirement_id}/proposals",
        json={"label": "Third idea", "pages": 1},
        headers=seller_headers,
    )
    assert third.status_code == 409
    assert third.json()["code"] == "proposal_limit"

    portal = brief_client.get(f"/api/portal/{requirement_id}")
    assert portal.status_code == 200
    assert len(portal.json()["proposals"]) == 2
    assert portal.json()["quotes"] == []

    rejected_selection = brief_client.post(
        f"/api/portal/requirements/{requirement_id}/proposals/{infeasible['id']}/select",
        headers=brief_headers,
    )
    assert rejected_selection.status_code == 409

    selected = brief_client.post(
        f"/api/portal/requirements/{requirement_id}/proposals/{feasible['id']}/select",
        headers=brief_headers,
    )
    assert selected.status_code == 200
    assert selected.json()["selected_at"] is not None

    blocked_quote = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": infeasible["id"]},
        headers=seller_headers,
    )
    assert blocked_quote.status_code == 409

    created = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": feasible["id"], "scope_summary": "One page, external ordering"},
        headers=seller_headers,
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

    confirm_path = f"/api/portal/requirements/{requirement_id}/quotes/{quote['id']}/confirm"
    premature = brief_client.post(confirm_path, headers=brief_headers)
    assert premature.status_code == 409
    assert premature.json()["code"] == "invalid_transition"

    reviewed = seller_client.post(f"/api/quotes/{quote['id']}/review", headers=seller_headers)
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "REVIEWED"

    confirmed = brief_client.post(confirm_path, headers=brief_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "CONFIRMED"

    again = brief_client.post(confirm_path, headers=brief_headers)
    assert again.status_code == 409

    seller_view = seller_client.get(f"/api/quotes/{quote['id']}")
    assert seller_view.status_code == 200
    assert seller_view.json()["status"] == "CONFIRMED"
    assert seller_view.json()["confirmed_at"] is not None


def test_structured_change_updates_the_recorded_budget(seller, rules) -> None:
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)

    response = brief_client.post(
        f"/api/portal/{requirement_id}/messages",
        json={
            "body": "The owner approved a bigger budget: 800 dollars.",
            "expected_revision": 1,
            "budget_minor": 80000,
            "assets_ready": True,
        },
        headers=brief_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["revision"] == 2
    assert response.json()["budget_minor"] == 80000

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert view["requirement"]["budget_minor"] == 80000

    repriced = _proposal(
        seller_client, requirement_id, seller_headers, label="Three pages", pages=3
    )
    assert repriced["feasible"] is True
    assert repriced["total_minor"] == 70000


def test_new_revision_supersedes_the_open_draft(seller, rules) -> None:
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)
    proposal = _proposal(seller_client, requirement_id, seller_headers)

    quote = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    ).json()

    appended = brief_client.post(
        f"/api/portal/{requirement_id}/messages",
        json={"body": "We also need a contact form.", "expected_revision": 1},
        headers=brief_headers,
    )
    assert appended.status_code == 201
    assert appended.json()["revision"] == 2

    stale = brief_client.post(
        f"/api/portal/{requirement_id}/messages",
        json={"body": "And a blog?", "expected_revision": 1},
        headers=brief_headers,
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "revision_conflict"

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    superseded = next(item for item in view["quotes"] if item["id"] == quote["id"])
    assert superseded["status"] == "SUPERSEDED"
    assert view["requirement"]["revision"] == 2
