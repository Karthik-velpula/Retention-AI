from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.intervention import Intervention
from app.models.intervention_history import InterventionHistory
from app.models.student import Student
from app.models.user import User
from app.schemas.intervention import (
    InterventionAssistRequest,
    InterventionAssistResponse,
    InterventionHistoryResponse,
    InterventionResponse,
    InterventionSaveResponse,
    InterventionStudentOverview,
    InterventionUpsert,
)
from app.services.email_service import send_follow_up_email, send_resolution_email
from app.services.student_service import _filtered_students_query, _heuristic_overview_risk

IST = ZoneInfo("Asia/Kolkata")


def _risk_factors(student: Student) -> list[str]:
    factors: list[str] = []
    if student.attendance < 65:
        factors.append("attendance is below 65%")
    elif student.attendance < 75:
        factors.append("attendance is below 75%")
    elif student.attendance < 85:
        factors.append("attendance is below 85%")

    if student.gpa < 6:
        factors.append("CGPA is below 6.0")
    elif student.gpa < 7:
        factors.append("CGPA needs improvement")

    if student.lms_activity:
        if student.lms_activity.assignment_submission_rate < 70:
            factors.append("LMS submission rate is weak")
        if student.lms_activity.missed_assignments >= 3:
            factors.append("multiple LMS assignments are pending")

    if student.financial and student.financial.fee_due > 0:
        factors.append("fee payment is pending")

    return factors


def _recommended_follow_up_date(risk_level: str, attendance: float) -> date:
    today = datetime.now(IST).date()
    if risk_level == "High":
        delta_days = 2 if attendance < 65 else 3
    elif risk_level == "Medium":
        delta_days = 5 if attendance < 75 else 7
    else:
        delta_days = 10
    return today + timedelta(days=delta_days)


def build_intervention_assist(
    db: Session,
    current_user: User,
    student_id: int,
    payload: InterventionAssistRequest,
) -> InterventionAssistResponse:
    student = (
        _filtered_students_query(db, current_user)
        .options(
            joinedload(Student.predictions),
            joinedload(Student.lms_activity),
            joinedload(Student.financial),
            selectinload(Student.subject_attendance),
        )
        .filter(Student.id == student_id)
        .first()
    )
    if not student:
        raise ValueError("Student not found or not assigned")

    latest_prediction = max(student.predictions, key=lambda item: item.created_at) if student.predictions else None
    fallback_risk_level, _ = _heuristic_overview_risk(student)
    risk_level = latest_prediction.risk_level if latest_prediction else fallback_risk_level

    factors = _risk_factors(student)
    if not factors:
        factors = ["current risk indicators require continued monitoring"]

    recommended_follow_up_date = None if payload.status == "resolved" else _recommended_follow_up_date(risk_level, student.attendance)
    suggest_parent_informed = risk_level == "High" or student.attendance < 65 or payload.fee_issue_escalated

    if suggest_parent_informed:
        parent_informed_reason = (
            "Parent communication is recommended because the student has a high-priority academic or attendance concern."
        )
    else:
        parent_informed_reason = "Parent communication is optional for now; direct student follow-up should be sufficient."

    actions: list[str] = []
    if payload.contacted_student:
        actions.append("student was contacted")
    if payload.parent_informed:
        actions.append("parent was informed")
    if current_user.role == "admin" and payload.counselor_assigned:
        actions.append("counselor support was assigned")
    if payload.fee_issue_escalated:
        actions.append("fee issue was escalated")

    action_sentence = (
        f"Immediate action recorded: {', '.join(actions)}."
        if actions
        else "Immediate action should begin with a student meeting and progress review."
    )
    factor_sentence = ", ".join(factors[:3])
    status_sentence = {
        "pending": "The case is pending intervention.",
        "in_progress": "The case is currently under active intervention.",
        "resolved": "The case has been marked resolved.",
    }[payload.status]

    suggested_note = (
        f"{risk_level} risk case for {student.name}. Key concerns: {factor_sentence}. "
        f"{action_sentence} {status_sentence}"
        + (
            f" Recommended next follow-up date: {recommended_follow_up_date.strftime('%d %b %Y')}."
            if recommended_follow_up_date
            else ""
        )
    ).strip()

    return InterventionAssistResponse(
        suggested_note=suggested_note,
        recommended_follow_up_date=recommended_follow_up_date,
        suggest_parent_informed=suggest_parent_informed,
        parent_informed_reason=parent_informed_reason,
    )


def list_interventions(db: Session, current_user: User) -> list[InterventionStudentOverview]:
    students = (
        _filtered_students_query(db, current_user)
        .options(
            selectinload(Student.lms_activity),
            selectinload(Student.financial),
            selectinload(Student.subject_attendance),
            selectinload(Student.intervention).selectinload(Intervention.history),
        )
        .order_by(Student.registration_number.asc())
        .all()
    )
    result: list[InterventionStudentOverview] = []
    for student in students:
        resolved_risk_level, resolved_risk_score = _heuristic_overview_risk(student)
        if resolved_risk_level not in {"Medium", "High"}:
            continue
        result.append(
            InterventionStudentOverview(
                student_id=student.id,
                registration_number=student.registration_number,
                student_name=student.name,
                student_email=student.email,
                counselor_name=student.counselor_name,
                attendance=student.attendance,
                latest_risk_level=resolved_risk_level,
                latest_risk_score=resolved_risk_score,
                intervention=InterventionResponse.model_validate(student.intervention) if student.intervention else None,
                history=[
                    InterventionHistoryResponse.model_validate(item)
                    for item in sorted(student.intervention.history, key=lambda entry: entry.created_at, reverse=True)
                ]
                if student.intervention
                else [],
            )
        )
    return result


def _summarize_changes(previous: dict[str, object], payload: InterventionUpsert, role: str | None) -> tuple[str, str]:
    changes: list[str] = []

    def add_change(label: str, old: object, new: object):
        if old != new:
            changes.append(f"{label}: {old if old not in (None, '') else 'empty'} -> {new if new not in (None, '') else 'empty'}")

    add_change("contacted student", previous["contacted_student"], payload.contacted_student)
    add_change("parent informed", previous["parent_informed"], payload.parent_informed)
    if role == "admin":
        add_change("counselor assigned", previous["counselor_assigned"], payload.counselor_assigned)
    add_change("fee issue escalated", previous["fee_issue_escalated"], payload.fee_issue_escalated)
    add_change("next follow-up date", previous["next_follow_up_date"], payload.next_follow_up_date.isoformat() if payload.next_follow_up_date else None)
    add_change("follow-up outcome", previous["follow_up_outcome"], payload.follow_up_outcome)
    add_change("status", previous["status"], payload.status)
    add_change("notes", previous["notes"], payload.notes.strip())

    if not changes:
        return ("no changes", "Record saved without field changes.")
    return (", ".join(item.split(":")[0] for item in changes), "; ".join(changes))


def upsert_intervention(db: Session, current_user: User, student_id: int, payload: InterventionUpsert) -> InterventionSaveResponse:
    student = (
        _filtered_students_query(db, current_user)
        .options(
            joinedload(Student.intervention),
            joinedload(Student.predictions),
            joinedload(Student.lms_activity),
            joinedload(Student.financial),
            selectinload(Student.subject_attendance),
        )
        .filter(Student.id == student_id)
        .first()
    )
    if not student:
        raise ValueError("Student not found or not assigned")

    intervention = student.intervention
    if not intervention:
        intervention = Intervention(student_id=student.id)
        db.add(intervention)

    previous = {
        "contacted_student": intervention.contacted_student,
        "parent_informed": intervention.parent_informed,
        "counselor_assigned": intervention.counselor_assigned,
        "fee_issue_escalated": intervention.fee_issue_escalated,
        "next_follow_up_date": intervention.next_follow_up_date.isoformat() if intervention.next_follow_up_date else None,
        "follow_up_outcome": intervention.follow_up_outcome,
        "status": intervention.status,
        "notes": intervention.notes,
    }

    intervention.contacted_student = payload.contacted_student
    intervention.parent_informed = payload.parent_informed
    intervention.counselor_assigned = payload.counselor_assigned
    intervention.fee_issue_escalated = payload.fee_issue_escalated
    intervention.next_follow_up_date = payload.next_follow_up_date
    intervention.follow_up_outcome = payload.follow_up_outcome
    if payload.status == "resolved":
        intervention.resolved_at = intervention.resolved_at or datetime.now(IST).replace(tzinfo=None)
    else:
        intervention.resolved_at = None
    intervention.status = payload.status
    intervention.notes = payload.notes.strip()
    intervention.updated_by = current_user.name

    changed_fields, change_summary = _summarize_changes(previous, payload, current_user.role)

    db.commit()
    db.refresh(intervention)

    history_entry = InterventionHistory(
        intervention_id=intervention.id,
        student_id=student.id,
        changed_by=current_user.name,
        changed_fields=changed_fields,
        change_summary=change_summary,
        created_at=datetime.now(IST).replace(tzinfo=None),
    )
    db.add(history_entry)
    db.commit()
    db.refresh(intervention)
    db.refresh(history_entry)

    email_status = "skipped"
    email_detail = "No follow-up date set, so no email was sent."
    if intervention.status == "resolved" or intervention.next_follow_up_date:
        try:
            latest_prediction = max(student.predictions, key=lambda item: item.created_at) if student.predictions else None
            fallback_risk_level, _ = _heuristic_overview_risk(student)
            risk_level = latest_prediction.risk_level if latest_prediction else fallback_risk_level
            if intervention.status == "resolved":
                email_result = asyncio.run(
                    send_resolution_email(
                        student.name,
                        student.email,
                        risk_level,
                        intervention.notes,
                    )
                )
            else:
                email_result = asyncio.run(
                    send_follow_up_email(
                        student.name,
                        student.email,
                        risk_level,
                        intervention.next_follow_up_date.isoformat(),
                        intervention.status,
                        intervention.notes,
                    )
                )
            email_status = email_result["status"]
            email_detail = email_result["detail"]
        except Exception as exc:
            email_status = "failed"
            email_detail = f"Follow-up saved, but email failed: {exc}"
    elif intervention.status != "resolved":
        email_detail = "No follow-up date set, so no email was sent."

    return InterventionSaveResponse(
        intervention=InterventionResponse.model_validate(intervention),
        history_entry=InterventionHistoryResponse.model_validate(history_entry),
        email_status=email_status,
        email_detail=email_detail,
    )
