from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from collections import Counter
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from app.core.config import settings
from app.ml.features import CATEGORICAL_COLUMNS, FEATURE_COLUMNS, TARGET_COLUMN


@dataclass
class TrainedArtifacts:
    random_forest: Pipeline
    logistic_regression: Pipeline
    label_encoder: LabelEncoder
    feature_names: list[str]
    metrics: dict[str, dict[str, float | str]]


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    if "cgpa" in prepared.columns and "gpa" not in prepared.columns:
        prepared["gpa"] = prepared["cgpa"]
    if "lms_activity_status" not in prepared.columns:
        prepared["lms_activity_status"] = prepared.apply(
            lambda row: derive_lms_activity_status(
                row["weekly_logins"],
                row["avg_time_spent"],
                row["assignment_submission_rate"],
                row["missed_assignments"],
            ),
            axis=1,
        )
    if "fees_paid_status" not in prepared.columns:
        prepared["fees_paid_status"] = prepared.apply(
            lambda row: derive_fees_paid_status(
                row.get("fee_due", 0),
                row.get("payment_delay_days", 0),
                row.get("fees_paid_status"),
            ),
            axis=1,
        )
    prepared[TARGET_COLUMN] = prepared[TARGET_COLUMN].astype(str).str.strip().str.title()
    prepared = prepared[prepared[TARGET_COLUMN].isin({"Low", "Medium", "High"})].copy()
    return prepared


def derive_lms_activity_status(
    weekly_logins: float,
    avg_time_spent: float,
    assignment_submission_rate: float,
    missed_assignments: float,
) -> str:
    if weekly_logins >= 12 and avg_time_spent >= 5 and assignment_submission_rate >= 80 and missed_assignments <= 2:
        return "Active"
    if weekly_logins >= 7 and avg_time_spent >= 3 and assignment_submission_rate >= 60 and missed_assignments <= 4:
        return "Moderate"
    return "Low"


def derive_fees_paid_status(
    fee_due: float | None = None,
    payment_delay_days: float | None = None,
    existing_status: str | None = None,
) -> str:
    if existing_status in {"Paid", "Not Paid"}:
        return existing_status
    due = float(fee_due or 0)
    delay = float(payment_delay_days or 0)
    return "Paid" if due <= 0 and delay <= 0 else "Not Paid"


def build_preprocessor() -> ColumnTransformer:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    transformers = [("num", numeric_transformer, FEATURE_COLUMNS)]
    if CATEGORICAL_COLUMNS:
        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]
        )
        transformers.append(("cat", categorical_transformer, CATEGORICAL_COLUMNS))

    return ColumnTransformer(transformers=transformers)


def train_models_from_dataframe(df: pd.DataFrame) -> TrainedArtifacts:
    prepared = prepare_dataframe(df)
    X = prepared[FEATURE_COLUMNS + CATEGORICAL_COLUMNS]
    y = prepared[TARGET_COLUMN]

    class_counts = Counter(y)
    use_stratify = min(class_counts.values()) >= 2 if class_counts else False

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_encoded,
        test_size=0.2,
        random_state=42,
        stratify=y_encoded if use_stratify else None,
    )

    preprocessor = build_preprocessor()
    rf_pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced")),
        ]
    )
    lr_pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("classifier", LogisticRegression(max_iter=300, class_weight="balanced")),
        ]
    )

    rf_pipeline.fit(X_train, y_train)
    lr_pipeline.fit(X_train, y_train)

    y_pred_rf = rf_pipeline.predict(X_test)
    y_proba_rf = rf_pipeline.predict_proba(X_test)
    y_pred_lr = lr_pipeline.predict(X_test)
    y_proba_lr = lr_pipeline.predict_proba(X_test)
    labels = list(range(len(label_encoder.classes_)))

    feature_names = list(
        rf_pipeline.named_steps["preprocessor"].get_feature_names_out(FEATURE_COLUMNS + CATEGORICAL_COLUMNS)
    )

    def safe_roc_auc(y_true, y_proba) -> float | None:
        unique_classes = np.unique(y_true)
        if len(unique_classes) < 2:
            return None
        return round(float(roc_auc_score(y_true, y_proba, multi_class="ovr", labels=labels)), 4)

    metrics = {
        "random_forest": {
            "accuracy": round(float(accuracy_score(y_test, y_pred_rf)), 4),
            "roc_auc_ovr": safe_roc_auc(y_test, y_proba_rf),
            "report": classification_report(
                y_test,
                y_pred_rf,
                labels=labels,
                target_names=label_encoder.classes_,
                zero_division=0,
            ),
        },
        "logistic_regression": {
            "accuracy": round(float(accuracy_score(y_test, y_pred_lr)), 4),
            "roc_auc_ovr": safe_roc_auc(y_test, y_proba_lr),
            "report": classification_report(
                y_test,
                y_pred_lr,
                labels=labels,
                target_names=label_encoder.classes_,
                zero_division=0,
            ),
        },
    }

    return TrainedArtifacts(
        random_forest=rf_pipeline,
        logistic_regression=lr_pipeline,
        label_encoder=label_encoder,
        feature_names=feature_names,
        metrics=metrics,
    )


def save_artifacts(artifacts: TrainedArtifacts) -> None:
    model_dir = settings.MODEL_DIR_PATH
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifacts.random_forest, settings.MODEL_PATH)
    joblib.dump(artifacts.logistic_regression, str(model_dir / "comparison_model.pkl"))
    joblib.dump(artifacts.label_encoder, settings.LABEL_ENCODER_PATH)
    joblib.dump(artifacts.feature_names, settings.FEATURE_COLUMNS_PATH)


def load_artifacts() -> dict[str, object]:
    model_dir = settings.MODEL_DIR_PATH
    return {
        "model": joblib.load(settings.MODEL_PATH),
        "comparison_model": joblib.load(str(model_dir / "comparison_model.pkl")),
        "label_encoder": joblib.load(settings.LABEL_ENCODER_PATH),
        "feature_names": joblib.load(settings.FEATURE_COLUMNS_PATH),
    }


def build_shap_explanation(model: Pipeline, feature_names: list[str], payload_df: pd.DataFrame) -> list[dict[str, float | str]]:
    transformed = model.named_steps["preprocessor"].transform(payload_df)
    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    classifier = model.named_steps["classifier"]
    try:
        explainer = shap.TreeExplainer(classifier)
        shap_values = explainer.shap_values(transformed)

        if isinstance(shap_values, list):
            scores = np.mean(np.abs(np.array(shap_values)), axis=0)
            if scores.ndim == 2:
                importances = scores.mean(axis=0)
            else:
                importances = scores
        else:
            importances = np.abs(shap_values).mean(axis=0)
            if importances.ndim > 1:
                importances = importances.mean(axis=0)
    except Exception:
        importances = getattr(classifier, "feature_importances_", np.ones(len(feature_names)))

    ranked = sorted(
        [{"feature": feature, "importance": round(float(score), 4)} for feature, score in zip(feature_names, importances)],
        key=lambda item: item["importance"],
        reverse=True,
    )
    return ranked[:6]
