import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DefenseActionType(str, enum.Enum):
    allow = "ALLOW"
    mfa_challenge = "MFA_CHALLENGE"
    rate_limit = "RATE_LIMIT"
    temp_block = "TEMP_BLOCK"
    perm_block = "PERM_BLOCK"
    honeypot_redirect = "HONEYPOT_REDIRECT"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    login_events: Mapped[list["LoginEvent"]] = relationship(back_populates="user")
    network_flows: Mapped[list["NetworkFlow"]] = relationship(back_populates="user")
    timeseries_points: Mapped[list["TimeSeriesPoint"]] = relationship(back_populates="user")


class LoginEvent(Base):
    __tablename__ = "login_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    source_ip: Mapped[str] = mapped_column(String(64), index=True)
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    success: Mapped[bool] = mapped_column(Boolean, index=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped["User | None"] = relationship(back_populates="login_events")


class NetworkFlow(Base):
    __tablename__ = "network_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    source_ip: Mapped[str] = mapped_column(String(64), index=True)
    destination_ip: Mapped[str] = mapped_column(String(64), index=True)
    protocol: Mapped[str] = mapped_column(String(16), index=True)
    bytes_in: Mapped[int] = mapped_column(Integer, default=0)
    bytes_out: Mapped[int] = mapped_column(Integer, default=0)
    packets: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tcp_flags: Mapped[dict] = mapped_column(JSON, default=dict)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped["User | None"] = relationship(back_populates="network_flows")


class TimeSeriesPoint(Base):
    __tablename__ = "timeseries_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    metric_name: Mapped[str] = mapped_column(String(64), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped["User | None"] = relationship(back_populates="timeseries_points")


class AttackSequenceEvent(Base):
    __tablename__ = "attack_sequence_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attack_family: Mapped[str] = mapped_column(String(64), index=True)
    signature: Mapped[str] = mapped_column(Text)
    tokens: Mapped[list[str]] = mapped_column(JSON, default=list)
    embedding_hint: Mapped[list[float]] = mapped_column(JSON, default=list)
    predicted_mutation: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class DefenseAction(Base):
    __tablename__ = "defense_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[DefenseActionType] = mapped_column(
        Enum(
            DefenseActionType,
            values_callable=lambda enum_values: [item.value for item in enum_values],
            native_enum=False,
        ),
        index=True,
    )
    reward: Mapped[float] = mapped_column(Float, default=0.0)
    decision_context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(128), index=True)
    model_version: Mapped[str] = mapped_column(String(32), index=True)
    model_type: Mapped[str] = mapped_column(String(64), index=True)
    artifact_path: Mapped[str] = mapped_column(String(512))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


Index("ix_login_user_time", LoginEvent.user_id, LoginEvent.created_at)
Index("ix_flow_src_dst_time", NetworkFlow.source_ip, NetworkFlow.destination_ip, NetworkFlow.created_at)
Index("ix_ts_metric_time", TimeSeriesPoint.metric_name, TimeSeriesPoint.created_at)
