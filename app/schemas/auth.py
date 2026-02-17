from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginInput(BaseModel):
    username: str
    password: str
    source_ip: str = "0.0.0.0"
    user_agent: str = ""
    latency_ms: float = 0.0


class LoginResult(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    authenticated: bool
    risk_score: float
    action: str
    message: str
