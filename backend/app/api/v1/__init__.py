from fastapi import APIRouter

from app.api.v1 import account, auth, drawings, examples, expression, mastery, quizzes, srs

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(quizzes.router)
api_router.include_router(srs.router)
api_router.include_router(mastery.router)
api_router.include_router(expression.router)
api_router.include_router(examples.router)
api_router.include_router(drawings.router)
api_router.include_router(account.router)

__all__ = ["api_router"]
