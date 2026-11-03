"""Clarification gate: AI facts reviewed, manual exception explicit."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi.testclient import TestClient
from helpers import client_browser, create_brief, seller_browser

from app.ai.client import ModelReply
from app.clarifications.models import RequirementClarification
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.requirements.models import Requirement


def _proposal(seller: TestClient, headers: dict, requirement_id: str) -> dict:
    response = seller.post(
        f"/api/requirements/{requirement_id}/proposals",
        json={
            "label": "One page",
            "pages": 1,
            "addon_codes": ["external_order_link"],
            "requested_features": ["landing_pages"],
            "assets_ready": True,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _fact_reply(monkeypatch) -> None:
    facts = {
        "pages": 1,
        "budget_usd": 500,
        "deadline_days": 30,
        "assets_ready": True,
        "features": ["landing_pages", "on_site_ordering"],
    }

    def _complete(**_kwargs):
        return ModelReply(content=json.dumps(facts), latency_ms=10)

    monkeypatch.setattr("app.ai.service.model_client.complete_json", _complete)


def _insert_pending_ai(requirement_id: str, questions: list[str]) -> str:
    with SessionLocal() as db:
        requirement = db.get(Requirement, UUID(requirement_id))
        assert requirement is not None
        row = RequirementClarification(
            requirement_id=requirement.id,
            source_revision=requirement.revision,
            kind="AI",
            status="PENDING",
            questions=questions,
            unsupported_requests=["on_site_ordering"],
            created_by=requirement.seller_id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return str(row.id)


def test_quote_is_rejected_without_a_current_clarification(seller, rules) -> None:
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)
    proposal = _proposal(seller_client, seller_headers, requirement_id)

    response = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "clarification_required"
    assert response.json()["details"]["status"] == "NONE"


def test_ai_clarification_must_be_confirmed_before_a_quote(
    seller, rules, monkeypatch
) -> None:
    _fact_reply(monkeypatch)
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)
    proposal = _proposal(seller_client, seller_headers, requirement_id)

    extraction = seller_client.post(
        f"/api/requirements/{requirement_id}/extractions", headers=seller_headers
    )
    assert extraction.status_code == 201, extraction.text

    detail = seller_client.get(f"/api/requirements/{requirement_id}").json()
    clarification = detail["clarification"]
    assert clarification["kind"] == "AI"
    assert clarification["status"] == "PENDING"
    assert "on_site_ordering" in clarification["unsupported_requests"]

    blocked = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "clarification_required"
    assert blocked.json()["details"]["status"] == "PENDING"

    confirm_path = (
        f"/api/portal/requirements/{requirement_id}/clarifications/"
        f"{clarification['id']}/confirm"
    )
    no_ack = brief_client.post(
        confirm_path, json={"answers": "", "acknowledged": False}, headers=brief_headers
    )
    assert no_ack.status_code == 422
    assert no_ack.json()["code"] == "clarification_acknowledgement_required"

    unsupported_not_ack = brief_client.post(
        confirm_path,
        json={"answers": "", "acknowledged": True, "acknowledged_unsupported": False},
        headers=brief_headers,
    )
    assert unsupported_not_ack.status_code == 422
    assert unsupported_not_ack.json()["code"] == "unsupported_acknowledgement_required"

    confirmed = brief_client.post(
        confirm_path,
        json={"answers": "", "acknowledged": True, "acknowledged_unsupported": True},
        headers=brief_headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["kind"] == "AI"
    assert confirmed.json()["status"] == "CONFIRMED"

    quote = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    )
    assert quote.status_code == 201, quote.text
    assert quote.json()["clarification"]["kind"] == "AI"
    assert quote.json()["clarification"]["status"] == "CONFIRMED"


def test_ai_questions_require_answers(seller, rules) -> None:
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)
    proposal = _proposal(seller_client, seller_headers, requirement_id)
    clarification_id = _insert_pending_ai(requirement_id, ["Do you have photos ready?"])

    confirm_path = (
        f"/api/portal/requirements/{requirement_id}/clarifications/"
        f"{clarification_id}/confirm"
    )
    empty = brief_client.post(
        confirm_path,
        json={"answers": "", "acknowledged": True, "acknowledged_unsupported": True},
        headers=brief_headers,
    )
    assert empty.status_code == 422
    assert empty.json()["code"] == "clarification_answers_required"

    answered = brief_client.post(
        confirm_path,
        json={
            "answers": "No photos yet; we will send them next week.",
            "acknowledged": True,
            "acknowledged_unsupported": True,
        },
        headers=brief_headers,
    )
    assert answered.status_code == 200, answered.text

    quote = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    )
    assert quote.status_code == 201, quote.text


def test_manual_clarification_is_persisted_and_quote_continues(
    seller, rules, monkeypatch
) -> None:
    settings = get_settings().model_copy(update={"model_api_key": "", "model_name": ""})
    monkeypatch.setattr("app.clarifications.service.get_settings", lambda: settings)

    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)
    proposal = _proposal(seller_client, seller_headers, requirement_id)

    manual = seller_client.post(
        f"/api/requirements/{requirement_id}/clarifications/manual",
        json={
            "note": "Model key is absent; the seller reviewed the brief by hand.",
            "reason_code": "model_not_configured",
        },
        headers=seller_headers,
    )
    assert manual.status_code == 201, manual.text
    body = manual.json()
    assert body["kind"] == "MANUAL"
    assert body["status"] == "CONFIRMED"
    assert body["reason_code"] == "model_not_configured"

    detail = seller_client.get(f"/api/requirements/{requirement_id}").json()
    assert detail["clarification"]["kind"] == "MANUAL"
    portal = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert portal["clarification"]["kind"] == "MANUAL"
    assert "not AI-assisted" not in portal["clarification"]["note"]
    assert portal["clarification"]["note"].startswith("Model key is absent")

    quote = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    )
    assert quote.status_code == 201, quote.text
    assert quote.json()["clarification"]["kind"] == "MANUAL"

    reviewed = seller_client.post(
        f"/api/quotes/{quote.json()['id']}/review", headers=seller_headers
    )
    assert reviewed.status_code == 200
    confirmed = brief_client.post(
        f"/api/portal/requirements/{requirement_id}/quotes/{quote.json()['id']}/confirm",
        headers=brief_headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "CONFIRMED"


def test_manual_clarification_requires_a_model_failure_or_missing_config(
    seller, rules
) -> None:
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)

    response = seller_client.post(
        f"/api/requirements/{requirement_id}/clarifications/manual",
        json={
            "note": "Trying to bypass the model without a reason.",
            "reason_code": "model_unavailable",
        },
        headers=seller_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "model_required"
