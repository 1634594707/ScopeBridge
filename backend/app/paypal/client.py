"""PayPal Orders v2 adapter (sandbox only).

Design rules enforced here:
- the amount always comes from the caller (the confirmed quote), never from the client;
- every mutating call carries a stable `PayPal-Request-Id`;
- transport failures are raised as `PayPalTransportError` so the caller can move
  the attempt into RECONCILING instead of guessing;
- access tokens are cached in-process and never logged or stored.
"""

from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings


class PayPalError(Exception):
    """Base class for adapter failures."""


class PayPalTransportError(PayPalError):
    """No usable response: timeout, connection reset, DNS, proxy."""


class PayPalResponseError(PayPalError):
    """The API answered with a non-2xx status."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.payload = payload
        name = payload.get("name") or payload.get("error") or "paypal_error"
        super().__init__(f"{status_code} {name}")

    @property
    def issue(self) -> str:
        details = self.payload.get("details") or []
        if details and isinstance(details, list):
            return str(details[0].get("issue", ""))
        return str(self.payload.get("name", ""))


@dataclass(frozen=True)
class PayPalOrder:
    id: str
    status: str
    approve_url: str | None
    raw: dict[str, Any]


_token_lock = threading.Lock()
_token_cache: dict[str, tuple[str, float]] = {}


def _settings():
    return get_settings()


def _access_token() -> str:
    settings = _settings()
    if not settings.paypal_client_id or not settings.paypal_client_secret:
        raise PayPalError("PayPal sandbox credentials are not configured")

    cache_key = f"{settings.paypal_base_url}:{settings.paypal_client_id[:8]}"
    cached = _token_cache.get(cache_key)
    now = time.time()
    if cached and cached[1] > now:
        return cached[0]

    with _token_lock:
        cached = _token_cache.get(cache_key)
        if cached and cached[1] > now:
            return cached[0]
        basic = base64.b64encode(
            f"{settings.paypal_client_id}:{settings.paypal_client_secret}".encode()
        ).decode()
        try:
            response = httpx.post(
                f"{settings.paypal_base_url}/v1/oauth2/token",
                headers={"Authorization": f"Basic {basic}"},
                data={"grant_type": "client_credentials"},
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            raise PayPalTransportError(type(exc).__name__) from exc
        if response.status_code != 200:
            raise PayPalResponseError(response.status_code, _body(response))
        payload = response.json()
        token = payload["access_token"]
        expires_in = float(payload.get("expires_in", 300))
        _token_cache[cache_key] = (token, now + max(30.0, expires_in - 60.0))
        return token


def _headers(request_id: str | None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if request_id:
        headers["PayPal-Request-Id"] = request_id
    return headers


def _body(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {"raw": response.text[:500]}
    return payload if isinstance(payload, dict) else {"raw": str(payload)[:500]}


def _call(method: str, path: str, *, request_id: str | None, body: dict | None) -> dict:
    settings = _settings()
    try:
        response = httpx.request(
            method,
            f"{settings.paypal_base_url}{path}",
            headers=_headers(request_id),
            json=body,
            timeout=settings.paypal_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise PayPalTransportError(type(exc).__name__) from exc
    if response.status_code >= 400:
        raise PayPalResponseError(response.status_code, _body(response))
    return _body(response)


def create_order(
    *,
    amount_minor: int,
    currency: str,
    reference_id: str,
    description: str,
    return_url: str,
    cancel_url: str,
    request_id: str,
) -> PayPalOrder:
    payload = _call(
        "POST",
        "/v2/checkout/orders",
        request_id=request_id,
        body={
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "description": description[:127],
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount_minor // 100}.{amount_minor % 100:02d}",
                    },
                }
            ],
            "application_context": {
                "brand_name": "ScopeBridge",
                "user_action": "PAY_NOW",
                "return_url": return_url,
                "cancel_url": cancel_url,
            },
        },
    )
    links = payload.get("links") or []
    approve = next(
        (
            link.get("href")
            for link in links
            if link.get("rel") in {"approve", "payer-action"}
        ),
        None,
    )
    return PayPalOrder(
        id=payload.get("id", ""),
        status=payload.get("status", ""),
        approve_url=approve,
        raw=payload,
    )


def capture_order(order_id: str, *, request_id: str) -> dict[str, Any]:
    return _call(
        "POST",
        f"/v2/checkout/orders/{order_id}/capture",
        request_id=request_id,
        body={},
    )


def get_order(order_id: str) -> dict[str, Any]:
    return _call("GET", f"/v2/checkout/orders/{order_id}", request_id=None, body=None)


def capture_of(order: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first capture object in an order payload, if any."""
    units = order.get("purchase_units") or []
    if not units:
        return None
    payments = units[0].get("payments") or {}
    captures = payments.get("captures") or []
    return captures[0] if captures else None


def amount_matches(capture: dict[str, Any], amount_minor: int, currency: str) -> bool:
    amount = capture.get("amount") or {}
    value = amount.get("value")
    code = amount.get("currency_code")
    if value is None or code != currency:
        return False
    expected = f"{amount_minor // 100}.{amount_minor % 100:02d}"
    return str(value) == expected
