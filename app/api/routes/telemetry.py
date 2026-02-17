from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.telemetry import (
    AttackSequenceIn,
    AttackSequenceOut,
    NetworkFlowIn,
    NetworkFlowResult,
    NetworkFlowStreamAck,
    TimeSeriesPointIn,
)
from app.services.defense_orchestrator import DefenseOrchestrator
from app.services.kafka_stream import kafka_stream

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/network", response_model=NetworkFlowResult)
def ingest_network(payload: NetworkFlowIn, db: Session = Depends(get_db_session)):
    defense = DefenseOrchestrator(db)
    result = defense.evaluate_network_flow(payload)
    return result


@router.post("/network/stream", response_model=NetworkFlowStreamAck, status_code=status.HTTP_202_ACCEPTED)
async def ingest_network_stream(payload: NetworkFlowIn, db: Session = Depends(get_db_session)):
    if kafka_stream.enabled:
        accepted = await kafka_stream.publish_network_flow(payload.model_dump())
        return {
            "accepted": accepted,
            "mode": "kafka",
            "topic": kafka_stream.settings.kafka_network_topic,
        }

    DefenseOrchestrator(db).evaluate_network_flow(payload)
    return {"accepted": True, "mode": "sync", "topic": None}


@router.post("/timeseries", status_code=status.HTTP_202_ACCEPTED)
def ingest_timeseries(payload: TimeSeriesPointIn, db: Session = Depends(get_db_session)):
    defense = DefenseOrchestrator(db)
    defense.ingest_timeseries(payload)
    return {"status": "accepted"}


@router.post("/attack-sequence", response_model=AttackSequenceOut)
def ingest_attack_sequence(payload: AttackSequenceIn, db: Session = Depends(get_db_session)):
    defense = DefenseOrchestrator(db)
    return defense.ingest_attack_sequence(payload)
