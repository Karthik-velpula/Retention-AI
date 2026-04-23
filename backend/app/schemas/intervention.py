from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.common import ORMBase


InterventionStatus = Literal["pending", "in_progress", "resolved"]
FollowUpOutcome = Literal["attended", "missed", "rescheduled", "resolved"]


class InterventionUpsert(BaseModel):
    contacted_student: bool = False
    parent_informed: bool = False
    counselor_assigned: bool = False
    fee_issue_escalated: bool = False
    next_follow_up_date: date | None = None
    follow_up_outcome: FollowUpOutcome | None = None
    status: InterventionStatus = "pending"
    notes: str = ""


class InterventionAssistRequest(BaseModel):
    contacted_student: bool = False
    parent_informed: bool = False
    counselor_assigned: bool = False
    fee_issue_escalated: bool = False
    status: InterventionStatus = "pending"


class InterventionResponse(ORMBase):
    id: int
    student_id: int
    contacted_student: bool
    parent_informed: bool
    counselor_assigned: bool
    fee_issue_escalated: bool
    next_follow_up_date: date | None = None
    follow_up_outcome: FollowUpOutcome | None = None
    status: InterventionStatus
    resolved_at: datetime | None = None
    notes: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class InterventionHistoryResponse(ORMBase):
    id: int
    intervention_id: int
    student_id: int
    changed_by: str
    changed_fields: str
    change_summary: str
    created_at: datetime


class InterventionSaveResponse(BaseModel):
    intervention: InterventionResponse
    history_entry: InterventionHistoryResponse | None = None
    email_status: str
    email_detail: str


class InterventionAssistResponse(BaseModel):
    suggested_note: str
    recommended_follow_up_date: date | None = None
    suggest_parent_informed: bool
    parent_informed_reason: str


class InterventionStudentOverview(ORMBase):
    student_id: int
    registration_number: str
    student_name: str
    student_email: str
    counselor_name: str
    attendance: float
    latest_risk_level: str
    latest_risk_score: float
    intervention: InterventionResponse | None = None
    history: list[InterventionHistoryResponse] = []
