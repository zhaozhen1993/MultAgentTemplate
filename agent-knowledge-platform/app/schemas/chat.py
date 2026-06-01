"""Chat conversation request/response schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """Create conversation request."""
    agent_name: str = Field(..., min_length=1, max_length=100)
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: UUID
    agent_name: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    """Create message request (send message to agent)."""
    message: str = Field(..., min_length=1)
    stream: bool = True


class MessageResponse(BaseModel):
    """Message response."""
    id: UUID
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """Conversation with messages."""
    id: UUID
    agent_name: str
    title: Optional[str]
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
