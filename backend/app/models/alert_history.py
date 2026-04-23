from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    sent_by = Column(String(120), nullable=False)
    recipient_name = Column(String(120), nullable=False)
    recipient_email = Column(String(120), nullable=False, index=True)
    risk_level = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="sent")
    error_message = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student = relationship("Student", back_populates="alert_history")
