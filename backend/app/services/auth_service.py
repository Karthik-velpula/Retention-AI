import json
from datetime import datetime, timedelta
import secrets

from sqlalchemy import func, or_

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.faculty_assignments import TEST_FACULTY_EMAIL
from app.core.security import (
    create_access_token,
    create_grid_challenge_token,
    create_one_time_token,
    generate_security_grid,
    get_password_hash,
    verify_password,
)
from app.models.password_reset_otp import PasswordResetOTP
from app.models.user import User
from app.schemas.auth import (
    GridChallengeResponse,
    GridLoginCompleteRequest,
    GridLoginVerifyRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    SecurityGridResetConfirm,
    SecurityGridResetConfirmResponse,
    SecurityGridResetRequest,
    SecurityGridPreviewResponse,
    TokenPayload,
    TokenResponse,
)
from app.services.email_service import send_password_reset_otp_email, send_security_grid_reset_otp_email

PASSWORD_RESET_PURPOSE = "password_reset"
GRID_RESET_PURPOSE = "security_grid_reset"
GRID_DOWNLOAD_PURPOSE = "security_grid_download"
FORGOT_PASSWORD_OTP_EMAIL = "231fa04509@gmail.com"


def _find_user(identifier: str, db: Session) -> User | None:
    normalized = identifier.strip().lower()
    raw = identifier.strip()
    return (
        db.query(User)
        .filter(
            or_(
                func.lower(User.email) == normalized,
                func.lower(User.username) == normalized,
                User.name == raw,
            )
        )
        .first()
    )


def _login_success_response(user: User, db: Session) -> TokenResponse:
    previous_login_at = user.last_login_at
    user.last_login_at = datetime.utcnow()
    db.commit()
    access_token = create_access_token(user.id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    display_name = "" if user.email == TEST_FACULTY_EMAIL else user.name
    return TokenResponse(access_token=access_token, role=user.role, name=display_name, last_login_at=previous_login_at)


def _build_grid_challenge(user: User) -> GridChallengeResponse:
    positions = sorted(secrets.SystemRandom().sample(list(json.loads(user.security_grid).keys()), 2))
    challenge_token = create_grid_challenge_token(user.id, positions, timedelta(minutes=5))
    return GridChallengeResponse(challenge_token=challenge_token, positions=positions)


def create_login_grid_challenge(username: str, db: Session) -> GridChallengeResponse:
    user = _find_user(username, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _build_grid_challenge(user)


def login_user(payload: LoginRequest, db: Session) -> TokenResponse:
    user = _find_user(payload.username, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login ID is wrong")
    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password is wrong")
    return _login_success_response(user, db)


def get_security_grid_preview(username: str, db: Session) -> SecurityGridPreviewResponse:
    user = _find_user(username, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return SecurityGridPreviewResponse(username=user.email, grid=json.loads(user.security_grid))


def verify_grid_login(payload: GridLoginVerifyRequest, db: Session) -> TokenResponse:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid security grid verification")
    try:
        token_payload = jwt.decode(payload.challenge_token, settings.SECRET_KEY, algorithms=["HS256"])
        challenge = TokenPayload(
            sub=token_payload.get("sub"),
            purpose=token_payload.get("purpose"),
            positions=token_payload.get("positions"),
        )
    except JWTError as exc:
        raise credentials_exception from exc

    if challenge.sub is None or challenge.purpose != "grid-login" or not challenge.positions or len(challenge.positions) != 2:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(challenge.sub)).first()
    if not user:
        raise credentials_exception

    security_grid = json.loads(user.security_grid)
    for position in challenge.positions:
        expected = security_grid.get(position, "").strip().upper()
        provided = payload.answers.get(position, "").strip().upper()
        if not expected or provided != expected:
            raise credentials_exception

    return _login_success_response(user, db)


def complete_grid_login(payload: GridLoginCompleteRequest, db: Session) -> TokenResponse:
    user = _find_user(payload.username, db)
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return verify_grid_login(
        GridLoginVerifyRequest(challenge_token=payload.challenge_token, answers=payload.answers),
        db,
    )


async def request_password_reset(payload: PasswordResetRequest, db: Session) -> MessageResponse:
    user = _find_user(payload.username, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user.id,
        PasswordResetOTP.purpose == PASSWORD_RESET_PURPOSE,
        PasswordResetOTP.used_at.is_(None),
    ).delete(synchronize_session=False)

    otp_code = f"{secrets.randbelow(10**6):06d}"
    otp = PasswordResetOTP(
        user_id=user.id,
        otp_code=otp_code,
        purpose=PASSWORD_RESET_PURPOSE,
        expires_at=datetime.utcnow() + timedelta(minutes=3),
    )
    db.add(otp)
    db.commit()

    await send_password_reset_otp_email(user.name, FORGOT_PASSWORD_OTP_EMAIL, otp_code)
    return MessageResponse(detail=f"OTP sent to {FORGOT_PASSWORD_OTP_EMAIL}")


def confirm_password_reset(payload: PasswordResetConfirm, db: Session) -> MessageResponse:
    user = _find_user(payload.username, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.purpose == PASSWORD_RESET_PURPOSE,
            PasswordResetOTP.otp_code == payload.otp.strip(),
            PasswordResetOTP.used_at.is_(None),
        )
        .order_by(PasswordResetOTP.created_at.desc())
        .first()
    )
    if not otp or otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    user.password = get_password_hash(payload.new_password)
    otp.used_at = datetime.utcnow()
    db.commit()
    return MessageResponse(detail="Password reset successful. You can now log in with the new password.")


async def request_security_grid_reset(payload: SecurityGridResetRequest, db: Session) -> MessageResponse:
    user = _find_user(payload.username, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user.id,
        PasswordResetOTP.purpose == GRID_RESET_PURPOSE,
        PasswordResetOTP.used_at.is_(None),
    ).delete(synchronize_session=False)

    otp_code = f"{secrets.randbelow(10**6):06d}"
    otp = PasswordResetOTP(
        user_id=user.id,
        otp_code=otp_code,
        purpose=GRID_RESET_PURPOSE,
        expires_at=datetime.utcnow() + timedelta(minutes=3),
    )
    db.add(otp)
    db.commit()

    await send_security_grid_reset_otp_email(user.name, user.email, otp_code)
    return MessageResponse(detail=f"OTP sent to {user.email}")


def confirm_security_grid_reset(payload: SecurityGridResetConfirm, db: Session) -> SecurityGridResetConfirmResponse:
    user = _find_user(payload.username, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.user_id == user.id,
            PasswordResetOTP.purpose == GRID_RESET_PURPOSE,
            PasswordResetOTP.otp_code == payload.otp.strip(),
            PasswordResetOTP.used_at.is_(None),
        )
        .order_by(PasswordResetOTP.created_at.desc())
        .first()
    )
    if not otp or otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    user.security_grid = json.dumps(generate_security_grid(f"{user.email}:{secrets.token_hex(8)}"))
    otp.used_at = datetime.utcnow()
    db.commit()
    download_token = create_one_time_token(user.id, GRID_DOWNLOAD_PURPOSE, timedelta(minutes=10))
    return SecurityGridResetConfirmResponse(
        detail="Security grid reset successful. Download your new grid now.",
        download_token=download_token,
    )


def get_security_grid_report_for_download(token: str, db: Session) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired grid download token")
    try:
        token_payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        subject = token_payload.get("sub")
        purpose = token_payload.get("purpose")
    except JWTError as exc:
        raise credentials_exception from exc

    if subject is None or purpose != GRID_DOWNLOAD_PURPOSE:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(subject)).first()
    if not user:
        raise credentials_exception
    return user
