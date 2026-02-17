from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.defense import router as defense_router
from app.api.routes.models import router as models_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.telemetry import router as telemetry_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(telemetry_router)
api_router.include_router(defense_router)
api_router.include_router(models_router)
api_router.include_router(monitoring_router)
