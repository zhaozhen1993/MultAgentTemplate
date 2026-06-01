"""Base Agent abstract class for LangGraph-based agents."""

from abc import ABC, abstractmethod
from typing import Any

from langgraph.graph import StateGraph


class BaseAgent(ABC):
    """Abstract base class for all agents in the platform.

    Subclasses must implement _build_graph() to define their LangGraph workflow.
    """

    def __init__(self, llm: Any, tools: list = None, config: dict = None):
        self.llm = llm
        self.tools = tools or []
        self.config = config or {}
        self.graph = self._build_graph()

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """Build and return the LangGraph workflow.

        Returns:
            Compiled StateGraph instance
        """
        pass

    async def invoke(self, messages: list, context: dict = None) -> dict:
        """Execute the agent with given messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            context: Additional context (user_id, knowledge_base_ids, etc.)

        Returns:
            Dict with 'messages' key containing the response
        """
        state = {
            "messages": messages,
            "context": context or {},
        }
        result = await self.graph.ainvoke(state)
        return result
