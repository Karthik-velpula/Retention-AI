from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class SubjectAttendance(Base):
    __tablename__ = "subject_attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_name = Column(String(120), nullable=False)
    attendance_percentage = Column(Float, nullable=False, default=0)
    pre_t1_marks = Column(Float, nullable=False, default=0)
    t1_marks = Column(Float, nullable=False, default=0)
    t2_marks = Column(Float, nullable=False, default=0)
    t3_marks = Column(Float, nullable=False, default=0)
    t4_marks = Column(Float, nullable=False, default=0)
    t5_marks = Column(Float, nullable=False, default=0)
    t5_assignment_1 = Column(Float, nullable=False, default=0)
    t5_assignment_2 = Column(Float, nullable=False, default=0)
    t5_assignment_3 = Column(Float, nullable=False, default=0)
    t5_assignment_4 = Column(Float, nullable=False, default=0)
    total_marks = Column(Float, nullable=False, default=0)

    student = relationship("Student", back_populates="subject_attendance")
