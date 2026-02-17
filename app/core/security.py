from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
from typing import Any

try:
    from jose import jwt
except Exception:  # pragma: no cover - fallback for constrained envs
    jwt = None

try:
    from passlib.context import CryptContext
except Exception:  # pragma: no cover - fallback for constrained envs
    CryptContext = None

from app.core.config import get_settings


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") if CryptContext else None


def hash_password(password: str) -> str:
    if pwd_context:
        return pwd_context.hash(password)
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return f"sha256${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if pwd_context:
        return pwd_context.verify(plain_password, hashed_password)
    expected = hash_password(plain_password)
    return hmac.compare_digest(expected, hashed_password)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    if jwt is not None:
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    # Lightweight fallback token encoder (HS256-like) when python-jose is unavailable.
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).rstrip(b"=")
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, default=str).encode("utf-8")
    ).rstrip(b"=")
    signing_input = header_b64 + b"." + payload_b64
    signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        digestmod=hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return (signing_input + b"." + sig_b64).decode("utf-8")
