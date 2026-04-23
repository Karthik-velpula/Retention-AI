from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class InterventionHistory(Base):
    __tablename__ = "intervention_history"

    id = Column(Integer, primary_key=True, index=True)
    intervention_id = Column(Integer, ForeignKey("interventions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by = Column(String(120), nullable=False, default="")
    changed_fields = Column(String(255), nullable=False, default="")
    change_summary = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    intervention = relationship("Intervention", back_populates="history")
    student = relationship("Student")
