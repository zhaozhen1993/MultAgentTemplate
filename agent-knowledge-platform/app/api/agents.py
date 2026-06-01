"""Agent listing API endpoints."""

from fastapi import APIRouter
from app.schemas.agent import AgentResponse, AgentListResponse
from app.services.agent_service import AgentService

router = APIRouter()


@router.get("", response_model=AgentListResponse)
async def list_agents():
    """List all available agents."""
    service = AgentService()
    agents = service.list_agents()
    return AgentListResponse(agents=agents)


@router.get("/{agent_name}", response_model=AgentResponse)
async def get_agent(agent_name: str):
    """Get details of a specific agent."""
    service = AgentService()
    agent = service.get_agent(agent_name)
    return agent
