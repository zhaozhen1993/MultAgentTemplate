"""Base Tool class for the platform's tool system."""

from abc import abstractmethod
from typing import Optional

from langchain_core.tools import BaseTool as LCBaseTool
from pydantic import Field


class BaseTool(LCBaseTool):
    """Base class for all tools in the platform.

    Extends LangChain's BaseTool with platform-specific metadata.
    """

    # Platform metadata
    tool_type: str = Field(default="general", description="Tool category: general/knowledge/code/external")
    requires_auth: bool = Field(default=False, description="Whether this tool requires external API keys")
    tenant_isolated: bool = Field(default=True, description="Whether data is isolated per tenant")

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def _arun(self, *args, **kwargs) -> str:
        """Async execution - must be implemented by subclasses."""
        pass

    def _run(self, *args, **kwargs) -> str:
        """Sync execution - not supported, use async."""
        raise NotImplementedError("Use async version (_arun)")
