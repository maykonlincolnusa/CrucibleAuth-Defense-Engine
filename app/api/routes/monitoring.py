from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/overview")
def overview(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db_session),
):
    return MonitoringService(db).overview(hours=hours)


@router.get("/timeseries")
def timeseries(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db_session),
):
    return MonitoringService(db).timeseries(hours=hours)


@router.get("/drilldown")
def drilldown(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db_session),
):
    return MonitoringService(db).drilldown(hours=hours, limit=limit)
