from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    registration_number = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(120), index=True, nullable=False)
    student_mobile = Column(String(30), nullable=False, default="")
    parent_mobile = Column(String(30), nullable=False, default="")
    counselor_name = Column(String(120), nullable=False, default="")
    codechef_username = Column(String(100), nullable=False, default="-")
    codechef_contests_participated = Column(Integer, nullable=False, default=0)
    codechef_problems_solved = Column(Integer, nullable=False, default=0)
    codechef_participation_status = Column(String(30), nullable=False, default="Not Available")
    codechef_last_synced_at = Column(DateTime(timezone=True), nullable=True)
    section = Column(String(20), nullable=False, default="-")
    gender = Column(String(20), nullable=False, default="-")
    age = Column(Integer, nullable=True)
    gpa = Column(Float, nullable=False)
    attendance = Column(Float, nullable=False)
    marks = Column(Float, nullable=False, default=0)
    pre_t1_marks = Column(Float, nullable=False, default=0)
    t1_marks = Column(Float, nullable=False, default=0)
    t2_marks = Column(Float, nullable=False, default=0)
    t3_marks = Column(Float, nullable=False, default=0)
    t4_marks = Column(Float, nullable=False, default=0)
    t5_marks = Column(Float, nullable=False, default=0)
    department = Column(String(100), nullable=False, default="CSE")
    year = Column(Integer, nullable=False, default=1)
    career_interest = Column(String(120), nullable=False, default="Data Analysis")
    skills = Column(String(255), nullable=False, default="")

    lms_activity = relationship("LMSActivity", back_populates="student", uselist=False, cascade="all, delete-orphan")
    financial = relationship("Financial", back_populates="student", uselist=False, cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="student", cascade="all, delete-orphan")
    subject_attendance = relationship("SubjectAttendance", back_populates="student", cascade="all, delete-orphan")
    intervention = relationship("Intervention", back_populates="student", uselist=False, cascade="all, delete-orphan")
    intervention_history = relationship("InterventionHistory", cascade="all, delete-orphan", overlaps="student")
    alert_history = relationship("AlertHistory", back_populates="student")
