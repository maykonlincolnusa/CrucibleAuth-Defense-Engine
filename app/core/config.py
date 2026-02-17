from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=("settings_",),
    )

    app_name: str = Field(default="Password Cracking Lab + Defense System")
    app_env: str = Field(default="dev")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)

    database_url: str = Field(default="sqlite+pysqlite:///./security_lab.db")
    jwt_secret_key: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)

    model_dir: str = Field(default="./artifacts")
    auto_train_min_samples: int = Field(default=200)
    auto_retrain_enabled: bool = Field(default=False)
    auto_retrain_interval_minutes: int = Field(default=30)
    retrain_min_events: int = Field(default=250)
    retrain_acceptance_threshold: float = Field(default=0.55)

    mlflow_tracking_uri: str = Field(default="file:./artifacts/mlruns")
    mlflow_experiment: str = Field(default="security-defense-pipeline")

    kafka_enabled: bool = Field(default=False)
    kafka_bootstrap_servers: str = Field(default="redpanda:9092")
    kafka_network_topic: str = Field(default="security.network.flows")
    kafka_consumer_group: str = Field(default="security-defense-api")

    metrics_enabled: bool = Field(default=True)
    otel_enabled: bool = Field(default=False)
    otel_exporter_otlp_endpoint: str = Field(default="")

    @property
    def model_path(self) -> Path:
        path = Path(self.model_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
