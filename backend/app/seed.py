"""Idempotent demo seed: seller account, rule version 1, one worked example.

Run with `uv run python -m app.seed`. Re-running never duplicates rows; the demo
requirement is only created when the seller has none.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.accounts.service import ensure_seller
from app.core.config import REPO_ROOT, get_settings
from app.core.db import SessionLocal
from app.proposals.schemas import ProposalCreate
from app.proposals.service import create_proposal
from app.requirements.models import Requirement
from app.requirements.schemas import IntakeRequest
from app.requirements.service import create_requirement
from app.service_rules.service import ensure_default_rules

DEMO_TOKEN_FILE = REPO_ROOT / "data" / "demo_portal.txt"


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

        existing = db.scalar(
            select(Requirement).where(Requirement.seller_id == seller.id).limit(1)
        )
        if existing is not None:
            print(f"[seed] demo data already present (requirement {existing.id})")
            return

        deadline = date.today() + timedelta(days=14)
        requirement, portal_token = create_requirement(
            db,
            IntakeRequest(
                client_name="Maya Ortiz",
                client_business="Fern & Filter Coffee",
                client_email="maya@fernandfilter.example",
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

        DEMO_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEMO_TOKEN_FILE.write_text(portal_token, encoding="utf-8")

        print(f"[seed] seller: {seller.email}")
        print(f"[seed] demo portal: {settings.app_base_url}/r/{portal_token}")
        print(f"[seed] token also written to {DEMO_TOKEN_FILE}")


if __name__ == "__main__":
    seed()
