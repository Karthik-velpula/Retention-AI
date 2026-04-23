from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    model_name = Column(String(50), nullable=False)
    explanation = Column(String(1000), nullable=False)
    feature_importance = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="predictions")
