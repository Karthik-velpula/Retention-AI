from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_faculty
from app.db.session import get_db
from app.models.user import User
from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from app.services.assistant_service import answer_query

router = APIRouter()


@router.post("/assistant/query", response_model=AssistantQueryResponse)
def query_assistant(
    payload: AssistantQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_faculty),
):
    return AssistantQueryResponse(answer=answer_query(db, current_user, payload.query))
