from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(sub=payload.get("sub"), token_type=payload.get("token_type"))
    except JWTError as exc:
        raise credentials_exception from exc

    if token_data.sub is None or token_data.token_type != "access":
        raise credentials_exception

    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if not user:
        raise credentials_exception
    return user


def require_admin_or_faculty(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "faculty"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
