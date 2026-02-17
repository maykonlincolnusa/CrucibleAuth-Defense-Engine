from datetime import datetime

from pydantic import BaseModel, Field


class NetworkFlowIn(BaseModel):
    user_id: str | None = None
    source_ip: str
    destination_ip: str
    protocol: str = Field(default="tcp")
    bytes_in: int = 0
    bytes_out: int = 0
    packets: int = 0
    duration_ms: float = 0.0
    tcp_flags: dict[str, int] = Field(default_factory=dict)


class NetworkFlowResult(BaseModel):
    anomaly_score: float
    anomaly_flag: bool
    action: str


class NetworkFlowStreamAck(BaseModel):
    accepted: bool
    mode: str
    topic: str | None = None


class TimeSeriesPointIn(BaseModel):
    user_id: str | None = None
    metric_name: str
    metric_value: float
    window_start: datetime
    window_end: datetime


class AttackSequenceIn(BaseModel):
    attack_family: str
    signature: str
    tokens: list[str]
    embedding_hint: list[float] = Field(default_factory=list)


class AttackSequenceOut(BaseModel):
    predicted_mutation: str
    mutation_risk: float
