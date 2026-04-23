from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    otp_code = Column(String(6), nullable=False, index=True)
    purpose = Column(String(40), nullable=False, default="password_reset")
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="password_reset_otps")
