try:
    from alembic import command
    from alembic.config import Config
except Exception:  # pragma: no cover - fallback for minimal environments
    command = None
    Config = None
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import User
from app.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def run_migrations() -> None:
    if not command or not Config:
        init_db()
        return
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def ensure_default_admin(db: Session) -> None:
    user = db.query(User).filter(User.username == "admin").first()
    if user:
        return
    admin = User(
        username="admin",
        email="admin@security.local",
        password_hash=hash_password("Admin123!"),
        role="admin",
    )
    db.add(admin)
    db.commit()
