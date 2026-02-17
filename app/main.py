from contextlib import asynccontextmanager
from pathlib import Path
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import get_settings
from app.db.init_db import ensure_default_admin, init_db, run_migrations
from app.db.session import SessionLocal, engine
from app.observability.metrics import PrometheusMiddleware, metrics_response
from app.observability.tracing import setup_tracing
from app.services.background_jobs import auto_retrain_loop, monitoring_push_loop
from app.services.kafka_stream import kafka_stream
from app.services.realtime_hub import realtime_hub

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        run_migrations()
    except Exception:
        init_db()
    with SessionLocal() as db:
        ensure_default_admin(db)

    if kafka_stream.enabled:
        await kafka_stream.start()

    monitor_task = asyncio.create_task(monitoring_push_loop())
    retrain_task = asyncio.create_task(auto_retrain_loop())
    yield
    for task in [monitor_task, retrain_task]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await kafka_stream.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)
if settings.metrics_enabled:
    app.add_middleware(PrometheusMiddleware)
setup_tracing(app, engine)

web_dir = Path(__file__).resolve().parent / "web"
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=web_dir), name="web")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(web_dir / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return metrics_response()


@app.websocket("/ws/monitoring")
async def monitoring_socket(websocket: WebSocket):
    await realtime_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await realtime_hub.disconnect(websocket)


@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(_, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable", "error": str(type(exc).__name__)},
    )
