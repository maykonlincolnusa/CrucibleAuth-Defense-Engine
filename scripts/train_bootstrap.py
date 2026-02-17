from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.model_lifecycle_service import ModelLifecycleService


def run() -> None:
    init_db()
    with SessionLocal() as db:
        result = ModelLifecycleService(db).train_with_validation_and_rollback()
        print(result)


if __name__ == "__main__":
    run()
