"""Payment boundary: lock, capture, unknown outcomes, recovery, snapshot."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from helpers import client_browser, create_brief, seller_browser

from app.paypal import client as paypal

ORDER_ID = "ORDER-SANDBOX-1"
CAPTURE_ID = "CAPTURE-SANDBOX-1"
TOTAL = 50000


def _order_payload(
    order_id: str = ORDER_ID, status: str = "COMPLETED", value: str = "500.00"
) -> dict:
    captures = []
    if status == "COMPLETED":
        captures = [
            {
                "id": CAPTURE_ID,
                "status": "COMPLETED",
                "amount": {"value": value, "currency_code": "USD"},
                "payee": {"merchant_id": "MERCHANT-1"},
            }
        ]
    return {
        "id": order_id,
        "status": status,
        "payer": {"email_address": "buyer@example.com"},
        "purchase_units": [
            {
                "reference_id": "quote-1",
                "payments": {"captures": captures},
            }
        ],
    }


def _confirmed_quote() -> tuple[TestClient, dict, TestClient, dict, str, str]:
    """Walk one brief to a confirmed quote.

    Returns (seller browser, seller headers, client browser, client headers,
    requirement id, quote id).
    """
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)

    proposal = seller_client.post(
        f"/api/requirements/{requirement_id}/proposals",
        json={
            "label": "One page",
            "pages": 1,
            "addon_codes": ["external_order_link"],
            "requested_features": ["landing_pages"],
            "assets_ready": True,
        },
        headers=seller_headers,
    ).json()
    brief_client.post(
        f"/api/portal/requirements/{requirement_id}/proposals/{proposal['id']}/select",
        headers=brief_headers,
    )

    quote = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    ).json()
    seller_client.post(f"/api/quotes/{quote['id']}/review", headers=seller_headers)
    confirmed = brief_client.post(
        f"/api/portal/requirements/{requirement_id}/quotes/{quote['id']}/confirm",
        headers=brief_headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    return seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote["id"]


def _attempt_path(requirement_id: str, quote_id: str) -> str:
    return f"/api/portal/requirements/{requirement_id}/quotes/{quote_id}/payment-attempts"


@pytest.fixture
def fake_paypal(monkeypatch):
    state = {
        "create_error": None,
        "capture_error": None,
        "capture_payload": None,
        "order_payload": None,
        "created": 0,
    }

    def create_order(**kwargs):
        if state["create_error"] is not None:
            raise state["create_error"]
        state["created"] += 1
        order_id = f"{ORDER_ID}-{state['created']}"
        state["order_payload"] = _order_payload(
            order_id, "APPROVED", f"{kwargs['amount_minor'] / 100:.2f}"
        )
        return paypal.PayPalOrder(
            id=order_id,
            status="APPROVED",
            approve_url="https://sandbox.paypal.com/checkoutnow?token=" + order_id,
            raw=state["order_payload"],
        )

    def capture_order(order_id: str, *, request_id: str):
        if state["capture_error"] is not None:
            raise state["capture_error"]
        if state["capture_payload"] is not None:
            return state["capture_payload"]
        return _order_payload("COMPLETED")

    def get_order(order_id: str):
        if state["order_payload"] is None:
            state["order_payload"] = _order_payload(order_id, "APPROVED")
        assert state["order_payload"]["id"] == order_id
        return state["order_payload"]

    monkeypatch.setattr("app.paypal.client.create_order", create_order)
    monkeypatch.setattr("app.paypal.client.capture_order", capture_order)
    monkeypatch.setattr("app.paypal.client.get_order", get_order)
    return state


def test_payment_locks_the_quote_and_returns_an_approval_link(seller, rules, fake_paypal) -> None:
    seller_client, _, brief_client, brief_headers, requirement_id, quote_id = _confirmed_quote()

    response = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-0001"},
    )
    assert response.status_code == 200, response.text
    attempt = response.json()
    assert attempt["status"] == "AWAITING_APPROVAL"
    assert attempt["paypal_order_id"].startswith(ORDER_ID)
    assert attempt["approve_url"].startswith("https://sandbox.paypal.com/")

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert view["quotes"][0]["status"] == "PAYMENT_LOCKED"
    assert view["payments"][0]["id"] == attempt["id"]

    replay = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-0001"},
    )
    assert replay.json()["id"] == attempt["id"]

    other_key = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-0002"},
    )
    assert other_key.json()["id"] == attempt["id"]
    assert fake_paypal["created"] == 1


def test_capture_completes_the_quote_and_freezes_a_snapshot(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-1001"},
    ).json()

    captured = brief_client.post(
        f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers
    )
    assert captured.status_code == 200, captured.text
    assert captured.json()["status"] == "COMPLETED"
    assert captured.json()["paypal_capture_id"] == CAPTURE_ID

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert view["quotes"][0]["status"] == "PAID"
    assert view["order"]["amount_minor"] == TOTAL
    assert view["order"]["capture_id"] == CAPTURE_ID
    assert len(view["order"]["items"]) >= 2

    again = brief_client.post(
        f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers
    )
    assert again.status_code == 200
    assert again.json()["status"] == "COMPLETED"

    order = seller_client.get(f"/api/orders/{view['order']['id']}")
    assert order.status_code == 200
    assert order.json()["order_id"].startswith(ORDER_ID)


def test_amount_mismatch_stays_in_reconciling(seller, rules, fake_paypal) -> None:
    _, _, brief_client, brief_headers, requirement_id, quote_id = _confirmed_quote()
    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-2001"},
    ).json()

    fake_paypal["capture_payload"] = _order_payload(status="COMPLETED", value="999.00")
    captured = brief_client.post(
        f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers
    )
    assert captured.json()["status"] == "RECONCILING"
    assert captured.json()["error_code"] == "capture_amount_mismatch"

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert view["quotes"][0]["status"] == "PAYMENT_LOCKED"


def test_lost_capture_response_is_recovered_by_reconcile(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-3001"},
    ).json()

    fake_paypal["capture_error"] = paypal.PayPalTransportError("ReadTimeout")
    failed = brief_client.post(
        f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers
    )
    assert failed.json()["status"] == "RECONCILING"

    # The buyer did approve and PayPal did capture; only our response was lost.
    fake_paypal["order_payload"]["status"] = "COMPLETED"
    fake_paypal["order_payload"]["purchase_units"][0]["payments"]["captures"] = [
        {
            "id": CAPTURE_ID,
            "status": "COMPLETED",
            "amount": {"value": "500.00", "currency_code": "USD"},
            "payee": {"merchant_id": "MERCHANT-1"},
        }
    ]

    reconciled = seller_client.post(
        f"/api/payments/{attempt['id']}/reconcile", headers=seller_headers
    )
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["status"] == "COMPLETED"

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert view["quotes"][0]["status"] == "PAID"
    assert view["order"]["capture_id"] == CAPTURE_ID


def test_declined_capture_unlocks_the_quote(seller, rules, fake_paypal) -> None:
    _, _, brief_client, brief_headers, requirement_id, quote_id = _confirmed_quote()
    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-4001"},
    ).json()

    fake_paypal["capture_error"] = paypal.PayPalResponseError(
        422, {"name": "UNPROCESSABLE_ENTITY", "details": [{"issue": "INSTRUMENT_DECLINED"}]}
    )
    declined = brief_client.post(
        f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "FAILED"

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert view["quotes"][0]["status"] == "CONFIRMED"

    retry = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-4002"},
    )
    assert retry.status_code == 200
    assert retry.json()["id"] != attempt["id"]


def test_idempotency_key_cannot_be_reused_for_another_quote(seller, rules, fake_paypal) -> None:
    seller_a, _, client_a, headers_a, requirement_a, quote_a = _confirmed_quote()
    client_a.post(
        _attempt_path(requirement_a, quote_a),
        headers={**headers_a, "Idempotency-Key": "shared-key-1"},
    )
    _, _, client_b, headers_b, requirement_b, quote_b = _confirmed_quote()

    conflict = client_b.post(
        _attempt_path(requirement_b, quote_b),
        headers={**headers_b, "Idempotency-Key": "shared-key-1"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_unconfirmed_quote_cannot_start_payment(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers = seller_browser()
    brief_client, brief_headers = client_browser()
    requirement_id = create_brief(brief_client, brief_headers)
    proposal = seller_client.post(
        f"/api/requirements/{requirement_id}/proposals",
        json={"label": "One page", "pages": 1, "requested_features": ["landing_pages"]},
        headers=seller_headers,
    ).json()
    quote = seller_client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    ).json()

    response = brief_client.post(
        _attempt_path(requirement_id, quote["id"]),
        headers={**brief_headers, "Idempotency-Key": "demo-key-5001"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "quote_not_payable"


def test_a_client_cannot_touch_another_briefs_payment(seller, rules, fake_paypal) -> None:
    _, _, client_a, headers_a, requirement_a, quote_a = _confirmed_quote()
    attempt = client_a.post(
        _attempt_path(requirement_a, quote_a),
        headers={**headers_a, "Idempotency-Key": "demo-key-6001"},
    ).json()

    _, _, client_b, headers_b, _, _ = _confirmed_quote()
    forbidden = client_b.get(f"/api/portal/payments/{attempt['id']}")
    assert forbidden.status_code == 404

    missing_key = client_a.post(_attempt_path(requirement_a, quote_a), headers=headers_a)
    assert missing_key.status_code == 422


def test_snapshot_is_written_once(seller, rules, fake_paypal, db) -> None:
    from app.payments.models import OrderSnapshot

    _, _, brief_client, brief_headers, requirement_id, quote_id = _confirmed_quote()
    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-7001"},
    ).json()
    brief_client.post(f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers)

    snapshots = db.query(OrderSnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].captured_at <= datetime.now(UTC)
    assert snapshots[0].quote_version_id is not None
    assert snapshots[0].paypal_capture_id == CAPTURE_ID


def test_a_paid_brief_cannot_be_deleted(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "demo-key-8001"},
    ).json()
    brief_client.post(f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers)

    response = seller_client.delete(f"/api/requirements/{requirement_id}", headers=seller_headers)
    assert response.status_code == 409
    assert response.json()["code"] == "payment_completed"


def test_attention_lists_reconciling_and_failed_attempts(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )

    assert seller_client.get("/api/payments/attention").json() == []

    attempt = _attempt_with_unknown_create(
        fake_paypal,
        requirement_id,
        quote_id,
        "attention-key-1",
        brief_client,
        brief_headers,
    )
    rows = seller_client.get("/api/payments/attention").json()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == attempt["id"]
    assert row["status"] == "RECONCILING"
    assert row["client_name"] == "Maya Ortiz"
    assert row["client_business"] == "Fern & Filter Coffee"
    assert row["quote_number"] == 1
    assert row["amount_minor"] == TOTAL

    assert brief_client.get("/api/payments/attention").status_code == 403
    from app.main import app

    with TestClient(app) as anonymous:
        assert anonymous.get("/api/payments/attention").status_code == 401

    # A resolved create moves out of the list; a declined capture moves back in.
    fake_paypal["create_error"] = None
    retried = seller_client.post(
        f"/api/payments/{attempt['id']}/retry-create", headers=seller_headers
    )
    assert retried.json()["status"] == "AWAITING_APPROVAL"
    assert seller_client.get("/api/payments/attention").json() == []

    fake_paypal["capture_error"] = paypal.PayPalResponseError(
        422, {"name": "UNPROCESSABLE_ENTITY", "details": [{"issue": "INSTRUMENT_DECLINED"}]}
    )
    failed = brief_client.post(
        f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers
    )
    assert failed.json()["status"] == "FAILED"
    assert [item["status"] for item in seller_client.get("/api/payments/attention").json()] == [
        "FAILED"
    ]

    # A brief stays open while a payment failed and the quote is unlocked.
    assert seller_client.get(f"/api/requirements/{requirement_id}").json()["requirement"][
        "status"
    ] == "OPEN"

    fake_paypal["capture_error"] = None
    second = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "attention-key-2"},
    ).json()
    captured = brief_client.post(
        f"/api/portal/payments/{second['id']}/capture", headers=brief_headers
    )
    assert captured.json()["status"] == "COMPLETED"
    assert seller_client.get("/api/payments/attention").json() == []


def test_attention_is_scoped_to_the_signed_in_seller(seller, rules, fake_paypal, db) -> None:
    seller_client, _, brief_client, brief_headers, requirement_id, quote_id = _confirmed_quote()
    _attempt_with_unknown_create(
        fake_paypal,
        requirement_id,
        quote_id,
        "attention-key-3",
        brief_client,
        brief_headers,
    )

    from app.payments.service import list_attention

    assert len(seller_client.get("/api/payments/attention").json()) == 1
    assert list_attention(db, seller.id)
    assert list_attention(db, uuid4()) == []


def test_a_completed_payment_closes_the_brief(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    before = seller_client.get(f"/api/requirements/{requirement_id}").json()
    assert before["requirement"]["status"] == "OPEN"

    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "close-key-1"},
    ).json()
    captured = brief_client.post(
        f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers
    )
    assert captured.json()["status"] == "COMPLETED"

    seller_row = seller_client.get(f"/api/requirements/{requirement_id}").json()
    assert seller_row["requirement"]["status"] == "CLOSED"
    assert next(
        row for row in seller_client.get("/api/requirements").json() if row["id"] == requirement_id
    )["status"] == "CLOSED"
    assert next(
        row
        for row in brief_client.get("/api/portal/briefs").json()
        if row["id"] == requirement_id
    )["status"] == "CLOSED"


def test_seller_list_marks_paid_briefs_as_not_deletable(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )

    before = next(
        row
        for row in seller_client.get("/api/requirements").json()
        if row["id"] == requirement_id
    )
    assert before["deletable"] is True

    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "deletable-key-1"},
    ).json()
    captured = brief_client.post(
        f"/api/portal/payments/{attempt['id']}/capture", headers=brief_headers
    )
    assert captured.json()["status"] == "COMPLETED"

    after = next(
        row
        for row in seller_client.get("/api/requirements").json()
        if row["id"] == requirement_id
    )
    assert after["deletable"] is False

    # The client brief list keeps the plain summary contract.
    assert "deletable" not in brief_client.get("/api/portal/briefs").json()[0]


def test_unknown_payment_returns_404(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers = seller_browser()
    response = seller_client.post(f"/api/payments/{uuid4()}/reconcile", headers=seller_headers)
    assert response.status_code == 404


def _attempt_with_unknown_create(
    fake_paypal: dict,
    requirement_id: str,
    quote_id: str,
    key: str,
    brief_client: TestClient,
    brief_headers: dict,
) -> dict:
    fake_paypal["create_error"] = paypal.PayPalTransportError("ReadTimeout")
    response = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_reconcile_without_order_id_is_rejected(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = _attempt_with_unknown_create(
        fake_paypal,
        requirement_id, quote_id, "recover-key-1", brief_client, brief_headers,
    )
    assert attempt["status"] == "RECONCILING"
    assert attempt["paypal_order_id"] is None

    response = seller_client.post(
        f"/api/payments/{attempt['id']}/reconcile", headers=seller_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "no_order_id"


def test_retry_create_recovers_the_missing_order(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = _attempt_with_unknown_create(
        fake_paypal,
        requirement_id, quote_id, "recover-key-2", brief_client, brief_headers,
    )

    fake_paypal["create_error"] = None
    response = seller_client.post(
        f"/api/payments/{attempt['id']}/retry-create", headers=seller_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "AWAITING_APPROVAL"
    assert body["paypal_order_id"].startswith(ORDER_ID)
    assert body["retry_count"] == 1

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert view["quotes"][0]["status"] == "PAYMENT_LOCKED"


def test_retry_create_is_bounded(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = _attempt_with_unknown_create(
        fake_paypal,
        requirement_id, quote_id, "recover-key-3", brief_client, brief_headers,
    )

    for expected in (1, 2):
        response = seller_client.post(
            f"/api/payments/{attempt['id']}/retry-create", headers=seller_headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["retry_count"] == expected
        assert response.json()["status"] == "RECONCILING"

    blocked = seller_client.post(
        f"/api/payments/{attempt['id']}/retry-create", headers=seller_headers
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "retry_limit"


def test_close_requires_confirmation_and_a_note(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = _attempt_with_unknown_create(
        fake_paypal,
        requirement_id, quote_id, "recover-key-4", brief_client, brief_headers,
    )
    path = f"/api/payments/{attempt['id']}/close"

    unconfirmed = seller_client.post(
        path,
        json={"note": "Checked PayPal activity list: no order.", "confirmed_no_order": False},
        headers=seller_headers,
    )
    assert unconfirmed.status_code == 422
    assert unconfirmed.json()["code"] == "confirmation_required"

    # Whitespace passes the schema's length check but not the semantic one.
    short_note = seller_client.post(
        path, json={"note": "            ", "confirmed_no_order": True}, headers=seller_headers
    )
    assert short_note.status_code == 422
    assert short_note.json()["code"] == "note_required"


def test_close_unlocks_the_quote_and_keeps_a_trail(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = _attempt_with_unknown_create(
        fake_paypal,
        requirement_id, quote_id, "recover-key-5", brief_client, brief_headers,
    )

    closed = seller_client.post(
        f"/api/payments/{attempt['id']}/close",
        json={
            "note": "Checked PayPal activity: no order was created for this quote.",
            "confirmed_no_order": True,
        },
        headers=seller_headers,
    )
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "ABANDONED"
    assert body["resolution_note"].startswith("Checked PayPal")
    assert body["resolved_at"] is not None

    view = brief_client.get(f"/api/portal/{requirement_id}").json()
    assert view["quotes"][0]["status"] == "CONFIRMED"


def test_retry_rejected_when_paypal_already_returned_an_order(seller, rules, fake_paypal) -> None:
    seller_client, seller_headers, brief_client, brief_headers, requirement_id, quote_id = (
        _confirmed_quote()
    )
    attempt = brief_client.post(
        _attempt_path(requirement_id, quote_id),
        headers={**brief_headers, "Idempotency-Key": "recover-key-6"},
    ).json()

    response = seller_client.post(
        f"/api/payments/{attempt['id']}/retry-create", headers=seller_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "order_already_exists"
