from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Integer, and_, case, cast, exists, func, not_, or_, String
from sqlalchemy.orm import Session, joinedload

from app.models.financial import Financial
from app.models.lms_activity import LMSActivity
from app.models.prediction import Prediction
from app.models.student import Student
from app.models.subject_attendance import SubjectAttendance
from app.models.user import User
from app.ml.features import CATEGORICAL_COLUMNS, FEATURE_COLUMNS
from app.ml.pipeline import (
    build_shap_explanation,
    derive_fees_paid_status,
    derive_lms_activity_status,
    load_artifacts,
)
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.email_service import send_risk_alert_email
from app.services.recommendation_service import build_recommendations

EXCLUDED_SUBJECT_ATTENDANCE_NAMES = {"lib001 library", "oc223 counseling"}


def normalize_student_email(email: str) -> str:
    cleaned = email.strip().lower()
    if cleaned.endswith("@retentionai.local"):
        return cleaned.replace("@retentionai.local", "@gmail.com")
    if cleaned.endswith("@retentionai.edu"):
        return cleaned.replace("@retentionai.edu", "@gmail.com")
    if cleaned.endswith("@vignan.ac.in"):
        return cleaned.replace("@vignan.ac.in", "@gmail.com")
    return cleaned


def _row_value(row: dict, *keys: str, default=None):
    for key in keys:
        if key in row and pd.notna(row[key]):
            return row[key]
    return default


def _subject_attendance_name_is_excluded(subject_name: str | None) -> bool:
    return (subject_name or "").strip().lower() in EXCLUDED_SUBJECT_ATTENDANCE_NAMES


def _has_low_non_excluded_subject_attendance(student: Student) -> bool:
    return any(
        item.attendance_percentage < 75 and not _subject_attendance_name_is_excluded(item.subject_name)
        for item in (student.subject_attendance or [])
    )


def _normalized_gpa_attendance(student: Student) -> tuple[float, float]:
    gpa = float(student.gpa or 0)
    attendance = float(student.attendance or 0)
    if gpa > 10 and attendance <= 10:
        return attendance, gpa
    return gpa, attendance


def _low_subject_attendance_exists_expression():
    return exists().where(
        and_(
            SubjectAttendance.student_id == Student.id,
            SubjectAttendance.attendance_percentage < 75,
            not_(func.lower(SubjectAttendance.subject_name).in_(EXCLUDED_SUBJECT_ATTENDANCE_NAMES)),
        )
    )


def _apply_subject_attendance_guard(
    risk_level: str,
    probability: float,
    student: Student | None,
) -> tuple[str, float]:
    if not student or risk_level not in {"Safe", "Low"}:
        return risk_level, probability
    if _has_low_non_excluded_subject_attendance(student):
        return "Medium", max(probability, 0.65)
    return risk_level, probability


def _heuristic_overview_risk(student: Student) -> tuple[str, float]:
    academic_financial_points = 0
    lms_points = 0
    gpa, attendance = _normalized_gpa_attendance(student)

    if attendance < 65:
        academic_financial_points += 3
    elif attendance < 75:
        academic_financial_points += 2
    elif attendance < 85:
        academic_financial_points += 1

    if gpa < 5.5:
        academic_financial_points += 2
    elif gpa < 7.0:
        academic_financial_points += 1

    if student.lms_activity:
        if (
            student.lms_activity.weekly_logins < 7
            or student.lms_activity.assignment_submission_rate < 65
            or student.lms_activity.missed_assignments >= 4
        ):
            lms_points += 1

    if student.financial and (student.financial.fee_due > 0 or student.financial.payment_delay_days > 0):
        academic_financial_points += 1

    total_points = academic_financial_points + lms_points

    if (
        attendance >= 80
        and gpa >= 8.0
        and student.lms_activity
        and student.lms_activity.assignment_submission_rate >= 80
        and student.financial
        and student.financial.fee_due <= 0
        and student.financial.payment_delay_days <= 0
    ):
        return _apply_subject_attendance_guard("Safe", 0.15, student)
    if academic_financial_points >= 4:
        return "High", 0.85
    if total_points >= 2:
        return "Medium", 0.65
    if total_points == 1:
        return _apply_subject_attendance_guard("Low", 0.35, student)
    return _apply_subject_attendance_guard("Low", 0.35, student)


def _student_belongs_to_user(student: Student, current_user: User) -> bool:
    return current_user.role == "admin" or student.counselor_name == current_user.name


def _sync_lms_activity_from_codechef(student: Student) -> None:
    if not student.lms_activity:
        return
    if not student.codechef_username or student.codechef_username == "-":
        return

    contests = max(student.codechef_contests_participated or 0, 0)
    solved = max(student.codechef_problems_solved or 0, 0)
    if contests <= 0 and solved <= 0:
        return

    # Use contest participation as a supplemental engagement signal only when
    # we have actual participation counts, not just a linked username.
    student.lms_activity.weekly_logins = max(student.lms_activity.weekly_logins, min(3 + contests, 14))
    student.lms_activity.avg_time_spent = max(student.lms_activity.avg_time_spent, min(1.0 + solved * 0.15, 10.0))
    student.lms_activity.assignment_submission_rate = max(
        student.lms_activity.assignment_submission_rate,
        min(35 + contests * 10 + solved * 1.5, 100.0),
    )
    student.lms_activity.missed_assignments = min(student.lms_activity.missed_assignments, max(0, 6 - contests))


def _filtered_students_query(db: Session, current_user: User):
    query = db.query(Student)
    if current_user.role == "faculty":
        query = query.filter(Student.counselor_name == current_user.name)
    return query


def _student_section_order():
    return (
        cast(Student.section, Integer).asc(),
        Student.section.asc(),
        Student.registration_number.asc(),
        Student.id.asc(),
    )


def _lms_risk_points_expression():
    return case(
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


def _academic_financial_risk_points_expression():
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


def _safe_condition_expression():
    return (
        (Student.attendance >= 80)
        & (Student.gpa >= 8.0)
        & (LMSActivity.assignment_submission_rate >= 80)
        & (Financial.fee_due <= 0)
        & (Financial.payment_delay_days <= 0)
    )


def _safe_condition_without_subject_guard_expression():
    return _safe_condition_expression() & ~_low_subject_attendance_exists_expression()


def _student_overview(student: Student) -> dict[str, object]:
    fallback_risk_level, fallback_risk_score = _heuristic_overview_risk(student)
    gpa, attendance = _normalized_gpa_attendance(student)
    return {
        "id": student.id,
        "registration_number": student.registration_number,
        "name": student.name,
        "email": student.email,
        "student_mobile": student.student_mobile or "",
        "parent_mobile": student.parent_mobile or "",
        "counselor_name": student.counselor_name,
        "codechef_username": student.codechef_username,
        "codechef_contests_participated": student.codechef_contests_participated,
        "codechef_problems_solved": student.codechef_problems_solved,
        "codechef_participation_status": student.codechef_participation_status,
        "codechef_last_synced_at": student.codechef_last_synced_at,
        "section": student.section,
        "gender": student.gender,
        "age": student.age,
        "gpa": gpa,
        "attendance": attendance,
        "lms_activity_percentage": float(student.lms_activity.assignment_submission_rate) if student.lms_activity else 0.0,
        "fees_paid_status": derive_fees_paid_status(
            student.financial.fee_due if student.financial else 0,
            student.financial.payment_delay_days if student.financial else 0,
        ),
        "marks": student.marks,
        "pre_t1_marks": student.pre_t1_marks,
        "t1_marks": student.t1_marks,
        "t2_marks": student.t2_marks,
        "t3_marks": student.t3_marks,
        "t4_marks": student.t4_marks,
        "t5_marks": student.t5_marks,
        "department": student.department,
        "year": student.year,
        "latest_risk_level": fallback_risk_level,
        "latest_risk_score": fallback_risk_score,
    }


def student_detail_response(student: Student) -> dict[str, object]:
    gpa, attendance = _normalized_gpa_attendance(student)
    return {
        "id": student.id,
        "registration_number": student.registration_number,
        "name": student.name,
        "email": student.email,
        "student_mobile": student.student_mobile or "",
        "parent_mobile": student.parent_mobile or "",
        "counselor_name": student.counselor_name or "",
        "codechef_username": student.codechef_username or "-",
        "codechef_contests_participated": student.codechef_contests_participated or 0,
        "codechef_problems_solved": student.codechef_problems_solved or 0,
        "codechef_participation_status": student.codechef_participation_status or "Not Available",
        "codechef_last_synced_at": student.codechef_last_synced_at,
        "section": student.section or "-",
        "gender": student.gender or "-",
        "age": student.age,
        "gpa": gpa,
        "attendance": attendance,
        "marks": student.marks,
        "pre_t1_marks": student.pre_t1_marks,
        "t1_marks": student.t1_marks,
        "t2_marks": student.t2_marks,
        "t3_marks": student.t3_marks,
        "t4_marks": student.t4_marks,
        "t5_marks": student.t5_marks,
        "department": student.department,
        "year": student.year,
        "career_interest": student.career_interest,
        "skills": student.skills or "",
        "lms_activity": student.lms_activity,
        "financial": student.financial,
        "subject_attendance": student.subject_attendance or [],
    }


def list_students(db: Session, current_user: User) -> list[Student]:
    students = (
        _filtered_students_query(db, current_user)
        .options(joinedload(Student.lms_activity), joinedload(Student.financial), joinedload(Student.subject_attendance))
        .order_by(*_student_section_order())
        .all()
    )
    return [_student_overview(student) for student in students]


def list_counselors(db: Session, current_user: User) -> list[str]:
    query = _filtered_students_query(db, current_user).with_entities(Student.counselor_name).distinct()
    counselors = [
        (name or "").strip()
        for (name,) in query.all()
    ]
    return sorted([name for name in counselors if name and name != "-"], key=str.lower)


def list_students_page(
    db: Session,
    current_user: User,
    *,
    page: int,
    page_size: int,
    query: str | None = None,
    risk_level: str | None = None,
    attendance_filter: str | None = None,
    fee_status: str | None = None,
    counselor_name: str | None = None,
    section: str | None = None,
    gender: str | None = None,
    year: int | None = None,
    min_cgpa: float | None = None,
    max_cgpa: float | None = None,
) -> dict[str, object]:
    base_query = (
        _filtered_students_query(db, current_user)
        .outerjoin(Student.lms_activity)
        .outerjoin(Student.financial)
    )

    if query:
        normalized_query = f"%{query.strip().lower()}%"
        base_query = base_query.filter(
            or_(
                func.lower(Student.name).like(normalized_query),
                func.lower(Student.email).like(normalized_query),
                func.lower(Student.registration_number).like(normalized_query),
                func.lower(Student.counselor_name).like(normalized_query),
                func.lower(Student.section).like(normalized_query),
                func.lower(Student.gender).like(normalized_query),
                cast(Student.year, String).like(normalized_query),
                cast(Student.age, String).like(normalized_query),
                cast(Student.gpa, String).like(normalized_query),
                func.lower(Student.department).like(normalized_query),
            )
        )

    if attendance_filter == "Below 65%":
        base_query = base_query.filter(Student.attendance < 65)
    elif attendance_filter == "Below 75%":
        base_query = base_query.filter(Student.attendance < 75)
    elif attendance_filter == "Below 85%":
        base_query = base_query.filter(Student.attendance < 85)

    if fee_status == "Paid":
        base_query = base_query.filter(
            or_(Financial.id.is_(None), (Financial.fee_due <= 0) & (Financial.payment_delay_days <= 0))
        )
    elif fee_status == "Not Paid":
        base_query = base_query.filter(
            Financial.id.is_not(None),
            or_(Financial.fee_due > 0, Financial.payment_delay_days > 0),
        )

    if counselor_name and counselor_name != "All":
        base_query = base_query.filter(Student.counselor_name == counselor_name)
    if section and section != "All":
        base_query = base_query.filter(Student.section == section)
    if gender and gender != "All":
        base_query = base_query.filter(Student.gender == gender)
    if year is not None:
        base_query = base_query.filter(Student.year == year)
    if min_cgpa is not None:
        base_query = base_query.filter(Student.gpa >= min_cgpa)
    if max_cgpa is not None:
        base_query = base_query.filter(Student.gpa <= max_cgpa)

    academic_financial_points = _academic_financial_risk_points_expression()
    lms_points = _lms_risk_points_expression()
    total_points = academic_financial_points + lms_points
    low_subject_attendance_exists = _low_subject_attendance_exists_expression()
    safe_condition = _safe_condition_without_subject_guard_expression()
    if risk_level == "High":
        base_query = base_query.filter(~safe_condition, academic_financial_points >= 4)
    elif risk_level == "Medium":
        base_query = base_query.filter(
            or_(
                and_(~safe_condition, academic_financial_points < 4, total_points >= 2),
                and_(low_subject_attendance_exists, total_points < 2),
            )
        )
    elif risk_level == "Low":
        base_query = base_query.filter(~safe_condition, ~low_subject_attendance_exists, total_points < 2)
    elif risk_level == "Safe":
        base_query = base_query.filter(safe_condition)

    total = base_query.with_entities(func.count(Student.id)).scalar() or 0
    students = (
        base_query.options(joinedload(Student.lms_activity), joinedload(Student.financial), joinedload(Student.subject_attendance))
        .order_by(*_student_section_order())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_student_overview(student) for student in students],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_student(db: Session, student_id: int, current_user: User) -> Student:
    student = (
        _filtered_students_query(db, current_user)
        .options(
            joinedload(Student.lms_activity),
            joinedload(Student.financial),
            joinedload(Student.predictions),
            joinedload(Student.subject_attendance),
        )
        .filter(Student.id == student_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found or not assigned")
    return student


def create_student(db: Session, payload: StudentCreate, current_user: User) -> Student:
    existing = db.query(Student).filter(Student.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student email already exists")

    student = Student(
        registration_number=payload.registration_number,
        name=payload.name,
        email=payload.email,
        student_mobile=payload.student_mobile,
        parent_mobile=payload.parent_mobile,
        counselor_name=payload.counselor_name,
        codechef_username=payload.codechef_username,
        codechef_contests_participated=payload.codechef_contests_participated,
        codechef_problems_solved=payload.codechef_problems_solved,
        codechef_participation_status=payload.codechef_participation_status,
        codechef_last_synced_at=payload.codechef_last_synced_at,
        section=payload.section,
        gender=payload.gender,
        age=payload.age,
        gpa=payload.gpa,
        attendance=payload.attendance,
        marks=payload.marks,
        pre_t1_marks=payload.pre_t1_marks,
        t1_marks=payload.t1_marks,
        t2_marks=payload.t2_marks,
        t3_marks=payload.t3_marks,
        t4_marks=payload.t4_marks,
        t5_marks=payload.t5_marks,
        department=payload.department,
        year=payload.year,
        career_interest=payload.career_interest,
        skills=payload.skills,
    )
    student.lms_activity = LMSActivity(**payload.lms_activity.model_dump())
    student.financial = Financial(**payload.financial.model_dump())
    _sync_lms_activity_from_codechef(student)
    db.add(student)
    db.commit()
    db.refresh(student)
    return get_student(db, student.id, current_user)


def update_student(db: Session, student_id: int, payload: StudentUpdate, current_user: User) -> Student:
    student = get_student(db, student_id, current_user)
    for field, value in payload.model_dump(exclude={"lms_activity", "financial"}).items():
        setattr(student, field, value)
    for field, value in payload.lms_activity.model_dump().items():
        setattr(student.lms_activity, field, value)
    for field, value in payload.financial.model_dump().items():
        setattr(student.financial, field, value)
    _sync_lms_activity_from_codechef(student)
    db.commit()
    db.refresh(student)
    return get_student(db, student.id, current_user)


def delete_student(db: Session, student_id: int, current_user: User) -> dict[str, str]:
    student = get_student(db, student_id, current_user)
    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully"}


async def upload_students_csv(db: Session, file: UploadFile) -> dict[str, object]:
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    inserted = 0
    for row in df.to_dict(orient="records"):
        normalized_email = normalize_student_email(row["email"])
        existing = db.query(Student).filter(Student.email == normalized_email).first()
        if existing:
            continue
        cgpa = float(_row_value(row, "cgpa", "gpa", default=0))
        student = Student(
            registration_number=str(_row_value(row, "registration_number", default=f"REG{inserted + 1:05d}")),
            name=row["name"],
            email=normalized_email,
            student_mobile="",
            parent_mobile="",
            counselor_name=_row_value(row, "counselor_name", default=""),
            section=str(_row_value(row, "section", "sectioncode", default="-")),
            gender=str(_row_value(row, "gender", default="-")),
            age=int(_row_value(row, "age", default=0)) or None,
            gpa=cgpa,
            attendance=float(row["attendance"]),
            marks=float(_row_value(row, "marks", default=round(cgpa * 10, 2))),
            pre_t1_marks=float(_row_value(row, "pre_t1_marks", default=0)),
            t1_marks=float(_row_value(row, "t1_marks", default=0)),
            t2_marks=float(_row_value(row, "t2_marks", default=0)),
            t3_marks=float(_row_value(row, "t3_marks", default=0)),
            t4_marks=float(_row_value(row, "t4_marks", default=0)),
            t5_marks=float(_row_value(row, "t5_marks", default=0)),
            department="CSE",
            year=int(_row_value(row, "year", default=1)),
            career_interest=_row_value(row, "career_interest", default="Academic Advising"),
            skills=_row_value(row, "skills", default=""),
        )
        student.lms_activity = LMSActivity(
            weekly_logins=int(row["weekly_logins"]),
            avg_time_spent=float(row["avg_time_spent"]),
            assignment_submission_rate=float(row["assignment_submission_rate"]),
            missed_assignments=int(row["missed_assignments"]),
        )
        student.financial = Financial(
            fee_due=0 if _row_value(row, "fees_paid_status", default="Not Paid") == "Paid" else float(_row_value(row, "fee_due", default=10000)),
            payment_delay_days=0 if _row_value(row, "fees_paid_status", default="Not Paid") == "Paid" else int(_row_value(row, "payment_delay_days", default=15)),
            scholarship_amount=float(_row_value(row, "scholarship_amount", default=0)),
        )
        db.add(student)
        inserted += 1
    db.commit()

    model_path = Path(__file__).resolve().parents[2] / "models" / "student_retention_model.pkl"
    scoring_summary = None
    if model_path.exists():
        scoring_summary = score_all_students(db)

    return {"status": "success", "inserted": inserted, "scoring_summary": scoring_summary}


def _risk_label(probability_map: dict[str, float]) -> tuple[str, float]:
    risk_level = max(probability_map, key=probability_map.get)
    return risk_level, probability_map[risk_level]


def _build_payload_df(payload: PredictionRequest) -> pd.DataFrame:
    row = payload.model_dump()
    row["lms_activity_status"] = derive_lms_activity_status(
        payload.weekly_logins,
        payload.avg_time_spent,
        payload.assignment_submission_rate,
        payload.missed_assignments,
    )
    row["fees_paid_status"] = derive_fees_paid_status(payload.fee_due, payload.payment_delay_days)
    return pd.DataFrame([row])[FEATURE_COLUMNS + CATEGORICAL_COLUMNS]


def _build_explanation(payload: PredictionRequest, risk_level: str, _: list[dict[str, float | str]]) -> str:
    positive_reasons: list[str] = []
    risk_reasons: list[str] = []

    if payload.gpa >= 7.0:
        positive_reasons.append("strong CGPA")
    elif payload.gpa < 6.0:
        risk_reasons.append("low CGPA")

    if payload.attendance >= 85:
        positive_reasons.append("high attendance")
    elif payload.attendance < 65:
        risk_reasons.append("very low attendance")
    elif payload.attendance < 75:
        risk_reasons.append("low attendance")
    elif payload.attendance < 85:
        risk_reasons.append("attendance below the safe threshold")

    if payload.weekly_logins >= 12 and payload.assignment_submission_rate >= 80 and payload.missed_assignments <= 2:
        positive_reasons.append("strong LMS activity")
    elif payload.weekly_logins < 7 or payload.assignment_submission_rate < 65 or payload.missed_assignments >= 4:
        risk_reasons.append("weak LMS activity")

    if payload.fee_due <= 0 and payload.payment_delay_days <= 0:
        positive_reasons.append("fees paid on time")
    elif payload.fee_due > 0 or payload.payment_delay_days > 0:
        risk_reasons.append("pending fee payment")

    if risk_level == "Safe":
        reasons = positive_reasons[:3] or ["excellent academic and engagement signals"]
        joined = ", ".join(reasons)
        return f"{joined.capitalize()} are the main reasons behind the safe retention outlook."

    if risk_level == "Low":
        reasons = positive_reasons[:3] or ["stable academic and engagement signals"]
        joined = ", ".join(reasons)
        return f"{joined.capitalize()} are the main reasons behind the low retention risk."

    reasons = risk_reasons[:3] or ["inconsistent academic and engagement signals"]
    joined = ", ".join(reasons)
    return f"{joined.capitalize()} are the main reasons behind the {risk_level.lower()} retention risk."


def _persist_prediction(
    db: Session,
    student: Student | None,
    probability: float,
    risk_level: str,
    explanation: str,
    feature_importance: list[dict[str, float | str]],
    recommendations: list[str],
) -> None:
    if not student:
        return
    record = Prediction(
        student_id=student.id,
        risk_score=probability,
        risk_level=risk_level,
        model_name="RandomForestClassifier",
        explanation=explanation,
        feature_importance=feature_importance,
        recommendations=recommendations,
    )
    db.add(record)
    db.commit()


def _feature_actual_value(payload: PredictionRequest, feature: str) -> str | float | int | None:
    cleaned = feature.replace("num__", "").replace("cat__", "")

    if cleaned == "attendance":
        return f"{payload.attendance:.1f}%"
    if cleaned == "gpa":
        return round(payload.gpa, 2)
    if cleaned == "marks":
        return round(payload.marks, 2)
    if cleaned == "weekly_logins":
        return payload.weekly_logins
    if cleaned == "avg_time_spent":
        return round(payload.avg_time_spent, 2)
    if cleaned == "assignment_submission_rate":
        return f"{payload.assignment_submission_rate:.1f}%"
    if cleaned == "missed_assignments":
        return payload.missed_assignments
    if cleaned == "fee_due":
        return round(payload.fee_due, 2)
    if cleaned == "payment_delay_days":
        return payload.payment_delay_days
    if cleaned == "scholarship_amount":
        return round(payload.scholarship_amount, 2)
    if cleaned == "department":
        return payload.department
    if cleaned == "year":
        return payload.year
    if cleaned == "career_interest":
        return payload.career_interest
    if cleaned == "skills":
        return payload.skills
    if cleaned.startswith("fees_paid_status"):
        return "Paid" if payload.fee_due <= 0 and payload.payment_delay_days <= 0 else "Not Paid"
    if cleaned.startswith("lms_activity_status"):
        return derive_lms_activity_status(
            payload.weekly_logins,
            payload.avg_time_spent,
            payload.assignment_submission_rate,
            payload.missed_assignments,
        )
    return None


def _enrich_feature_importance_with_values(
    payload: PredictionRequest,
    feature_importance: list[dict[str, float | str]],
) -> list[dict[str, float | str | int | None]]:
    enriched: list[dict[str, float | str | int | None]] = []
    for item in feature_importance:
        feature = str(item.get("feature", ""))
        enriched.append(
            {
                **item,
                "actual_value": _feature_actual_value(payload, feature),
            }
        )
    return enriched


def _upgrade_low_to_safe(payload: PredictionRequest, risk_level: str, probability: float) -> tuple[str, float]:
    if risk_level != "Low":
        return risk_level, probability
    if (
        payload.attendance >= 80
        and payload.gpa >= 8.0
        and payload.assignment_submission_rate >= 80
        and payload.fee_due <= 0
        and payload.payment_delay_days <= 0
    ):
        return "Safe", 0.15
    return "Low", 0.35


def _build_prediction_payload_from_student(student: Student) -> PredictionRequest:
    return PredictionRequest(
        student_id=student.id,
        gpa=student.gpa,
        attendance=student.attendance,
        marks=student.marks,
        weekly_logins=student.lms_activity.weekly_logins,
        avg_time_spent=student.lms_activity.avg_time_spent,
        assignment_submission_rate=student.lms_activity.assignment_submission_rate,
        missed_assignments=student.lms_activity.missed_assignments,
        fee_due=student.financial.fee_due,
        payment_delay_days=student.financial.payment_delay_days,
        scholarship_amount=student.financial.scholarship_amount,
    )


def predict_and_store(db: Session, payload: PredictionRequest, current_user: User) -> PredictionResponse:
    return _predict_and_store(db, payload, current_user, send_email=True)


def _predict_and_store(db: Session, payload: PredictionRequest, current_user: User, send_email: bool) -> PredictionResponse:
    model_path = Path(__file__).resolve().parents[2] / "models" / "student_retention_model.pkl"
    if not model_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model artifacts are missing. Run /train-model first.",
        )

    artifacts = load_artifacts()
    model = artifacts["model"]
    comparison_model = artifacts["comparison_model"]
    label_encoder = artifacts["label_encoder"]
    feature_names = artifacts["feature_names"]

    payload_df = _build_payload_df(payload)
    probabilities = model.predict_proba(payload_df)[0]
    probability_map = {
        label_encoder.inverse_transform([index])[0]: float(score)
        for index, score in enumerate(probabilities)
    }
    risk_level, probability = _risk_label(probability_map)
    risk_level, probability = _upgrade_low_to_safe(payload, risk_level, probability)

    comparison_probabilities = comparison_model.predict_proba(payload_df)[0]
    comparison_probability = max(float(score) for score in comparison_probabilities)

    feature_importance = build_shap_explanation(model, feature_names, payload_df)
    feature_importance = _enrich_feature_importance_with_values(payload, feature_importance)
    explanation = _build_explanation(payload, risk_level, feature_importance)

    student = get_student(db, payload.student_id, current_user) if payload.student_id else None
    risk_level, probability = _apply_subject_attendance_guard(risk_level, probability, student)
    recommendations_obj = build_recommendations(student) if student else None
    recommendations = (
        recommendations_obj.academic + recommendations_obj.career[:1] + recommendations_obj.learning_pathways[:1]
        if recommendations_obj
        else [
            "Increase attendance consistency and LMS engagement over the next four weeks.",
            "Resolve overdue fee payments and connect with faculty for an academic review.",
        ]
    )

    _persist_prediction(db, student, probability, risk_level, explanation, feature_importance, recommendations)

    if send_email and student and risk_level in {"Medium", "High"}:
        import asyncio

        try:
            asyncio.run(send_risk_alert_email(student.name, student.email, risk_level, explanation, recommendations))
        except Exception:
            pass

    return PredictionResponse(
        risk_level=risk_level,
        probability=round(probability, 4),
        feature_importance=feature_importance,
        explanation=explanation,
        recommendations=recommendations,
        comparison_model_probability=round(comparison_probability, 4),
    )


def score_all_students(db: Session) -> dict[str, int]:
    admin_user = User(id=0, name="System Admin", email="system@local", password="", role="admin")
    students = (
        db.query(Student)
        .options(joinedload(Student.lms_activity), joinedload(Student.financial), joinedload(Student.subject_attendance))
        .all()
    )
    scored = 0
    for student in students:
        if not student.lms_activity or not student.financial:
            continue
        _predict_and_store(db, _build_prediction_payload_from_student(student), admin_user, send_email=False)
        scored += 1
    return {"scored_students": scored}


def get_prediction_history(db: Session, student_id: int, current_user: User) -> list[Prediction]:
    get_student(db, student_id, current_user)
    return (
        db.query(Prediction)
        .filter(Prediction.student_id == student_id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
