from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.pipeline import save_artifacts, train_models_from_dataframe


def _load_training_dataset() -> pd.DataFrame:
    dataset_path = Path(__file__).resolve().parents[2] / "data" / "student_retention_dataset.csv"
    return pd.read_csv(dataset_path)


def train_models(_: Session) -> dict[str, object]:
    dataset = _load_training_dataset()
    artifacts = train_models_from_dataframe(dataset)
    save_artifacts(artifacts)
    scoring_summary: dict[str, int] | None = None
    if _ is not None:
        from app.services.student_service import score_all_students

        scoring_summary = score_all_students(_)
    return {
        "status": "success",
        "message": "Models trained and saved successfully.",
        "metrics": artifacts.metrics,
        "scoring_summary": scoring_summary,
    }
