from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.alert_history import AlertHistory
from app.schemas.prediction import AlertHistoryResponse

IST = ZoneInfo("Asia/Kolkata")


def record_alert_history(
    db: Session,
    *,
    student_id: int | None,
    sent_by: str,
    recipient_name: str,
    recipient_email: str,
    risk_level: str,
    status: str,
    error_message: str = "",
) -> AlertHistory:
    entry = AlertHistory(
        student_id=student_id,
        sent_by=sent_by,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        risk_level=risk_level,
        status=status,
        error_message=error_message,
        created_at=datetime.now(IST).replace(tzinfo=None),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_alert_history(db: Session, limit: int = 100) -> list[AlertHistoryResponse]:
    entries = (
        db.query(AlertHistory)
        .order_by(AlertHistory.created_at.desc(), AlertHistory.id.desc())
        .limit(limit)
        .all()
    )
    return [AlertHistoryResponse.model_validate(item) for item in entries]
