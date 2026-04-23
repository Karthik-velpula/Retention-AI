from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_faculty
from app.db.session import get_db
from app.models.user import User
from app.schemas.intervention import (
    InterventionAssistRequest,
    InterventionAssistResponse,
    InterventionSaveResponse,
    InterventionStudentOverview,
    InterventionUpsert,
)
from app.services.intervention_service import build_intervention_assist, list_interventions, upsert_intervention
from app.services.report_service import generate_intervention_history_report

router = APIRouter()


@router.get("/interventions", response_model=list[InterventionStudentOverview])
def get_interventions(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return list_interventions(db, current_user)


@router.get("/interventions/report/pdf")
def download_intervention_history_pdf(
    counselor_name: str = Query(...),
    student_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty),
):
    records = [item for item in list_interventions(db, current_user) if item.counselor_name == counselor_name]
    if student_id is not None:
        records = [item for item in records if item.student_id == student_id]

    records_with_history = [item for item in records if item.history]
    student_name = records_with_history[0].student_name if len(records_with_history) == 1 else None
    report_buffer = generate_intervention_history_report(records_with_history, counselor_name, student_name)
    safe_name = counselor_name.lower().replace(" ", "-").replace(".", "")
    filename = f"{safe_name}-intervention-history.pdf"
    if student_name:
        student_slug = student_name.lower().replace(" ", "-").replace(".", "")
        filename = f"{safe_name}-{student_slug}-intervention-history.pdf"

    return StreamingResponse(
        report_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/interventions/{student_id}/ai-assist", response_model=InterventionAssistResponse)
def get_intervention_assist(
    student_id: int,
    payload: InterventionAssistRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty),
):
    try:
        return build_intervention_assist(db, current_user, student_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/interventions/{student_id}", response_model=InterventionSaveResponse)
def save_intervention(
    student_id: int,
    payload: InterventionUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty),
):
    try:
        return upsert_intervention(db, current_user, student_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
