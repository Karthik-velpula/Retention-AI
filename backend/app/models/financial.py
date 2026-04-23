from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.session import Base


class Financial(Base):
    __tablename__ = "financial"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, unique=True)
    fee_due = Column(Float, nullable=False, default=0)
    payment_delay_days = Column(Integer, nullable=False, default=0)
    scholarship_amount = Column(Float, nullable=False, default=0)

    student = relationship("Student", back_populates="financial")
