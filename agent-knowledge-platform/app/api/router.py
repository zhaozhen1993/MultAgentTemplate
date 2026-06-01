"""API router registration."""

from fastapi import APIRouter

from app.api import auth, knowledge, chat, agents

api_router = APIRouter(prefix="/api/v1")

# Register sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
