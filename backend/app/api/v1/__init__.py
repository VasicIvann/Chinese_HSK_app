from fastapi import APIRouter

from app.api.v1 import auth, quizzes

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(quizzes.router)

__all__ = ["api_router"]
