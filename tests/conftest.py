import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_security_lab.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["MODEL_DIR"] = "./test_artifacts"
os.environ["KAFKA_ENABLED"] = "false"
os.environ["AUTO_RETRAIN_ENABLED"] = "false"
os.environ["METRICS_ENABLED"] = "true"
os.environ["OTEL_ENABLED"] = "false"

from app.main import app  # noqa: E402
from app.db.session import engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_artifacts():
    db_path = Path("test_security_lab.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass
    yield
    engine.dispose()
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass
    artifacts = Path("test_artifacts")
    if artifacts.exists():
        for file in artifacts.glob("*"):
            if file.is_file():
                file.unlink()
        artifacts.rmdir()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
