"""Chat API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    ConversationDetailResponse,
)
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("/sessions", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: ConversationCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session with a specific agent."""
    service = ChatService(db)
    conv = await service.create_conversation(
        user_id=user_id,
        agent_name=request.agent_name,
        title=request.title,
    )
    return conv


@router.get("/sessions", response_model=List[ConversationResponse])
async def list_conversations(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions for the current user."""
    service = ChatService(db)
    conversations = await service.list_conversations(user_id)
    return conversations


@router.get("/sessions/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conv_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with all its messages."""
    service = ChatService(db)
    conv = await service.get_conversation(conv_id, user_id)
    return conv


@router.get("/sessions/{conv_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conv_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation."""
    service = ChatService(db)
    messages = await service.get_messages(conv_id, user_id)
    return messages


@router.post("/sessions/{conv_id}/messages")
async def send_message(
    conv_id: UUID,
    request: MessageCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to an agent and get a response.

    If stream=True, returns Server-Sent Events (SSE).
    If stream=False, returns the complete response.
    """
    service = ChatService(db)

    if request.stream:
        return StreamingResponse(
            service.stream_message(conv_id, user_id, request.message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        response = await service.send_message(conv_id, user_id, request.message)
        return response


@router.delete("/sessions/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    service = ChatService(db)
    await service.delete_conversation(conv_id, user_id)
