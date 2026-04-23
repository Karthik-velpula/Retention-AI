from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.session import Base


class LMSActivity(Base):
    __tablename__ = "lms_activity"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, unique=True)
    weekly_logins = Column(Integer, nullable=False, default=0)
    avg_time_spent = Column(Float, nullable=False, default=0)
    assignment_submission_rate = Column(Float, nullable=False, default=0)
    missed_assignments = Column(Integer, nullable=False, default=0)

    student = relationship("Student", back_populates="lms_activity")
