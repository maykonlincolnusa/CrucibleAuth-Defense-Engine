from pathlib import Path
from typing import Any

import joblib


class PersistableModel:
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> Any:
        return joblib.load(path)
