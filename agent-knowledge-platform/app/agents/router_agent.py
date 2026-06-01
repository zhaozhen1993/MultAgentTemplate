"""Router Agent: intent classification and agent dispatching."""

import json
import logging
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, MessagesState, START, END

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """你是一个意图识别路由器。根据用户的输入，判断应该由哪个 Agent 处理：

- code_agent: 代码编写、调试、解释代码、技术问题、编程相关
- trade_agent: 外贸相关、客户沟通、报价、物流、跨境贸易
- general_agent: 通用问答（默认，当不确定时使用）

请直接返回 JSON 格式：
{"agent": "agent_name", "confidence": 0.95, "reason": "原因"}

只返回 JSON，不要有其他内容。"""


class RouterAgent(BaseAgent):
    """Routes user requests to the appropriate specialized agent."""

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(MessagesState)

        builder.add_node("classify", self._classify_intent)
        builder.add_node("dispatch", self._dispatch)

        builder.add_edge(START, "classify")
        builder.add_edge("classify", "dispatch")
        builder.add_edge("dispatch", END)

        return builder.compile()

    async def _classify_intent(self, state: MessagesState) -> dict:
        """Classify user intent using LLM."""
        if not self.llm:
            # No LLM available, default to general
            return {"messages": state["messages"]}

        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            state["messages"][-1],  # Only classify the latest message
        ]

        try:
            response = await self.llm.ainvoke(messages)
            # Parse routing decision
            routing = self._parse_routing(response.content)
            logger.info(f"Routing decision: {routing}")
            # Store routing info in state
            return {
                "messages": state["messages"],
                "routing": routing,
            }
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {
                "messages": state["messages"],
                "routing": {"agent": "general_agent", "confidence": 0.5, "reason": "classification failed"},
            }

    async def _dispatch(self, state: MessagesState) -> dict:
        """Dispatch to the appropriate agent."""
        routing = state.get("routing", {"agent": "general_agent"})
        agent_name = routing.get("agent", "general_agent")

        # The actual agent invocation is handled by the service layer
        # This node just passes through with the routing decision
        return {"messages": state["messages"]}

    def _parse_routing(self, content: str) -> dict:
        """Parse the routing decision from LLM response."""
        try:
            # Try to extract JSON from response
            content = content.strip()
            if content.startswith("```"):
                # Remove code block markers
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)
        except (json.JSONDecodeError, IndexError):
            # Fallback: simple keyword matching
            content_lower = content.lower()
            if any(kw in content_lower for kw in ["code", "代码", "编程", "python", "javascript"]):
                return {"agent": "code_agent", "confidence": 0.6, "reason": "keyword fallback"}
            elif any(kw in content_lower for kw in ["trade", "外贸", "报价", "物流"]):
                return {"agent": "trade_agent", "confidence": 0.6, "reason": "keyword fallback"}
            else:
                return {"agent": "general_agent", "confidence": 0.5, "reason": "default fallback"}
