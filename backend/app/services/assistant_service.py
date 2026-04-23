from __future__ import annotations

import re

from sqlalchemy import cast, func, or_, String
from sqlalchemy.orm import Session, joinedload

from app.models.financial import Financial
from app.models.student import Student
from app.models.user import User
from app.services.student_service import _filtered_students_query, _heuristic_overview_risk


REGISTRATION_PATTERN = re.compile(r"\b\d{2,3}\s*[a-z]{2}\s*\d{4,6}\b", re.IGNORECASE)


def _base_query(db: Session, current_user: User):
    return _filtered_students_query(db, current_user).outerjoin(Student.lms_activity).outerjoin(Student.financial)


def _section_match(query_text: str) -> str | None:
    match = re.search(r"section\s+(\d+)", query_text, re.IGNORECASE)
    return match.group(1) if match else None


def _year_match(query_text: str) -> int | None:
    match = re.search(r"(\d+)(?:st|nd|rd|th)?\s+year", query_text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _find_student_by_registration(db: Session, current_user: User, registration_number: str) -> Student | None:
    normalized_registration = re.sub(r"\s+", "", registration_number)
    return (
        _filtered_students_query(db, current_user)
        .options(joinedload(Student.lms_activity), joinedload(Student.financial), joinedload(Student.subject_attendance))
        .filter(func.lower(Student.registration_number) == normalized_registration.lower())
        .first()
    )


def _student_summary(student: Student, query_text: str) -> str:
    risk_level, _ = _heuristic_overview_risk(student)
    if "name" in query_text or "who is" in query_text:
        return f"{student.registration_number} belongs to {student.name}."

    unpaid = "paid" if not student.financial or (student.financial.fee_due <= 0 and student.financial.payment_delay_days <= 0) else "not paid"
    return (
        f"{student.name}, registration number {student.registration_number}, is in section {student.section}. "
        f"Current risk is {risk_level}, attendance is {student.attendance:.0f} percent, marks are {student.marks:.2f}, "
        f"LMS activity is {student.lms_activity.assignment_submission_rate:.0f} percent, and fees status is {unpaid}."
        if student.lms_activity
        else f"{student.name}, registration number {student.registration_number}, is in section {student.section}. "
        f"Current risk is {risk_level}, attendance is {student.attendance:.0f} percent, marks are {student.marks:.2f}, and fees status is {unpaid}."
    )


def _apply_common_filters(query, query_text: str):
    section = _section_match(query_text)
    if section:
        query = query.filter(Student.section == section)
    year = _year_match(query_text)
    if year is not None:
        query = query.filter(Student.year == year)
    return query, section, year


def _scope_text(section: str | None, year: int | None) -> str:
    scope_parts = []
    if year is not None:
        scope_parts.append(f"{year} year")
    if section:
        scope_parts.append(f"section {section}")
    return f" in {' '.join(scope_parts)}" if scope_parts else ""


def _risk_count(query, level: str) -> int:
    students = query.options(joinedload(Student.lms_activity), joinedload(Student.financial)).all()
    return sum(1 for student in students if _heuristic_overview_risk(student)[0] == level)


def answer_query(db: Session, current_user: User, query_text: str) -> str:
    cleaned = query_text.strip()
    normalized = cleaned.lower()
    registration_match = REGISTRATION_PATTERN.search(cleaned)
    if registration_match:
        normalized_registration = re.sub(r"\s+", "", registration_match.group(0))
        student = _find_student_by_registration(db, current_user, normalized_registration)
        if not student:
            return f"I could not find a student for {normalized_registration}."
        return _student_summary(student, normalized)

    query = _base_query(db, current_user)
    query, section, year = _apply_common_filters(query, normalized)
    scope = _scope_text(section, year)

    if "high risk" in normalized:
        return f"{_risk_count(query, 'High')} students are high risk{scope}."
    if "medium risk" in normalized:
        return f"{_risk_count(query, 'Medium')} students are medium risk{scope}."
    if "low risk" in normalized:
        return f"{_risk_count(query, 'Low')} students are low risk{scope}."

    if ("below 65" in normalized or "less than 65" in normalized) and "attendance" in normalized:
        count = query.filter(Student.attendance < 65).with_entities(func.count(Student.id)).scalar() or 0
        return f"{count} students have attendance below 65 percent{scope}."
    if ("below 75" in normalized or "less than 75" in normalized) and "attendance" in normalized:
        count = query.filter(Student.attendance < 75).with_entities(func.count(Student.id)).scalar() or 0
        return f"{count} students have attendance below 75 percent{scope}."
    if ("below 85" in normalized or "less than 85" in normalized) and "attendance" in normalized:
        count = query.filter(Student.attendance < 85).with_entities(func.count(Student.id)).scalar() or 0
        return f"{count} students have attendance below 85 percent{scope}."

    if "attendance" in normalized and ("average" in normalized or "avg" in normalized or "mean" in normalized):
        average = query.with_entities(func.avg(Student.attendance)).scalar() or 0
        return f"Average attendance is {average:.2f} percent{scope}."
    if "marks" in normalized and ("average" in normalized or "avg" in normalized or "mean" in normalized):
        average = query.with_entities(func.avg(Student.marks)).scalar() or 0
        return f"Average marks are {average:.2f}{scope}."
    if ("lms" in normalized or "activity" in normalized) and ("average" in normalized or "avg" in normalized or "mean" in normalized):
        students = query.options(joinedload(Student.lms_activity)).all()
        values = [student.lms_activity.assignment_submission_rate for student in students if student.lms_activity]
        average_value = (sum(values) / len(values)) if values else 0
        return f"Average LMS activity is {average_value:.2f} percent{scope}."

    if ("fee" in normalized or "fees" in normalized) and (
        "not paid" in normalized or "unpaid" in normalized or "unpaired" in normalized or "due" in normalized or "pending" in normalized
    ):
        count = (
            query.filter(
                Financial.id.is_not(None),
                or_(Financial.fee_due > 0, Financial.payment_delay_days > 0),
            )
            .with_entities(func.count(Student.id))
            .scalar()
            or 0
        )
        return f"{count} students have unpaid or due fees{scope}."
    if ("fee" in normalized or "fees" in normalized) and ("paid" in normalized or "cleared" in normalized):
        count = (
            query.filter(
                or_(Financial.id.is_(None), (Financial.fee_due <= 0) & (Financial.payment_delay_days <= 0))
            )
            .with_entities(func.count(Student.id))
            .scalar()
            or 0
        )
        return f"{count} students have paid fees{scope}."

    if "how many students" in normalized or normalized.startswith("students in ") or normalized.startswith("student count"):
        count = query.with_entities(func.count(Student.id)).scalar() or 0
        return f"{count} students are available{scope}."

    if (
        "topper" in normalized
        or "highest marks" in normalized
        or ("highest" in normalized and "mark" in normalized)
        or ("top" in normalized and "mark" in normalized)
        or ("best" in normalized and "mark" in normalized)
    ):
        topper = query.order_by(Student.marks.desc(), Student.registration_number.asc()).first()
        if topper:
            return f"{topper.name} has the highest marks{scope} with {topper.marks:.2f}."

    if "lowest attendance" in normalized:
        student = query.order_by(Student.attendance.asc(), Student.registration_number.asc()).first()
        if student:
            return f"{student.name} has the lowest attendance{scope} with {student.attendance:.2f} percent."

    if "lowest marks" in normalized:
        student = query.order_by(Student.marks.asc(), Student.registration_number.asc()).first()
        if student:
            return f"{student.name} has the lowest marks{scope} with {student.marks:.2f}."

    if "attendance" in normalized:
        if "highest" in normalized or "top" in normalized or "best" in normalized:
            student = query.order_by(Student.attendance.desc(), Student.registration_number.asc()).first()
            if student:
                return f"{student.name} has the highest attendance{scope} with {student.attendance:.2f} percent."
        count = query.with_entities(func.count(Student.id)).scalar() or 0
        average = query.with_entities(func.avg(Student.attendance)).scalar() or 0
        return f"{count} students are available{scope}. Average attendance is {average:.2f} percent."

    if "marks" in normalized:
        if "highest" in normalized or "top" in normalized or "best" in normalized:
            student = query.order_by(Student.marks.desc(), Student.registration_number.asc()).first()
            if student:
                return f"{student.name} has the highest marks{scope} with {student.marks:.2f}."
        count = query.with_entities(func.count(Student.id)).scalar() or 0
        average = query.with_entities(func.avg(Student.marks)).scalar() or 0
        return f"{count} students are available{scope}. Average marks are {average:.2f}."

    if "lms" in normalized or "activity" in normalized:
        students = query.options(joinedload(Student.lms_activity)).all()
        values = [student.lms_activity.assignment_submission_rate for student in students if student.lms_activity]
        average_value = (sum(values) / len(values)) if values else 0
        return f"{len(students)} students are available{scope}. Average LMS activity is {average_value:.2f} percent."

    if "risk" in normalized:
        high = _risk_count(query, "High")
        medium = _risk_count(query, "Medium")
        low = _risk_count(query, "Low")
        return f"Risk summary{scope}: {high} high, {medium} medium, and {low} low."

    if "student" in normalized or section or year is not None:
        count = query.with_entities(func.count(Student.id)).scalar() or 0
        return f"{count} students are available{scope}."

    if cleaned:
        normalized_query = f"%{cleaned.lower()}%"
        student = (
            _filtered_students_query(db, current_user)
            .options(joinedload(Student.lms_activity), joinedload(Student.financial))
            .filter(
                or_(
                    func.lower(Student.name).like(normalized_query),
                    func.lower(Student.registration_number).like(normalized_query),
                    func.lower(Student.counselor_name).like(normalized_query),
                    func.lower(Student.section).like(normalized_query),
                    cast(Student.year, String).like(normalized_query),
                )
            )
            .order_by(Student.registration_number.asc())
            .first()
        )
        if student:
            return _student_summary(student, normalized)
        similar_students = (
            _filtered_students_query(db, current_user)
            .filter(
                or_(
                    func.lower(Student.name).like(normalized_query),
                    func.lower(Student.registration_number).like(normalized_query),
                    func.lower(Student.counselor_name).like(normalized_query),
                )
            )
            .order_by(Student.registration_number.asc())
            .limit(3)
            .all()
        )
        if similar_students:
            names = ", ".join(student.name for student in similar_students)
            return f"I found matching students: {names}."

    total = query.with_entities(func.count(Student.id)).scalar() or 0
    if total:
        return f"{total} students are available{scope}. Ask about risk, attendance, marks, LMS, fees, section, year, or a registration number."
    return "No student data is available for that request."
