"""The model boundary: a narrow fact sheet, server-built scopes, server prices."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.ai.client import ModelReply
from app.ai.models import AiExtraction
from app.core.config import get_settings
from app.proposals.models import Proposal


def _sign_in(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    response = client.post(
        "/api/session",
        json={"email": settings.seller_email, "password": settings.seller_password},
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def _brief(client: TestClient, budget_minor: int = 50000) -> dict:
    response = client.post(
        "/api/requirements",
        json={
            "client_name": "Maya Ortiz",
            "client_business": "Fern & Filter Coffee",
            "client_email": "maya@example.com",
            "message": (
                "Three page site with online ordering, budget 500 dollars, live in two weeks. "
                "No photos ready yet."
            ),
            "budget_minor": budget_minor,
            "deadline": (date.today() + timedelta(days=30)).isoformat(),
            "assets_ready": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _extract(client: TestClient, brief: dict, headers: dict[str, str]):
    return client.post(
        f"/api/requirements/{brief['requirement_id']}/extractions", headers=headers
    )


def _facts(**overrides) -> dict:
    payload = {
        "pages": 3,
        "budget_usd": 500,
        "deadline_days": 14,
        "assets_ready": False,
        "features": ["landing_pages", "on_site_ordering"],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def fake_model(monkeypatch):
    def install(payload: dict | str):
        content = payload if isinstance(payload, str) else json.dumps(payload)

        def _complete(**_kwargs):
            return ModelReply(
                content=content,
                latency_ms=1234,
                prompt_tokens=100,
                completion_tokens=50,
            )

        monkeypatch.setattr("app.ai.service.model_client.complete_json", _complete)

    return install


def test_server_builds_and_prices_two_options(
    client: TestClient, seller, rules, fake_model
) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    fake_model(_facts())

    response = _extract(client, brief, headers)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["model"] == get_settings().model_name
    assert body["prompt_version"] == "facts-v7"
    assert body["unsupported_requests"] == ["on_site_ordering"]
    assert body["record"]["budget_minor"] == 50000
    assert body["source_message_ids"]

    assert len(body["candidates"]) == 2
    primary, narrowed = body["candidates"]
    assert primary["label"] == "As briefed"
    assert primary["total_minor"] == 70000
    assert primary["feasible"] is False
    assert "budget_exceeded" in [violation["code"] for violation in primary["violations"]]

    assert narrowed["pages"] == 1
    assert narrowed["addon_codes"] == ["external_order_link"]
    assert narrowed["total_minor"] == 50000
    assert narrowed["feasible"] is True
    assert "on_site_ordering" not in narrowed["requested_features"]


def test_a_brief_that_fits_yields_one_option(
    client: TestClient, seller, rules, fake_model
) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    fake_model(_facts(pages=1, features=["landing_pages"], assets_ready=True))

    body = _extract(client, brief, headers).json()
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["feasible"] is True
    assert body["candidates"][0]["total_minor"] == 50000


def test_model_supplied_money_is_ignored(
    client: TestClient, seller, rules, fake_model
) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    fake_model(_facts(budget_usd=9999))

    body = _extract(client, brief, headers).json()
    assert body["facts"]["budget_usd"] == 9999
    assert body["record"]["budget_minor"] == 50000
    assert body["candidates"][0]["feasible"] is False


def test_prose_answer_is_rejected_and_recorded(
    client: TestClient, seller, rules, fake_model, db
) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    fake_model("Happy to help! A three page site usually costs around $3,000.")

    response = _extract(client, brief, headers)
    assert response.status_code == 422
    assert response.json()["code"] == "model_output_invalid"

    records = db.scalars(select(AiExtraction)).all()
    assert [record.status for record in records] == ["REJECTED"]
    assert db.scalars(select(Proposal)).all() == []


def test_improvised_keys_are_rejected(client: TestClient, seller, rules, fake_model) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    fake_model({**_facts(), "summary": "Three page site for a coffee bar."})

    response = _extract(client, brief, headers)
    assert response.status_code == 422
    assert response.json()["code"] == "model_output_invalid"


def test_out_of_range_pages_are_rejected(client: TestClient, seller, rules, fake_model) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    fake_model(_facts(pages=99))

    response = _extract(client, brief, headers)
    assert response.status_code == 422


def test_latest_returns_the_last_successful_draft(
    client: TestClient, seller, rules, fake_model
) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    fake_model(_facts())
    _extract(client, brief, headers)

    latest = client.get(
        f"/api/requirements/{brief['requirement_id']}/extractions/latest", headers=headers
    )
    assert latest.status_code == 200
    assert latest.json()["extraction"]["candidates"][0]["label"] == "As briefed"


def test_latest_is_null_before_the_first_draft(client: TestClient, seller, rules) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    latest = client.get(
        f"/api/requirements/{brief['requirement_id']}/extractions/latest", headers=headers
    )
    assert latest.status_code == 200
    assert latest.json() == {"extraction": None}


def test_missing_model_credentials_are_reported(
    client: TestClient, seller, rules, monkeypatch
) -> None:
    headers = _sign_in(client)
    brief = _brief(client)
    settings = get_settings().model_copy(update={"model_api_key": ""})
    monkeypatch.setattr("app.ai.service.get_settings", lambda: settings)

    response = _extract(client, brief, headers)
    assert response.status_code == 503
    assert response.json()["code"] == "model_not_configured"
