"""Idempotent demo seed: seller, demo client, rule version 1, one worked example.

Run with `uv run python -m app.seed`. Re-running never duplicates rows; the demo
requirement is only created when the seller has none.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from sqlalchemy import select

from app.accounts.service import ensure_client, ensure_seller
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.proposals.schemas import ProposalCreate
from app.proposals.service import create_proposal
from app.quotes.schemas import QuoteCreate
from app.quotes.service import confirm_quote, create_quote, review_quote
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


def seed_pathb() -> None:
    """Create the clean brief + confirmed quote used by DEMO_SCRIPT Path B.

    This is meant to run against a separate database (``scopebridge_pathb``),
    never the demo database that holds the recorded sandbox snapshot.
    """
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
            select(Requirement)
            .where(
                Requirement.seller_id == seller.id,
                Requirement.client_id == client.id,
            )
            .order_by(Requirement.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            print("[seed:pathb] Path B brief already present")
            print(f"[seed:pathb] requirement: {existing.id}")
            return

        deadline = date.today() + timedelta(days=30)
        requirement = create_requirement(
            db,
            IntakeRequest(
                client_name="Maya Ortiz",
                client_business="Fern & Filter Coffee",
                client_email=settings.client_email,
                message=(
                    "We need a one page launch site with a link to our existing ordering tool. "
                    "Our budget is $500 and we would like it live in four weeks. "
                    "We do not have photos or copy ready yet."
                ),
                budget_minor=50000,
                deadline=deadline,
                assets_ready=False,
            ),
            seller.id,
            client.id,
        )
        proposal = create_proposal(
            db,
            requirement,
            ProposalCreate(
                label="Path B one-page launch",
                pages=1,
                addon_codes=["external_order_link"],
                requested_features=["landing_pages"],
                assets_ready=False,
            ),
        )
        quote = create_quote(
            db,
            requirement,
            QuoteCreate(
                proposal_id=proposal.id,
                scope_summary="Path B confirmed one-page launch with an external order link",
            ),
            seller.id,
        )
        reviewed = review_quote(db, quote, seller.id)
        confirmed = confirm_quote(db, reviewed, requirement)

        print("[seed:pathb] Path B data created")
        print(f"[seed:pathb] requirement: {requirement.id}")
        print(f"[seed:pathb] quote: {confirmed.id} (v{confirmed.quote_number})")
        print(f"[seed:pathb] status: {confirmed.status}")
        print(f"[seed:pathb] client URL: {settings.app_base_url}/briefs/{requirement.id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ScopeBridge demo data.")
    parser.add_argument(
        "--pathb",
        action="store_true",
        help="Create the clean, confirmed Path B quote in an isolated database.",
    )
    args = parser.parse_args()
    if args.pathb:
        seed_pathb()
    else:
        seed()


if __name__ == "__main__":
    main()
