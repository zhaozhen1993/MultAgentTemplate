"""Code Agent: specialized agent for code writing, debugging, and explanation."""

from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END

from app.agents.base import BaseAgent

CODE_SYSTEM_PROMPT = """你是一个专业的代码助手，精通多种编程语言和技术栈。

你的核心能力：
1. **代码编写**: 根据需求编写高质量、可维护的代码
2. **代码调试**: 分析和修复代码中的 bug
3. **代码解释**: 详细解释代码逻辑和工作原理
4. **最佳实践**: 提供架构设计和编码最佳实践建议

工作原则：
- 代码示例要完整可运行
- 解释要清晰易懂，适合不同水平的开发者
- 如果涉及知识库中的代码或文档，请基于知识库内容回答
- 对于不确定的内容，诚实说明

回答格式：
- 代码块使用正确的语言标记
- 关键步骤添加注释
- 必要时提供使用示例"""


class CodeAgent(BaseAgent):
    """Agent specialized in code-related tasks."""

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(MessagesState)

        builder.add_node("prepare", self._prepare_context)
        builder.add_node("think", self._think)
        builder.add_node("respond", self._respond)

        builder.add_edge(START, "prepare")
        builder.add_edge("prepare", "think")
        builder.add_edge("think", "respond")
        builder.add_edge("respond", END)

        return builder.compile()

    async def _prepare_context(self, state: MessagesState) -> dict:
        """Prepare context by searching knowledge base if available."""
        messages = list(state["messages"])

        # Add system prompt
        system_msg = SystemMessage(content=CODE_SYSTEM_PROMPT)

        # TODO: If knowledge base tools are available, search for relevant context
        # For now, just pass through with system prompt

        return {"messages": [system_msg] + messages}

    async def _think(self, state: MessagesState) -> dict:
        """LLM processes the request."""
        if not self.llm:
            return {"messages": state["messages"]}

        response = await self.llm.ainvoke(state["messages"])
        return {"messages": state["messages"] + [response]}

    async def _respond(self, state: MessagesState) -> dict:
        """Format and return the response."""
        # The response is already in the messages from the think step
        return {"messages": state["messages"]}
