from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class GridChallengeResponse(BaseModel):
    challenge_token: str
    positions: list[str]


class SecurityGridPreviewResponse(BaseModel):
    username: str
    grid: dict[str, str]


class GridLoginCompleteRequest(BaseModel):
    username: str
    password: str
    challenge_token: str
    answers: dict[str, str]


class GridLoginVerifyRequest(BaseModel):
    challenge_token: str
    answers: dict[str, str]


class PasswordResetRequest(BaseModel):
    username: str


class PasswordResetConfirm(BaseModel):
    username: str
    otp: str
    new_password: str


class SecurityGridResetRequest(BaseModel):
    username: str


class SecurityGridResetConfirm(BaseModel):
    username: str
    otp: str


class SecurityGridResetConfirmResponse(BaseModel):
    detail: str
    download_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    name: str
    last_login_at: datetime | None = None
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class TokenPayload(BaseModel):
    sub: str | None = None
    purpose: str | None = None
    positions: list[str] | None = None
    token_type: str | None = None
    token_version: int | None = None


class MessageResponse(BaseModel):
    detail: str
