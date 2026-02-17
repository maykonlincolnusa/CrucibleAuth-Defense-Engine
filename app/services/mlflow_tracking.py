from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

try:
    import mlflow
except Exception:  # pragma: no cover - optional dependency
    mlflow = None

from app.core.config import get_settings


def configure_mlflow() -> None:
    if mlflow is None:
        return
    settings = get_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment)


@contextmanager
def training_run(run_name: str, params: dict, metrics: dict) -> Iterator[str]:
    if mlflow is None:
        yield "mlflow-not-installed"
        return
    configure_mlflow()
    with mlflow.start_run(run_name=run_name) as run:
        for key, value in params.items():
            mlflow.log_param(key, value)
        for key, value in metrics.items():
            mlflow.log_metric(key, float(value))
        yield run.info.run_id
