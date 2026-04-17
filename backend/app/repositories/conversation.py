from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationMessage


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, app_id: uuid.UUID, title: str = "새 대화") -> Conversation:
        conv = Conversation(app_id=app_id, title=title)
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def list_by_app(self, app_id: uuid.UUID) -> list[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.app_id == app_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, conv_id: uuid.UUID) -> Conversation | None:
        return await self._session.get(Conversation, conv_id)

    async def delete(self, conv_id: uuid.UUID) -> bool:
        conv = await self.get(conv_id)
        if conv is None:
            return False
        await self._session.delete(conv)
        await self._session.flush()
        return True

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        run_id: uuid.UUID | None = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            run_id=run_id,
        )
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def get_messages(self, conversation_id: uuid.UUID) -> list[ConversationMessage]:
        result = await self._session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def update_title(self, conv_id: uuid.UUID, title: str) -> None:
        conv = await self.get(conv_id)
        if conv is not None:
            conv.title = title[:200]
            await self._session.flush()
