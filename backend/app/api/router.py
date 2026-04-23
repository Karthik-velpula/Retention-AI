from fastapi import APIRouter

from app.api.routes import analytics, assistant, auth, interventions, recommendations, students, training

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(assistant.router, tags=["assistant"])
api_router.include_router(analytics.router, tags=["analytics"])
api_router.include_router(interventions.router, tags=["interventions"])
api_router.include_router(recommendations.router, tags=["recommendations"])
api_router.include_router(training.router, tags=["training"])
