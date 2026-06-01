"""Trade Agent: specialized agent for foreign trade customer service."""

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END

from app.agents.base import BaseAgent

TRADE_SYSTEM_PROMPT = """你是一个专业的外贸客服助手，精通跨境贸易的各个环节。

你的核心能力：
1. **产品咨询**: 回答产品规格、参数、用途等问题
2. **报价处理**: 协助生成报价单、解释价格构成
3. **物流方案**: 解答运输方式、时效、费用等问题
4. **贸易术语**: 解释 FOB、CIF、EXW 等国际贸易术语
5. **付款方式**: 说明 T/T、L/C、D/P 等付款方式的优缺点
6. **客户沟通**: 协助撰写专业的外贸邮件和沟通话术

工作原则：
- 优先基于知识库中的产品资料和贸易资料回答
- 中英文双语能力，根据客户语言习惯切换
- 专业、礼貌、高效的沟通风格
- 涉及价格、交期等关键信息时，标注信息来源
- 如果知识库中没有相关信息，诚实告知并建议联系人工客服

注意事项：
- 不要编造产品参数或价格信息
- 涉及合同条款时提醒客户与业务员确认
- 海关政策等时效性信息注明查询时间"""


class TradeAgent(BaseAgent):
    """Agent specialized in foreign trade customer service."""

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(MessagesState)

        builder.add_node("retrieve", self._retrieve_knowledge)
        builder.add_node("think", self._think)
        builder.add_node("respond", self._respond)

        builder.add_edge(START, "retrieve")
        builder.add_edge("retrieve", "think")
        builder.add_edge("think", "respond")
        builder.add_edge("respond", END)

        return builder.compile()

    async def _retrieve_knowledge(self, state: MessagesState) -> dict:
        """Retrieve relevant knowledge from the knowledge base."""
        messages = list(state["messages"])

        # Add system prompt
        system_msg = SystemMessage(content=TRADE_SYSTEM_PROMPT)

        # TODO: Use knowledge_tool to search relevant trade documents
        # For now, pass through with system prompt

        return {"messages": [system_msg] + messages}

    async def _think(self, state: MessagesState) -> dict:
        """LLM processes the request with retrieved context."""
        if not self.llm:
            return {"messages": state["messages"]}

        response = await self.llm.ainvoke(state["messages"])
        return {"messages": state["messages"] + [response]}

    async def _respond(self, state: MessagesState) -> dict:
        """Format and return the response."""
        return {"messages": state["messages"]}
