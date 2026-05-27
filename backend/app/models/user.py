from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(40), unique=True, index=True, nullable=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="faculty")
    security_grid = Column(String(1000), nullable=False, default="{}")
    last_login_at = Column(DateTime, nullable=True)
    token_version = Column(Integer, nullable=False, default=0)

    password_reset_otps = relationship("PasswordResetOTP", back_populates="user", cascade="all, delete-orphan")
