"""Rule version persistence and projection into the pure rule layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.rules.types import AddonDefinition, RuleSet
from app.service_rules.models import ServiceRuleVersion

DEFAULT_RULES: dict[str, Any] = {
    "version_no": 1,
    "currency": "USD",
    "base_page_minor": 50000,
    "extra_page_minor": 10000,
    "revisions_included": 2,
    "lead_time_days": 5,
    "asset_buffer_days": 3,
    "addons": [
        {
            "code": "external_order_link",
            "label": "External order link integration",
            "amount_minor": 0,
            "description": "A checkout button pointing at your existing ordering tool.",
        },
        {
            "code": "extra_revision_round",
            "label": "Additional revision round",
            "amount_minor": 5000,
            "description": "One extra review round beyond the two included rounds.",
        },
        {
            "code": "copywriting",
            "label": "Page copywriting",
            "amount_minor": 15000,
            "description": "Writing the page copy from your notes and menu.",
        },
    ],
    "capabilities": [
        "landing_pages",
        "mobile_responsive",
        "external_order_link",
        "two_revision_rounds",
    ],
    "exclusions": [
        "Domain name and hosting",
        "On-site ordering or payment processing",
        "Product photography",
    ],
    "notes": "Demo price list. Not a market quote.",
}


def ensure_default_rules(db: Session) -> ServiceRuleVersion:
    """Create version 1 once; later versions are added explicitly."""
    existing = db.scalar(select(ServiceRuleVersion).where(ServiceRuleVersion.version_no == 1))
    if existing is not None:
        return existing
    row = ServiceRuleVersion(**DEFAULT_RULES)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_active_rules(db: Session) -> ServiceRuleVersion:
    row = db.scalar(
        select(ServiceRuleVersion).order_by(ServiceRuleVersion.version_no.desc()).limit(1)
    )
    if row is None:
        raise ApiError(409, "no_service_rules", "No service rule version has been published yet.")
    return row


def to_rule_set(row: ServiceRuleVersion) -> RuleSet:
    addons = tuple(
        AddonDefinition(
            code=item["code"],
            label=item["label"],
            amount_minor=int(item["amount_minor"]),
            description=item.get("description", ""),
        )
        for item in row.addons
    )
    return RuleSet(
        currency=row.currency,
        base_page_minor=row.base_page_minor,
        extra_page_minor=row.extra_page_minor,
        revisions_included=row.revisions_included,
        lead_time_days=row.lead_time_days,
        asset_buffer_days=row.asset_buffer_days,
        addons=addons,
        capabilities=frozenset(row.capabilities),
        exclusions=tuple(row.exclusions),
    )


def serialize(row: ServiceRuleVersion) -> dict[str, Any]:
    return {
        "id": row.id,
        "version_no": row.version_no,
        "currency": row.currency,
        "base_page_minor": row.base_page_minor,
        "extra_page_minor": row.extra_page_minor,
        "revisions_included": row.revisions_included,
        "lead_time_days": row.lead_time_days,
        "asset_buffer_days": row.asset_buffer_days,
        "addons": row.addons,
        "capabilities": row.capabilities,
        "exclusions": row.exclusions,
        "notes": row.notes,
    }
