from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.defense import RiskSummary
from app.services.defense_orchestrator import DefenseOrchestrator

router = APIRouter(prefix="/defense", tags=["defense"])


@router.get("/risk/{user_id}", response_model=RiskSummary)
def user_risk(user_id: str, db: Session = Depends(get_db_session)):
    defense = DefenseOrchestrator(db)
    return defense.user_risk_summary(user_id)
