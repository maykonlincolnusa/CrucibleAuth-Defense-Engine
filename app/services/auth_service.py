from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User
from app.schemas.auth import UserCreate


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, payload: UserCreate) -> User:
        user = User(
            username=payload.username.lower().strip(),
            email=payload.email.lower().strip(),
            password_hash=hash_password(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_username(self, username: str) -> User | None:
        return (
            self.db.query(User)
            .filter(User.username == username.lower().strip(), User.is_active.is_(True))
            .first()
        )

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
