from pydantic import BaseModel


class KPIResponse(BaseModel):
    total_students: int
    high_risk_students: int
    action_needed_today: int
    medium_risk_students: int
    low_risk_students: int
    safe_risk_students: int
    average_gpa: float
    average_attendance: float


class TrendPoint(BaseModel):
    label: str
    value: float


class AnalyticsResponse(BaseModel):
    kpis: KPIResponse
    risk_distribution: list[TrendPoint]
    department_risk: list[TrendPoint]
    attendance_vs_gpa: list[dict[str, float | str]]


class FacultyPerformanceItem(BaseModel):
    faculty_name: str
    assigned_students: int
    high_risk_students: int
    medium_risk_students: int
    overdue_followups: int
    resolved_this_week: int
    average_attendance: float


class FacultyPerformanceResponse(BaseModel):
    faculty_summary: list[FacultyPerformanceItem]
