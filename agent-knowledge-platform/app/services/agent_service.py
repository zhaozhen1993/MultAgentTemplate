"""Agent service: agent lifecycle management and invocation."""

from typing import List, AsyncGenerator

from app.schemas.agent import AgentResponse


class AgentService:
    """Manages agent discovery and invocation."""

    def __init__(self):
        self._agents = self._load_default_agents()

    def _load_default_agents(self) -> dict:
        """Load built-in agent configurations."""
        return {
            "code_agent": AgentResponse(
                name="code_agent",
                display_name="代码助手",
                description="专业的代码编写、调试和解释助手，精通多种编程语言",
                tools=["search_knowledge", "run_code"],
                is_active=True,
            ),
            "trade_agent": AgentResponse(
                name="trade_agent",
                display_name="外贸客服助手",
                description="专业的外贸客服，精通跨境贸易流程、报价、物流、客户沟通",
                tools=["search_knowledge", "query_exchange_rate"],
                is_active=True,
            ),
            "general_agent": AgentResponse(
                name="general_agent",
                display_name="通用助手",
                description="通用问答助手，可以回答各种问题",
                tools=["search_knowledge"],
                is_active=True,
            ),
        }

    def list_agents(self) -> List[AgentResponse]:
        """List all available agents."""
        return [a for a in self._agents.values() if a.is_active]

    def get_agent(self, name: str) -> AgentResponse:
        """Get agent by name."""
        agent = self._agents.get(name)
        if not agent:
            # Fall back to general agent
            agent = self._agents.get("general_agent")
        return agent

    async def invoke_agent(
        self,
        agent_name: str,
        messages: list,
    ) -> dict:
        """Invoke an agent with messages and get a complete response."""
        from app.llm.factory import LLMFactory
        from app.config import settings

        agent_config = self.get_agent(agent_name)

        # Create LLM instance
        llm = LLMFactory.create(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

        # Build system prompt
        system_prompt = self._build_system_prompt(agent_config)

        # Prepare messages for LLM
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        lc_messages = [SystemMessage(content=system_prompt)]
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        # Invoke LLM
        response = await llm.ainvoke(lc_messages)

        return {
            "content": response.content,
            "metadata": {
                "agent": agent_name,
                "model": settings.LLM_MODEL,
            },
        }

    async def stream_agent(
        self,
        agent_name: str,
        messages: list,
    ) -> AsyncGenerator[dict, None]:
        """Invoke an agent and stream the response."""
        from app.llm.factory import LLMFactory
        from app.config import settings

        agent_config = self.get_agent(agent_name)

        llm = LLMFactory.create(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

        system_prompt = self._build_system_prompt(agent_config)

        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        lc_messages = [SystemMessage(content=system_prompt)]
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        yield {"type": "thinking", "content": f"{agent_config.display_name} 正在思考..."}

        async for chunk in llm.astream(lc_messages):
            if chunk.content:
                yield {"type": "token", "content": chunk.content}

        yield {"type": "done", "content": ""}

    def _build_system_prompt(self, agent: AgentResponse) -> str:
        """Build the system prompt for an agent."""
        prompts = {
            "code_agent": """你是一个专业的代码助手。你的职责包括：
1. 编写高质量、可维护的代码
2. 调试和修复代码问题
3. 解释代码逻辑和概念
4. 提供最佳实践建议

请用清晰的代码示例和详细的解释来回答问题。如果涉及知识库中的内容，请基于知识库回答。""",

            "trade_agent": """你是一个专业的外贸客服助手。你的职责包括：
1. 回答客户关于产品规格、价格、交期的咨询
2. 协助处理询盘和报价
3. 解答物流、海关、付款方式相关问题
4. 用中英双语与客户沟通

请基于知识库中的外贸资料回答问题。如果知识库中没有相关信息，请诚实告知。""",

            "general_agent": """你是一个有用的通用助手。请用清晰、准确的方式回答用户的问题。
如果知识库中有相关信息，请优先基于知识库内容回答。""",
        }

        return prompts.get(agent.name, prompts["general_agent"])
