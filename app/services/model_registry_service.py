from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import ModelArtifact


class ModelRegistryService:
    def __init__(self, db: Session):
        self.db = db

    def register(
        self,
        model_name: str,
        model_version: str,
        model_type: str,
        artifact_path: str,
        metrics: dict,
    ) -> ModelArtifact:
        self.db.query(ModelArtifact).filter(
            ModelArtifact.model_name == model_name,
            ModelArtifact.is_active.is_(True),
        ).update({"is_active": False})

        artifact = ModelArtifact(
            model_name=model_name,
            model_version=model_version,
            model_type=model_type,
            artifact_path=artifact_path,
            metrics=metrics,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def list_active(self) -> list[ModelArtifact]:
        return (
            self.db.query(ModelArtifact)
            .filter(ModelArtifact.is_active.is_(True))
            .order_by(ModelArtifact.created_at.desc())
            .all()
        )
