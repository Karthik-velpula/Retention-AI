from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    contacted_student = Column(Boolean, nullable=False, default=False)
    parent_informed = Column(Boolean, nullable=False, default=False)
    counselor_assigned = Column(Boolean, nullable=False, default=False)
    fee_issue_escalated = Column(Boolean, nullable=False, default=False)
    next_follow_up_date = Column(Date, nullable=True)
    follow_up_outcome = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String(500), nullable=False, default="")
    updated_by = Column(String(120), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    student = relationship("Student", back_populates="intervention")
    history = relationship("InterventionHistory", back_populates="intervention", cascade="all, delete-orphan")
