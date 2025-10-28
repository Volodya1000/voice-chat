# repositories/message_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Message, MessageType
from typing import List
from datetime import datetime

class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_message(self, chat_id: int, content: str, message_type: MessageType) -> Message:
        msg = Message(chat_id=chat_id, content=content, message_type=message_type)
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def get_messages_for_chat(self, chat_id: int) -> List[Message]:
        q = await self.session.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
        )
        return q.scalars().all()

    async def get_recent_messages_for_chat(self, chat_id: int, limit: int = 100):
        q = await self.session.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.desc()).limit(limit)
        )
        return q.scalars().all()
