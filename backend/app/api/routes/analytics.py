from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_admin, require_admin_or_faculty
from app.db.session import get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.analytics import AnalyticsResponse, FacultyPerformanceResponse
from app.schemas.prediction import AlertHistoryResponse, PredictionRequest, PredictionResponse, SendAlertEmailRequest
from app.services.alert_history_service import list_alert_history, record_alert_history
from app.services.email_service import send_risk_alert_email
from app.services.analytics_service import build_analytics, build_faculty_performance
from app.services.report_service import generate_pdf_report
from app.services.student_service import predict_and_store

router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return build_analytics(db, current_user)


@router.get("/analytics/faculty-performance", response_model=FacultyPerformanceResponse)
def faculty_performance(db: Session = Depends(get_db), _: object = Depends(require_admin)):
    return build_faculty_performance(db)


@router.post("/predict-risk", response_model=PredictionResponse)
def predict(payload: PredictionRequest, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return predict_and_store(db, payload, current_user)


@router.post("/send-alert-email")
async def send_alert_email(
    payload: SendAlertEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        weak_subject_attendance: list[tuple[str, float]] = []
        if payload.student_id is not None:
            student = (
                db.query(Student)
                .options(joinedload(Student.subject_attendance))
                .filter(Student.id == payload.student_id)
                .first()
            )
            if student:
                weak_subject_attendance = [
                    (item.subject_name, item.attendance_percentage)
                    for item in student.subject_attendance
                    if item.attendance_percentage < 75
                ]
                if payload.risk_level not in {"High", "Medium"}:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Alert not sent for {payload.student_name}. "
                            "Emails are only sent for students with High or Medium risk."
                        ),
                    )

        result = await send_risk_alert_email(
            payload.student_name,
            payload.student_email,
            payload.risk_level,
            payload.explanation,
            payload.recommendations,
            weak_subject_attendance=weak_subject_attendance,
        )
        record_alert_history(
            db,
            student_id=payload.student_id,
            sent_by=current_user.name or current_user.email,
            recipient_name=payload.student_name,
            recipient_email=payload.student_email,
            risk_level=payload.risk_level,
            status=result.get("status", "sent"),
            error_message="",
        )
        return result
    except Exception as exc:
        record_alert_history(
            db,
            student_id=payload.student_id,
            sent_by=current_user.name or current_user.email,
            recipient_name=payload.student_name,
            recipient_email=payload.student_email,
            risk_level=payload.risk_level,
            status="failed",
            error_message=str(exc),
        )
        raise


@router.get("/alerts/history", response_model=list[AlertHistoryResponse])
def get_alert_history(db: Session = Depends(get_db), _: object = Depends(require_admin)):
    return list_alert_history(db)


@router.get("/analytics/report")
def download_report(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    report_buffer = generate_pdf_report(build_analytics(db, current_user))
    return StreamingResponse(
        report_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=student-retention-report.pdf"},
    )
