from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMBase


class PredictionRequest(BaseModel):
    student_id: int | None = None
    gpa: float
    attendance: float
    marks: float
    weekly_logins: int
    avg_time_spent: float
    assignment_submission_rate: float
    missed_assignments: int
    fee_due: float
    payment_delay_days: int
    scholarship_amount: float
    department: str = "General"
    year: int = 1
    career_interest: str = "Data Analysis"
    skills: str = ""


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
    actual_value: str | float | int | None = None


class PredictionResponse(BaseModel):
    risk_level: str
    probability: float
    feature_importance: list[FeatureImportanceItem]
    explanation: str
    recommendations: list[str]
    comparison_model_probability: float


class SendAlertEmailRequest(BaseModel):
    student_id: int | None = None
    student_name: str
    student_email: str
    risk_level: str
    explanation: str
    recommendations: list[str]


class AlertHistoryResponse(ORMBase):
    id: int
    student_id: int | None = None
    sent_by: str
    recipient_name: str
    recipient_email: str
    risk_level: str
    status: str
    error_message: str
    created_at: datetime


class PredictionHistoryResponse(ORMBase):
    id: int
    student_id: int
    risk_score: float
    risk_level: str
    model_name: str
    explanation: str
    feature_importance: list[FeatureImportanceItem]
    recommendations: list[str]
    created_at: datetime
