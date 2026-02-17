from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.security import create_access_token
from app.schemas.auth import LoginInput, LoginResult, UserCreate, UserOut
from app.services.auth_service import AuthService
from app.services.defense_orchestrator import DefenseOrchestrator

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db_session)):
    auth_service = AuthService(db)

    if auth_service.get_user_by_username(payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")

    user = auth_service.create_user(payload)
    return user


@router.post("/login", response_model=LoginResult)
def login(payload: LoginInput, db: Session = Depends(get_db_session)):
    auth_service = AuthService(db)
    defense = DefenseOrchestrator(db)

    user = auth_service.authenticate(payload.username, payload.password)
    authenticated = user is not None

    decision = defense.evaluate_login(
        username=payload.username,
        source_ip=payload.source_ip,
        user_agent=payload.user_agent,
        latency_ms=payload.latency_ms,
        authenticated=authenticated,
        user=user,
    )

    token = create_access_token(subject=user.id, extra={"username": user.username}) if user else None

    message = "Login autorizado"
    if not authenticated:
        message = "Credenciais invalidas"
    if decision["action"] in {"TEMP_BLOCK", "PERM_BLOCK"}:
        message = "Tentativa bloqueada pelo motor de defesa"

    return {
        "access_token": token,
        "authenticated": authenticated,
        "risk_score": decision["risk_score"],
        "action": decision["action"],
        "message": message,
    }
