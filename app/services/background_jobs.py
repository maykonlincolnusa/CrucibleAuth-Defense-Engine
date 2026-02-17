import asyncio
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.db.models import LoginEvent
from app.db.session import SessionLocal
from app.services.model_lifecycle_service import ModelLifecycleService
from app.services.model_registry_service import ModelRegistryService
from app.services.monitoring_service import MonitoringService
from app.services.realtime_hub import realtime_hub


async def monitoring_push_loop() -> None:
    while True:
        try:
            if await realtime_hub.size() > 0:
                with SessionLocal() as db:
                    monitoring = MonitoringService(db)
                    await realtime_hub.broadcast(
                        {
                            "type": "monitoring.update",
                            "payload": {
                                "overview": monitoring.overview(hours=24),
                                "timeseries": monitoring.timeseries(hours=24),
                                "drilldown": monitoring.drilldown(hours=24, limit=8),
                            },
                        }
                    )
        except Exception:
            pass
        await asyncio.sleep(5)


async def auto_retrain_loop() -> None:
    settings = get_settings()
    last_run: datetime | None = None

    while True:
        try:
            if settings.auto_retrain_enabled:
                now = datetime.now(timezone.utc)
                enough_time = (
                    last_run is None
                    or now - last_run >= timedelta(minutes=settings.auto_retrain_interval_minutes)
                )
                if enough_time:
                    with SessionLocal() as db:
                        event_count = (
                            db.query(LoginEvent)
                            .count()
                        )
                        if event_count >= settings.retrain_min_events:
                            lifecycle = ModelLifecycleService(db)
                            result = lifecycle.train_with_validation_and_rollback()
                            timestamp = now.strftime("%Y%m%d%H%M%S")
                            ModelRegistryService(db).register(
                                model_name="defense_pipeline",
                                model_version=f"auto-{timestamp}",
                                model_type="ensemble_ml_dl_rl_auto",
                                artifact_path=result["artifact_path"],
                                metrics=result,
                            )
                            last_run = now
        except Exception:
            pass

        await asyncio.sleep(30)
