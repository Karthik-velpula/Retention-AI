from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    GridChallengeResponse,
    GridLoginCompleteRequest,
    GridLoginVerifyRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    SecurityGridResetConfirm,
    SecurityGridResetConfirmResponse,
    SecurityGridResetRequest,
    SecurityGridPreviewResponse,
    TokenResponse,
)
from app.services.auth_service import (
    complete_grid_login,
    confirm_password_reset,
    confirm_security_grid_reset,
    create_login_grid_challenge,
    get_security_grid_report_for_download,
    get_security_grid_preview,
    login_user,
    logout_user,
    refresh_login,
    request_password_reset,
    request_security_grid_reset,
    verify_grid_login,
)
from app.services.report_service import generate_security_grid_report

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return login_user(payload, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return refresh_login(payload, db)


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MessageResponse:
    return logout_user(current_user, db)


@router.get("/login/grid-challenge", response_model=GridChallengeResponse)
def login_grid_challenge(username: str, db: Session = Depends(get_db)) -> GridChallengeResponse:
    return create_login_grid_challenge(username, db)


@router.get("/security-grid-preview", response_model=SecurityGridPreviewResponse)
def security_grid_preview(username: str, db: Session = Depends(get_db)) -> SecurityGridPreviewResponse:
    return get_security_grid_preview(username, db)


@router.post("/login/verify-grid", response_model=TokenResponse)
def login_verify_grid(payload: GridLoginVerifyRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return verify_grid_login(payload, db)


@router.post("/login/complete", response_model=TokenResponse)
def login_complete(payload: GridLoginCompleteRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return complete_grid_login(payload, db)


@router.post("/forgot-password/request", response_model=MessageResponse)
async def forgot_password_request(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> MessageResponse:
    return await request_password_reset(payload, db)


@router.post("/forgot-password/confirm", response_model=MessageResponse)
def forgot_password_confirm(payload: PasswordResetConfirm, db: Session = Depends(get_db)) -> MessageResponse:
    return confirm_password_reset(payload, db)


@router.post("/security-grid-reset/request", response_model=MessageResponse)
async def security_grid_reset_request(payload: SecurityGridResetRequest, db: Session = Depends(get_db)) -> MessageResponse:
    return await request_security_grid_reset(payload, db)


@router.post("/security-grid-reset/confirm", response_model=SecurityGridResetConfirmResponse)
def security_grid_reset_confirm(payload: SecurityGridResetConfirm, db: Session = Depends(get_db)) -> SecurityGridResetConfirmResponse:
    return confirm_security_grid_reset(payload, db)


@router.get("/security-grid-reset/download")
def download_reset_security_grid(token: str, db: Session = Depends(get_db)):
    user = get_security_grid_report_for_download(token, db)
    report_buffer = generate_security_grid_report([user])
    safe_name = (user.name or "user").replace(" ", "_").lower()
    return StreamingResponse(
        report_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_name}-security-grid.pdf"},
    )


@router.get("/security-grid-report")
def download_security_grid_report(db: Session = Depends(get_db), _: object = Depends(require_admin)):
    users = db.query(User).order_by(User.role.asc(), User.name.asc(), User.email.asc()).all()
    report_buffer = generate_security_grid_report(users)
    return StreamingResponse(
        report_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=user-security-grid-report.pdf"},
    )
