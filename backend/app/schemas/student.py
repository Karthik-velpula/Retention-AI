from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBase


class LMSActivityBase(ORMBase):
    weekly_logins: int = Field(ge=0)
    avg_time_spent: float = Field(ge=0)
    assignment_submission_rate: float = Field(ge=0, le=100)
    missed_assignments: int = Field(ge=0)


class FinancialBase(ORMBase):
    fee_due: float = Field(ge=0)
    payment_delay_days: int = Field(ge=0)
    scholarship_amount: float = Field(ge=0)


class SubjectAttendanceBase(ORMBase):
    subject_name: str
    attendance_percentage: float = Field(ge=0, le=100)
    pre_t1_marks: float = Field(default=0, ge=0, le=10)
    t1_marks: float = Field(default=0, ge=0, le=20)
    t2_marks: float = Field(default=0, ge=0, le=5)
    t3_marks: float = Field(default=0, ge=0, le=5)
    t4_marks: float = Field(default=0, ge=0, le=20)
    t5_marks: float = Field(default=0, ge=0, le=20)
    t5_assignment_1: float = Field(default=0, ge=0, le=20)
    t5_assignment_2: float = Field(default=0, ge=0, le=20)
    t5_assignment_3: float = Field(default=0, ge=0, le=20)
    t5_assignment_4: float = Field(default=0, ge=0, le=20)
    total_marks: float = Field(default=0, ge=0, le=60)


class StudentBase(BaseModel):
    registration_number: str = Field(min_length=10, max_length=20)
    name: str
    email: EmailStr
    student_mobile: str = ""
    parent_mobile: str = ""
    counselor_name: str = ""
    codechef_username: str = "-"
    codechef_contests_participated: int = Field(default=0, ge=0)
    codechef_problems_solved: int = Field(default=0, ge=0)
    codechef_participation_status: str = "Not Available"
    codechef_last_synced_at: datetime | None = None
    section: str = "-"
    gender: str = "-"
    age: int | None = Field(default=None, ge=0, le=120)
    gpa: float = Field(ge=0, le=10)
    attendance: float = Field(ge=0, le=100)
    marks: float = Field(ge=0, le=100)
    pre_t1_marks: float = Field(default=0, ge=0, le=10)
    t1_marks: float = Field(default=0, ge=0, le=20)
    t2_marks: float = Field(default=0, ge=0, le=5)
    t3_marks: float = Field(default=0, ge=0, le=5)
    t4_marks: float = Field(default=0, ge=0, le=20)
    t5_marks: float = Field(default=0, ge=0, le=20)
    department: str
    year: int = Field(ge=1, le=6)
    career_interest: str
    skills: str = ""
    lms_activity: LMSActivityBase
    financial: FinancialBase


class StudentCreate(StudentBase):
    pass


class StudentUpdate(StudentBase):
    pass


class StudentResponse(StudentBase, ORMBase):
    id: int
    subject_attendance: list[SubjectAttendanceBase] = []


class StudentOverview(ORMBase):
    id: int
    registration_number: str
    name: str
    email: EmailStr
    student_mobile: str = ""
    parent_mobile: str = ""
    counselor_name: str | None = None
    codechef_username: str = "-"
    codechef_contests_participated: int = 0
    codechef_problems_solved: int = 0
    codechef_participation_status: str = "Not Available"
    codechef_last_synced_at: datetime | None = None
    section: str = "-"
    gender: str = "-"
    age: int | None = None
    gpa: float
    attendance: float
    lms_activity_percentage: float
    fees_paid_status: str
    marks: float
    pre_t1_marks: float = 0
    t1_marks: float = 0
    t2_marks: float = 0
    t3_marks: float = 0
    t4_marks: float = 0
    t5_marks: float = 0
    department: str
    year: int
    latest_risk_level: str | None = None
    latest_risk_score: float | None = None


class StudentOverviewPage(ORMBase):
    items: list[StudentOverview]
    total: int
    page: int
    page_size: int
