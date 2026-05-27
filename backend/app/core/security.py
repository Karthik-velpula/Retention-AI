from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
LEGACY_SHARED_SECURITY_GRID = {
    "G1": "K7M",
    "G2": "P4X",
    "G3": "R8C",
    "G4": "T2Q",
    "G5": "V6N",
    "G6": "M3D",
    "G7": "H9L",
    "G8": "C5Z",
    "G9": "N7P",
    "G10": "Q2W",
    "G11": "L4K",
    "G12": "S8B",
    "G13": "X6R",
    "G14": "D1Y",
    "G15": "F9T",
}
GRID_LABELS = [f"G{i}" for i in range(1, 16)]
GRID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_security_grid(seed: str) -> dict[str, str]:
    values: list[str] = []
    counter = 0
    normalized_seed = seed.strip().lower()
    while len(values) < len(GRID_LABELS):
        digest = hashlib.sha256(f"{normalized_seed}:{counter}".encode("utf-8")).hexdigest()
        index = 0
        while index + 6 <= len(digest) and len(values) < len(GRID_LABELS):
            chunk = digest[index : index + 6]
            value = "".join(
                GRID_ALPHABET[int(chunk[offset : offset + 2], 16) % len(GRID_ALPHABET)]
                for offset in range(0, 6, 2)
            )
            if value not in values:
                values.append(value)
            index += 6
        counter += 1
    return dict(zip(GRID_LABELS, values, strict=False))


def is_legacy_shared_grid(raw_grid: str | None) -> bool:
    if not raw_grid:
        return True
    try:
        parsed = json.loads(raw_grid)
    except json.JSONDecodeError:
        return True
    return parsed == LEGACY_SHARED_SECURITY_GRID


def _create_token(subject: str | Any, expires_delta: timedelta | None = None, extra_claims: dict[str, Any] | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(subject: str | Any, token_version: int, expires_delta: timedelta | None = None) -> str:
    return _create_token(
        subject,
        expires_delta=expires_delta,
        extra_claims={"token_type": "access", "token_version": token_version},
    )


def create_refresh_token(subject: str | Any, token_version: int, expires_delta: timedelta | None = None) -> str:
    return _create_token(
        subject,
        expires_delta=expires_delta,
        extra_claims={"token_type": "refresh", "token_version": token_version},
    )


def create_grid_challenge_token(subject: str | Any, positions: list[str], expires_delta: timedelta | None = None) -> str:
    return _create_token(
        subject,
        expires_delta=expires_delta,
        extra_claims={"purpose": "grid-login", "positions": positions},
    )


def create_one_time_token(subject: str | Any, purpose: str, expires_delta: timedelta | None = None) -> str:
    return _create_token(subject, expires_delta=expires_delta, extra_claims={"purpose": purpose})
