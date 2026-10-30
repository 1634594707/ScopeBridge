"""Public read of the rule set the pricing is based on."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.service_rules import service
from app.service_rules.schemas import ServiceRuleOut

router = APIRouter(tags=["service-rules"])


@router.get("/service-rules", response_model=ServiceRuleOut)
def read_service_rules(db: Session = Depends(get_db)) -> ServiceRuleOut:
    row = service.get_active_rules(db)
    return ServiceRuleOut(**service.serialize(row))
