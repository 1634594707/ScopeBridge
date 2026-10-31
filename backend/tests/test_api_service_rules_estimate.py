"""Public scope estimator: the server prices, the request only chooses."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _estimate(client: TestClient, **payload) -> dict:
    response = client.post("/api/service-rules/estimate", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_estimate_prices_a_scope_with_the_active_rule_version(rules) -> None:
    from app.main import app

    with TestClient(app) as client:
        body = _estimate(client, pages=2, addon_codes=["copywriting"])

    assert body["rule_version"] == rules.version_no
    assert body["currency"] == "USD"
    assert body["total_minor"] == 50000 + 10000 + 15000
    assert [item["code"] for item in body["items"]] == ["base_page", "extra_page", "copywriting"]
    assert all(item["rule_ref"].startswith("rule.") for item in body["items"])
    assert body["violations"] == []


def test_estimate_follows_the_newest_rule_version(rules, db) -> None:
    from app.main import app
    from app.service_rules.models import ServiceRuleVersion

    db.add(
        ServiceRuleVersion(
            version_no=2,
            currency="USD",
            base_page_minor=60000,
            extra_page_minor=12000,
            revisions_included=2,
            lead_time_days=5,
            asset_buffer_days=3,
            addons=[],
            capabilities=[],
            exclusions=[],
            notes="Repriced.",
        )
    )
    db.commit()

    with TestClient(app) as client:
        body = _estimate(client, pages=2, addon_codes=[])

    assert body["rule_version"] == 2
    assert body["total_minor"] == 60000 + 12000


def test_estimate_reports_unknown_addons_without_charging_for_them(rules) -> None:
    from app.main import app

    with TestClient(app) as client:
        body = _estimate(client, pages=1, addon_codes=["not_offered"])

    assert body["total_minor"] == 50000
    assert [item["code"] for item in body["items"]] == ["base_page"]
    assert [violation["code"] for violation in body["violations"]] == ["unknown_addon"]
    assert body["violations"][0]["rule_ref"] == "rule.addon"


def test_estimate_rejects_amounts_and_pages_outside_the_published_range(rules) -> None:
    from app.main import app

    with TestClient(app) as client:
        with_amount = client.post(
            "/api/service-rules/estimate",
            json={"pages": 1, "addon_codes": [], "total_minor": 1},
        )
        too_many_pages = client.post(
            "/api/service-rules/estimate", json={"pages": 21, "addon_codes": []}
        )
        no_pages = client.post(
            "/api/service-rules/estimate", json={"pages": 0, "addon_codes": []}
        )

    for response in (with_amount, too_many_pages, no_pages):
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"


def test_estimate_is_public(rules) -> None:
    from app.main import app

    # No cookie jar, no CSRF header: the price list is a public page.
    with TestClient(app) as anonymous:
        response = anonymous.post(
            "/api/service-rules/estimate", json={"pages": 1, "addon_codes": []}
        )
    assert response.status_code == 200
