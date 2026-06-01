"""Agent response schemas."""

from typing import List, Optional

from pydantic import BaseModel


class AgentResponse(BaseModel):
    """Agent information response."""
    name: str
    display_name: str
    description: Optional[str]
    tools: List[str]
    is_active: bool


class AgentListResponse(BaseModel):
    """List of available agents."""
    agents: List[AgentResponse]
