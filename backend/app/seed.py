"""Idempotent demo seed: seller, demo client, rule version 1, one worked example.

Run with `uv run python -m app.seed`. Re-running never duplicates rows; the demo
requirement is only created when the seller has none.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.accounts.service import ensure_client, ensure_seller
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.proposals.schemas import ProposalCreate
from app.proposals.service import create_proposal
from app.requirements.models import Requirement
from app.requirements.schemas import IntakeRequest
from app.requirements.service import create_requirement
from app.service_rules.service import ensure_default_rules


def seed() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        ensure_default_rules(db)
        seller = ensure_seller(
            db,
            email=settings.seller_email,
            password=settings.seller_password,
            display_name="ScopeBridge Studio",
        )
        client = ensure_client(
            db,
            email=settings.client_email,
            password=settings.client_password,
            display_name="Maya Ortiz",
        )

        existing = db.scalar(
            select(Requirement).where(Requirement.seller_id == seller.id).limit(1)
        )
        if existing is not None:
            if existing.client_id is None:
                existing.client_id = client.id
                db.commit()
            print(f"[seed] demo data already present (requirement {existing.id})")
            return

        deadline = date.today() + timedelta(days=14)
        requirement = create_requirement(
            db,
            IntakeRequest(
                client_name="Maya Ortiz",
                client_business="Fern & Filter Coffee",
                client_email=settings.client_email,
                message=(
                    "We are opening a second coffee bar and need a three page website with "
                    "online ordering. Our budget is $500 and we would like it live in two weeks. "
                    "We do not have photos or copy ready yet."
                ),
                budget_minor=50000,
                deadline=deadline,
                assets_ready=False,
            ),
            seller.id,
            client.id,
        )

        create_proposal(
            db,
            requirement,
            ProposalCreate(
                label="One-page launch with external ordering",
                pages=1,
                addon_codes=["external_order_link"],
                requested_features=["landing_pages", "mobile_responsive"],
                assets_ready=False,
            ),
        )
        create_proposal(
            db,
            requirement,
            ProposalCreate(
                label="Two pages plus copywriting",
                pages=2,
                addon_codes=["copywriting"],
                requested_features=["landing_pages"],
                assets_ready=False,
            ),
        )

        print(f"[seed] seller: {seller.email}")
        print(f"[seed] client: {client.email}")
        print(f"[seed] demo brief: {settings.app_base_url}/briefs/{requirement.id}")


if __name__ == "__main__":
    seed()
