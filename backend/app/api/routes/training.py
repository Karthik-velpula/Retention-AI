from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_faculty
from app.db.session import get_db
from app.services.training_service import train_models

router = APIRouter()


@router.post("/train-model")
def train_model(db: Session = Depends(get_db), _: object = Depends(require_admin_or_faculty)):
    return train_models(db)
