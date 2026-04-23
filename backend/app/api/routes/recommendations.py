from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_faculty
from app.db.session import get_db
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import get_student_recommendations

router = APIRouter()


@router.get("/recommendations/{student_id}", response_model=RecommendationResponse)
def recommendations(student_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_faculty)):
    return get_student_recommendations(db, student_id, current_user)
