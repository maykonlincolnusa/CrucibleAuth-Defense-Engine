from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    pool_size=20 if "sqlite" not in settings.database_url else 5,
    max_overflow=40 if "sqlite" not in settings.database_url else 10,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
