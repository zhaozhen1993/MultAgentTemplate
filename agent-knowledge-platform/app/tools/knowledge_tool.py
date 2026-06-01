"""Knowledge base search tool for agents."""

from typing import Optional
from pydantic import Field

from app.tools.base import BaseTool


class KnowledgeSearchTool(BaseTool):
    """Search the user's knowledge base for relevant information."""

    name: str = "search_knowledge"
    description: str = (
        "Search the knowledge base for information relevant to the user's query. "
        "Use this when you need to find specific documents, facts, or context from uploaded files. "
        "Input should be a clear search query."
    )
    tool_type: str = "knowledge"
    tenant_isolated: bool = True

    async def _arun(self, query: str, knowledge_base_id: str = None, top_k: int = 3) -> str:
        """Search the knowledge base.

        Args:
            query: The search query
            knowledge_base_id: Optional specific knowledge base to search
            top_k: Number of results to return

        Returns:
            Formatted search results as a string
        """
        try:
            # This will be injected with actual context at runtime
            # For now, return a placeholder
            if not knowledge_base_id:
                return "请先指定要搜索的知识库 ID。"

            # The actual search is performed through KnowledgeService
            # which requires database access (injected at runtime)
            return f"正在搜索知识库中关于 '{query}' 的信息..."

        except Exception as e:
            return f"搜索知识库时出错: {str(e)}"


class KnowledgeListTool(BaseTool):
    """List available knowledge bases for the current user."""

    name: str = "list_knowledge_bases"
    description: str = (
        "List all available knowledge bases for the current user. "
        "Use this to discover what knowledge bases exist before searching."
    )
    tool_type: str = "knowledge"
    tenant_isolated: bool = True

    async def _arun(self) -> str:
        """List available knowledge bases."""
        try:
            return "可用的知识库列表将在运行时注入。"
        except Exception as e:
            return f"获取知识库列表时出错: {str(e)}"
