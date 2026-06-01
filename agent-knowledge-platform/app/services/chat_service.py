"""Chat service: conversation management and agent invocation."""

import json
from typing import List, AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, AgentError
from app.models.conversation import Conversation, Message


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(
        self,
        user_id: UUID,
        agent_name: str,
        title: str = None,
    ) -> Conversation:
        """Create a new conversation."""
        conv = Conversation(
            user_id=user_id,
            agent_name=agent_name,
            title=title or f"New {agent_name} conversation",
        )
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def list_conversations(self, user_id: UUID) -> List[Conversation]:
        """List all conversations for a user."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_conversation(self, conv_id: UUID, user_id: UUID) -> Conversation:
        """Get a conversation with messages, verifying ownership."""
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise NotFoundError("Conversation", str(conv_id))
        return conv

    async def get_messages(self, conv_id: UUID, user_id: UUID) -> List[Message]:
        """Get all messages in a conversation."""
        await self.get_conversation(conv_id, user_id)  # Verify ownership

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def send_message(self, conv_id: UUID, user_id: UUID, content: str) -> dict:
        """Send a message and get a complete (non-streaming) response."""
        conv = await self.get_conversation(conv_id, user_id)

        # Save user message
        user_msg = Message(
            conversation_id=conv_id,
            role="user",
            content=content,
        )
        self.db.add(user_msg)
        await self.db.flush()

        # Get conversation history
        messages = await self.get_messages(conv_id, user_id)

        # Invoke agent
        try:
            from app.services.agent_service import AgentService
            agent_service = AgentService()
            response = await agent_service.invoke_agent(
                agent_name=conv.agent_name,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            )
        except Exception as e:
            raise AgentError(str(e))

        # Save assistant message
        assistant_msg = Message(
            conversation_id=conv_id,
            role="assistant",
            content=response["content"],
            metadata_=response.get("metadata", {}),
        )
        self.db.add(assistant_msg)
        await self.db.flush()
        await self.db.refresh(assistant_msg)

        return {
            "id": str(assistant_msg.id),
            "role": "assistant",
            "content": assistant_msg.content,
            "metadata": assistant_msg.metadata_,
            "created_at": assistant_msg.created_at.isoformat(),
        }

    async def stream_message(
        self, conv_id: UUID, user_id: UUID, content: str
    ) -> AsyncGenerator[str, None]:
        """Send a message and stream the response via SSE."""
        conv = await self.get_conversation(conv_id, user_id)

        # Save user message
        user_msg = Message(
            conversation_id=conv_id,
            role="user",
            content=content,
        )
        self.db.add(user_msg)
        await self.db.flush()

        # Get conversation history
        messages = await self.get_messages(conv_id, user_id)

        # Stream agent response
        full_content = ""
        try:
            from app.services.agent_service import AgentService
            agent_service = AgentService()

            async for chunk in agent_service.stream_agent(
                agent_name=conv.agent_name,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            ):
                if chunk["type"] == "token":
                    full_content += chunk["content"]
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_msg = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_msg)}\n\n"

        # Save assistant message
        if full_content:
            assistant_msg = Message(
                conversation_id=conv_id,
                role="assistant",
                content=full_content,
            )
            self.db.add(assistant_msg)
            await self.db.flush()

        yield "data: [DONE]\n\n"

    async def delete_conversation(self, conv_id: UUID, user_id: UUID) -> None:
        """Delete a conversation and all its messages."""
        conv = await self.get_conversation(conv_id, user_id)
        await self.db.delete(conv)
