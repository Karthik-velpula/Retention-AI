from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_faculty
from app.core.security import ALGORITHM
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.prediction import PredictionHistoryResponse, PredictionRequest, PredictionResponse
from app.schemas.student import StudentCreate, StudentOverview, StudentOverviewPage, StudentResponse, StudentUpdate
from app.services import student_service
from app.services.google_drive_service import upload_pdf_report_to_drive
from app.services.report_service import generate_parent_student_report

router = APIRouter()


def _latest_parent_report_buffer(student_id: int, db: Session, current_user: User):
    student = student_service.get_student(db, student_id, current_user)
    latest_prediction = max(student.predictions, key=lambda item: item.created_at) if student.predictions else None

    if latest_prediction is None:
        payload = student_service._build_prediction_payload_from_student(student)
        student_service._predict_and_store(db, payload, current_user, send_email=False)
        student = student_service.get_student(db, student_id, current_user)
        latest_prediction = max(student.predictions, key=lambda item: item.created_at)

    return student, generate_parent_student_report(student, latest_prediction)


@router.get("", response_model=list[StudentOverview])
def list_students(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return student_service.list_students(db, current_user)


@router.get("/counselors", response_model=list[str])
def list_counselors(db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return student_service.list_counselors(db, current_user)


@router.get("/paged", response_model=StudentOverviewPage)
def list_students_page(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    query: str | None = None,
    risk_level: str | None = None,
    attendance_filter: str | None = None,
    fee_status: str | None = None,
    counselor_name: str | None = None,
    section: str | None = None,
    gender: str | None = None,
    year: int | None = Query(default=None, ge=1, le=6),
    min_cgpa: float | None = Query(default=None, ge=0, le=10),
    max_cgpa: float | None = Query(default=None, ge=0, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty),
):
    return student_service.list_students_page(
        db,
        current_user,
        page=page,
        page_size=page_size,
        query=query,
        risk_level=risk_level,
        attendance_filter=attendance_filter,
        fee_status=fee_status,
        counselor_name=counselor_name,
        section=section,
        gender=gender,
        year=year,
        min_cgpa=min_cgpa,
        max_cgpa=max_cgpa,
    )


@router.post("", response_model=StudentResponse)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return student_service.create_student(db, payload, current_user)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return student_service.get_student(db, student_id, current_user)


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty),
):
    return student_service.update_student(db, student_id, payload, current_user)


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return student_service.delete_student(db, student_id, current_user)


@router.post("/upload-csv")
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: object = Depends(require_admin_or_faculty),
):
    return await student_service.upload_students_csv(db, file)


@router.post("/predict-risk", response_model=PredictionResponse)
def predict_student_risk(
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty),
):
    return student_service.predict_and_store(db, payload, current_user)


@router.get("/{student_id}/predictions", response_model=list[PredictionHistoryResponse])
def prediction_history(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return student_service.get_prediction_history(db, student_id, current_user)


@router.get("/{student_id}/parent-report")
def download_parent_report(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    student, report_buffer = _latest_parent_report_buffer(student_id, db, current_user)
    safe_name = student.name.strip().lower().replace(" ", "-") or f"student-{student.id}"
    return StreamingResponse(
        report_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-parent-report.pdf"'},
    )


@router.get("/{student_id}/parent-report-link")
def create_parent_report_link(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty),
):
    student, report_buffer = _latest_parent_report_buffer(student_id, db, current_user)
    safe_name = student.name.strip().lower().replace(" ", "-") or f"student-{student.id}"
    filename = f"{safe_name}-{student.registration_number}-parent-report.pdf"
    return {"report_url": upload_pdf_report_to_drive(report_buffer.getvalue(), filename)}


@router.get("/parent-report/{token}", name="view_parent_report")
def view_parent_report(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired report link") from exc

    if payload.get("purpose") != "parent-report":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid report link")

    student_id = int(payload.get("sub"))
    system_user = User(id=0, name="System", email="system@local", password="", role="admin")
    student, report_buffer = _latest_parent_report_buffer(student_id, db, system_user)
    safe_name = student.name.strip().lower().replace(" ", "-") or f"student-{student.id}"
    return StreamingResponse(
        report_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_name}-parent-report.pdf"'},
    )
