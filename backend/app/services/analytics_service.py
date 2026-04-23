from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import and_, case, exists, func, not_, or_
from sqlalchemy.orm import Session, joinedload

from app.core.faculty_assignments import TEST_FACULTY_EMAIL
from app.models.financial import Financial
from app.models.intervention import Intervention
from app.models.lms_activity import LMSActivity
from app.models.student import Student
from app.models.subject_attendance import SubjectAttendance
from app.models.user import User
from app.schemas.analytics import AnalyticsResponse, FacultyPerformanceItem, FacultyPerformanceResponse, KPIResponse, TrendPoint
from app.services.student_service import _heuristic_overview_risk

SCATTER_POINT_LIMIT = 500
EXCLUDED_SUBJECT_ATTENDANCE_NAMES = {"lib001 library", "oc223 counseling"}


def _risk_points_expression():
    attendance_points = case(
        (Student.attendance < 65, 3),
        (Student.attendance < 75, 2),
        (Student.attendance < 85, 1),
        else_=0,
    )
    gpa_points = case(
        (Student.gpa < 5.5, 2),
        (Student.gpa < 7.0, 1),
        else_=0,
    )
    lms_points = case(
        (
            or_(
                LMSActivity.weekly_logins < 7,
                LMSActivity.assignment_submission_rate < 65,
                LMSActivity.missed_assignments >= 4,
            ),
            1,
        ),
        else_=0,
    )
    financial_points = case(
        (
            or_(
                Financial.fee_due > 0,
                Financial.payment_delay_days > 0,
            ),
            1,
        ),
        else_=0,
    )
    return attendance_points + gpa_points + lms_points + financial_points


def _non_lms_risk_points_expression():
    attendance_points = case(
        (Student.attendance < 65, 3),
        (Student.attendance < 75, 2),
        (Student.attendance < 85, 1),
        else_=0,
    )
    gpa_points = case(
        (Student.gpa < 5.5, 2),
        (Student.gpa < 7.0, 1),
        else_=0,
    )
    financial_points = case(
        (
            or_(
                Financial.fee_due > 0,
                Financial.payment_delay_days > 0,
            ),
            1,
        ),
        else_=0,
    )
    return attendance_points + gpa_points + financial_points


def _low_subject_attendance_exists_expression():
    return exists().where(
        and_(
            SubjectAttendance.student_id == Student.id,
            SubjectAttendance.attendance_percentage < 75,
            not_(func.lower(SubjectAttendance.subject_name).in_(EXCLUDED_SUBJECT_ATTENDANCE_NAMES)),
        )
    )


def build_analytics(db: Session, current_user: User) -> AnalyticsResponse:
    student_query = db.query(Student)
    if current_user.role == "faculty":
        student_query = student_query.filter(Student.counselor_name == current_user.name)

    base_query = student_query.outerjoin(Student.lms_activity).outerjoin(Student.financial)
    risk_points = _risk_points_expression()
    non_lms_risk_points = _non_lms_risk_points_expression()
    low_subject_attendance_exists = _low_subject_attendance_exists_expression()
    safe_condition = and_(
        Student.attendance >= 80,
        Student.gpa >= 8.0,
        LMSActivity.student_id.is_not(None),
        LMSActivity.assignment_submission_rate >= 80,
        Financial.student_id.is_not(None),
        Financial.fee_due <= 0,
        Financial.payment_delay_days <= 0,
    )
    high_condition = and_(not_(safe_condition), non_lms_risk_points >= 4)
    medium_condition = or_(
        and_(safe_condition, low_subject_attendance_exists),
        and_(not_(safe_condition), non_lms_risk_points < 4, or_(risk_points >= 2, low_subject_attendance_exists)),
    )
    low_condition = and_(
        not_(safe_condition),
        non_lms_risk_points < 4,
        risk_points < 2,
        not_(low_subject_attendance_exists),
    )
    risk_score_expr = case(
        (non_lms_risk_points >= 4, 0.85),
        (risk_points >= 2, 0.65),
        else_=0.35,
    )

    total_students, average_gpa, average_attendance = (
        base_query.with_entities(
            func.count(Student.id),
            func.avg(Student.gpa),
            func.avg(Student.attendance),
        ).one()
    )

    safe_risk_students, low_risk_students, medium_risk_students, high_risk_students = (
        base_query.with_entities(
            func.sum(case((and_(safe_condition, not_(low_subject_attendance_exists)), 1), else_=0)),
            func.sum(case((low_condition, 1), else_=0)),
            func.sum(case((medium_condition, 1), else_=0)),
            func.sum(case((high_condition, 1), else_=0)),
        ).one()
    )

    action_needed_today = (
        student_query.outerjoin(Student.lms_activity)
        .outerjoin(Student.financial)
        .outerjoin(Student.intervention)
        .filter(non_lms_risk_points >= 4, Student.attendance < 75)
        .filter(
            or_(
                Intervention.id.is_(None),
                Intervention.status != "resolved",
            )
        )
        .with_entities(func.count(Student.id))
        .scalar()
        or 0
    )

    department_risk_rows = (
        base_query.with_entities(
            Student.department,
            func.avg(risk_score_expr),
        )
        .group_by(Student.department)
        .all()
    )
    department_risk = [
        TrendPoint(label=department or "-", value=round(float(score or 0), 2))
        for department, score in department_risk_rows
    ]

    attendance_vs_gpa_rows = (
        student_query.with_entities(Student.name, Student.attendance, Student.gpa)
        .order_by(Student.id.asc())
        .limit(SCATTER_POINT_LIMIT)
        .all()
    )
    attendance_vs_gpa = [
        {"student": name, "attendance": float(attendance), "gpa": float(gpa)}
        for name, attendance, gpa in attendance_vs_gpa_rows
    ]

    total_students = int(total_students or 0)

    return AnalyticsResponse(
        kpis=KPIResponse(
            total_students=total_students,
            high_risk_students=int(high_risk_students or 0),
            action_needed_today=int(action_needed_today),
            medium_risk_students=int(medium_risk_students or 0),
            low_risk_students=int(low_risk_students or 0),
            safe_risk_students=int(safe_risk_students or 0),
            average_gpa=round(float(average_gpa or 0), 2),
            average_attendance=round(float(average_attendance or 0), 2),
        ),
        risk_distribution=[
            TrendPoint(label="Safe", value=int(safe_risk_students or 0)),
            TrendPoint(label="Low", value=int(low_risk_students or 0)),
            TrendPoint(label="Medium", value=int(medium_risk_students or 0)),
            TrendPoint(label="High", value=int(high_risk_students or 0)),
        ],
        department_risk=department_risk,
        attendance_vs_gpa=attendance_vs_gpa,
    )


def build_faculty_performance(db: Session) -> FacultyPerformanceResponse:
    faculty_users = (
        db.query(User)
        .filter(User.role == "faculty", User.email != TEST_FACULTY_EMAIL)
        .order_by(User.name.asc())
        .all()
    )
    students = (
        db.query(Student)
        .options(joinedload(Student.predictions), joinedload(Student.intervention))
        .order_by(Student.registration_number.asc())
        .all()
    )

    now = datetime.now()
    week_ago = now - timedelta(days=7)
    by_faculty: dict[str, list[Student]] = defaultdict(list)
    for student in students:
        by_faculty[student.counselor_name].append(student)

    summary: list[FacultyPerformanceItem] = []
    for faculty in faculty_users:
        assigned = by_faculty.get(faculty.name, [])
        high_risk_students = 0
        medium_risk_students = 0
        overdue_followups = 0
        resolved_this_week = 0

        for student in assigned:
            risk_level, _ = _heuristic_overview_risk(student)
            if risk_level == "High":
                high_risk_students += 1
            elif risk_level == "Medium":
                medium_risk_students += 1

            intervention: Intervention | None = student.intervention
            if intervention and intervention.status != "resolved" and intervention.next_follow_up_date:
                if intervention.next_follow_up_date < now.date():
                    overdue_followups += 1
            if intervention and intervention.status == "resolved" and intervention.resolved_at:
                if intervention.resolved_at >= week_ago:
                    resolved_this_week += 1

        summary.append(
            FacultyPerformanceItem(
                faculty_name=faculty.name,
                assigned_students=len(assigned),
                high_risk_students=high_risk_students,
                medium_risk_students=medium_risk_students,
                overdue_followups=overdue_followups,
                resolved_this_week=resolved_this_week,
                average_attendance=round(sum(student.attendance for student in assigned) / len(assigned), 2) if assigned else 0,
            )
        )

    summary.sort(
        key=lambda item: (
            -item.high_risk_students,
            -item.medium_risk_students,
            -item.assigned_students,
            item.faculty_name.casefold(),
        )
    )

    return FacultyPerformanceResponse(faculty_summary=summary)
