from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.services.model_lifecycle_service import ModelLifecycleService
from app.services.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/models", tags=["models"])


@router.post("/train-bootstrap")
def train_bootstrap(db: Session = Depends(get_db_session)):
    lifecycle = ModelLifecycleService(db)
    registry = ModelRegistryService(db)

    result = lifecycle.train_with_validation_and_rollback()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    registry.register(
        model_name="defense_pipeline",
        model_version=timestamp,
        model_type="ensemble_ml_dl_rl",
        artifact_path=result["artifact_path"],
        metrics=result,
    )
    return result


@router.get("/active")
def list_active_models(db: Session = Depends(get_db_session)):
    registry = ModelRegistryService(db)
    models = registry.list_active()
    return [
        {
            "model_name": m.model_name,
            "version": m.model_version,
            "type": m.model_type,
            "artifact_path": m.artifact_path,
            "created_at": m.created_at,
            "metrics": m.metrics,
        }
        for m in models
    ]


@router.post("/auto-retrain")
def auto_retrain(db: Session = Depends(get_db_session)):
    settings = get_settings()
    if not settings.auto_retrain_enabled:
        return {"status": "disabled", "message": "AUTO_RETRAIN_ENABLED=false"}
    lifecycle = ModelLifecycleService(db)
    return lifecycle.train_with_validation_and_rollback()
