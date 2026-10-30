"""Payment boundary: lock, capture, unknown outcomes, recovery, snapshot."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.paypal import client as paypal

ORDER_ID = "ORDER-SANDBOX-1"
CAPTURE_ID = "CAPTURE-SANDBOX-1"
TOTAL = 50000


def _sign_in(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    response = client.post(
        "/api/session",
        json={"email": settings.seller_email, "password": settings.seller_password},
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


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


def _confirmed_quote(client: TestClient) -> tuple[str, dict[str, str], str]:
    """Create a brief, price it, review and confirm it. Returns ids and headers."""
    seller = _sign_in(client)
    brief = client.post(
        "/api/requirements",
        json={
            "client_name": "Maya Ortiz",
            "client_business": "Fern & Filter Coffee",
            "client_email": "maya@example.com",
            "message": "One page site with a link to our ordering tool.",
            "budget_minor": TOTAL,
            "deadline": (date.today() + timedelta(days=30)).isoformat(),
            "assets_ready": True,
        },
    ).json()
    requirement_id = brief["requirement_id"]
    portal = {"X-Customer-Token": brief["portal_token"]}

    proposal = client.post(
        f"/api/requirements/{requirement_id}/proposals",
        json={
            "label": "One page",
            "pages": 1,
            "addon_codes": ["external_order_link"],
            "requested_features": ["landing_pages"],
            "assets_ready": True,
        },
        headers=seller,
    ).json()
    client.post(f"/api/portal/proposals/{proposal['id']}/select", headers=portal)

    quote = client.post(
        f"/api/requirements/{requirement_id}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller,
    ).json()
    client.post(f"/api/quotes/{quote['id']}/review", headers=seller)
    confirmed = client.post(f"/api/portal/quotes/{quote['id']}/confirm", headers=portal)
    assert confirmed.status_code == 200, confirmed.text
    return requirement_id, portal, quote["id"]


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


def test_payment_locks_the_quote_and_returns_an_approval_link(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)

    response = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-0001"},
    )
    assert response.status_code == 200, response.text
    attempt = response.json()
    assert attempt["status"] == "AWAITING_APPROVAL"
    assert attempt["paypal_order_id"].startswith(ORDER_ID)
    assert attempt["approve_url"].startswith("https://sandbox.paypal.com/")

    view = client.get("/api/portal", headers=portal).json()
    assert view["quotes"][0]["status"] == "PAYMENT_LOCKED"
    assert view["payments"][0]["id"] == attempt["id"]

    replay = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-0001"},
    )
    assert replay.json()["id"] == attempt["id"]

    other_key = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-0002"},
    )
    assert other_key.json()["id"] == attempt["id"]
    assert fake_paypal["created"] == 1


def test_capture_completes_the_quote_and_freezes_a_snapshot(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-1001"},
    ).json()

    captured = client.post(f"/api/portal/payments/{attempt['id']}/capture", headers=portal)
    assert captured.status_code == 200, captured.text
    assert captured.json()["status"] == "COMPLETED"
    assert captured.json()["paypal_capture_id"] == CAPTURE_ID

    view = client.get("/api/portal", headers=portal).json()
    assert view["quotes"][0]["status"] == "PAID"
    assert view["order"]["amount_minor"] == TOTAL
    assert view["order"]["capture_id"] == CAPTURE_ID
    assert len(view["order"]["items"]) >= 2

    again = client.post(f"/api/portal/payments/{attempt['id']}/capture", headers=portal)
    assert again.status_code == 200
    assert again.json()["status"] == "COMPLETED"

    seller_headers = _sign_in(client)
    order = client.get(f"/api/orders/{view['order']['id']}", headers=seller_headers)
    assert order.status_code == 200
    assert order.json()["order_id"].startswith(ORDER_ID)


def test_amount_mismatch_stays_in_reconciling(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-2001"},
    ).json()

    fake_paypal["capture_payload"] = _order_payload(status="COMPLETED", value="999.00")
    captured = client.post(f"/api/portal/payments/{attempt['id']}/capture", headers=portal)
    assert captured.json()["status"] == "RECONCILING"
    assert captured.json()["error_code"] == "capture_amount_mismatch"

    view = client.get("/api/portal", headers=portal).json()
    assert view["quotes"][0]["status"] == "PAYMENT_LOCKED"


def test_lost_capture_response_is_recovered_by_reconcile(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-3001"},
    ).json()

    fake_paypal["capture_error"] = paypal.PayPalTransportError("ReadTimeout")
    failed = client.post(f"/api/portal/payments/{attempt['id']}/capture", headers=portal)
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

    seller_headers = _sign_in(client)
    reconciled = client.post(
        f"/api/payments/{attempt['id']}/reconcile", headers=seller_headers
    )
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["status"] == "COMPLETED"

    view = client.get("/api/portal", headers=portal).json()
    assert view["quotes"][0]["status"] == "PAID"
    assert view["order"]["capture_id"] == CAPTURE_ID


def test_declined_capture_unlocks_the_quote(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-4001"},
    ).json()

    fake_paypal["capture_error"] = paypal.PayPalResponseError(
        422, {"name": "UNPROCESSABLE_ENTITY", "details": [{"issue": "INSTRUMENT_DECLINED"}]}
    )
    declined = client.post(f"/api/portal/payments/{attempt['id']}/capture", headers=portal)
    assert declined.status_code == 200
    assert declined.json()["status"] == "FAILED"

    view = client.get("/api/portal", headers=portal).json()
    assert view["quotes"][0]["status"] == "CONFIRMED"

    retry = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-4002"},
    )
    assert retry.status_code == 200
    assert retry.json()["id"] != attempt["id"]


def test_idempotency_key_cannot_be_reused_for_another_quote(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal_a, quote_a = _confirmed_quote(client)
    client.post(
        f"/api/portal/quotes/{quote_a}/payment-attempts",
        headers={**portal_a, "Idempotency-Key": "shared-key-1"},
    )
    _, portal_b, quote_b = _confirmed_quote(client)

    conflict = client.post(
        f"/api/portal/quotes/{quote_b}/payment-attempts",
        headers={**portal_b, "Idempotency-Key": "shared-key-1"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_unconfirmed_quote_cannot_start_payment(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    seller_headers = _sign_in(client)
    brief = client.post(
        "/api/requirements",
        json={
            "client_name": "Ada",
            "client_business": "Studio",
            "client_email": "ada@example.com",
            "message": "One page site please.",
            "budget_minor": TOTAL,
            "deadline": (date.today() + timedelta(days=30)).isoformat(),
            "assets_ready": True,
        },
    ).json()
    portal = {"X-Customer-Token": brief["portal_token"]}
    proposal = client.post(
        f"/api/requirements/{brief['requirement_id']}/proposals",
        json={"label": "One page", "pages": 1, "requested_features": ["landing_pages"]},
        headers=seller_headers,
    ).json()
    quote = client.post(
        f"/api/requirements/{brief['requirement_id']}/quotes",
        json={"proposal_id": proposal["id"]},
        headers=seller_headers,
    ).json()

    response = client.post(
        f"/api/portal/quotes/{quote['id']}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-5001"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "quote_not_payable"


def test_customer_token_cannot_touch_another_brief(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal_a, quote_a = _confirmed_quote(client)
    attempt = client.post(
        f"/api/portal/quotes/{quote_a}/payment-attempts",
        headers={**portal_a, "Idempotency-Key": "demo-key-6001"},
    ).json()

    _, portal_b, _ = _confirmed_quote(client)
    forbidden = client.get(f"/api/portal/payments/{attempt['id']}", headers=portal_b)
    assert forbidden.status_code == 404

    missing_key = client.post(
        f"/api/portal/quotes/{quote_a}/payment-attempts",
        headers=portal_a,
    )
    assert missing_key.status_code == 422


def test_snapshot_is_written_once(client: TestClient, seller, rules, fake_paypal, db) -> None:
    from app.payments.models import OrderSnapshot

    _, portal, quote_id = _confirmed_quote(client)
    attempt = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "demo-key-7001"},
    ).json()
    client.post(f"/api/portal/payments/{attempt['id']}/capture", headers=portal)

    snapshots = db.query(OrderSnapshot).all()
    assert len(snapshots) == 1
    assert snapshots[0].captured_at <= datetime.now(UTC)
    assert snapshots[0].quote_version_id is not None
    assert snapshots[0].paypal_capture_id == CAPTURE_ID


def test_unknown_payment_returns_404(client: TestClient, seller, rules, fake_paypal) -> None:
    headers = _sign_in(client)
    response = client.post(f"/api/payments/{uuid4()}/reconcile", headers=headers)
    assert response.status_code == 404


def _attempt_with_unknown_create(
    client: TestClient, portal: dict[str, str], quote_id: str, key: str, fake_paypal: dict
) -> dict:
    fake_paypal["create_error"] = paypal.PayPalTransportError("ReadTimeout")
    response = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_reconcile_without_order_id_is_rejected(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = _attempt_with_unknown_create(client, portal, quote_id, "recover-key-1", fake_paypal)
    assert attempt["status"] == "RECONCILING"
    assert attempt["paypal_order_id"] is None

    headers = _sign_in(client)
    response = client.post(f"/api/payments/{attempt['id']}/reconcile", headers=headers)
    assert response.status_code == 409
    assert response.json()["code"] == "no_order_id"


def test_retry_create_recovers_the_missing_order(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = _attempt_with_unknown_create(client, portal, quote_id, "recover-key-2", fake_paypal)

    fake_paypal["create_error"] = None
    headers = _sign_in(client)
    response = client.post(f"/api/payments/{attempt['id']}/retry-create", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "AWAITING_APPROVAL"
    assert body["paypal_order_id"].startswith(ORDER_ID)
    assert body["retry_count"] == 1

    view = client.get("/api/portal", headers=portal).json()
    assert view["quotes"][0]["status"] == "PAYMENT_LOCKED"


def test_retry_create_is_bounded(client: TestClient, seller, rules, fake_paypal) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = _attempt_with_unknown_create(client, portal, quote_id, "recover-key-3", fake_paypal)
    headers = _sign_in(client)

    for expected in (1, 2):
        response = client.post(f"/api/payments/{attempt['id']}/retry-create", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["retry_count"] == expected
        assert response.json()["status"] == "RECONCILING"

    blocked = client.post(f"/api/payments/{attempt['id']}/retry-create", headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "retry_limit"


def test_close_requires_confirmation_and_a_note(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = _attempt_with_unknown_create(client, portal, quote_id, "recover-key-4", fake_paypal)
    headers = _sign_in(client)
    path = f"/api/payments/{attempt['id']}/close"

    unconfirmed = client.post(
        path,
        json={"note": "Checked PayPal activity list: no order.", "confirmed_no_order": False},
        headers=headers,
    )
    assert unconfirmed.status_code == 422
    assert unconfirmed.json()["code"] == "confirmation_required"

    # Whitespace passes the schema's length check but not the semantic one.
    short_note = client.post(
        path, json={"note": "            ", "confirmed_no_order": True}, headers=headers
    )
    assert short_note.status_code == 422
    assert short_note.json()["code"] == "note_required"


def test_close_unlocks_the_quote_and_keeps_a_trail(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = _attempt_with_unknown_create(client, portal, quote_id, "recover-key-5", fake_paypal)
    headers = _sign_in(client)

    closed = client.post(
        f"/api/payments/{attempt['id']}/close",
        json={
            "note": "Checked PayPal activity: no order was created for this quote.",
            "confirmed_no_order": True,
        },
        headers=headers,
    )
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "ABANDONED"
    assert body["resolution_note"].startswith("Checked PayPal")
    assert body["resolved_at"] is not None

    view = client.get("/api/portal", headers=portal).json()
    assert view["quotes"][0]["status"] == "CONFIRMED"


def test_retry_rejected_when_paypal_already_returned_an_order(
    client: TestClient, seller, rules, fake_paypal
) -> None:
    _, portal, quote_id = _confirmed_quote(client)
    attempt = client.post(
        f"/api/portal/quotes/{quote_id}/payment-attempts",
        headers={**portal, "Idempotency-Key": "recover-key-6"},
    ).json()

    headers = _sign_in(client)
    response = client.post(f"/api/payments/{attempt['id']}/retry-create", headers=headers)
    assert response.status_code == 409
    assert response.json()["code"] == "order_already_exists"
