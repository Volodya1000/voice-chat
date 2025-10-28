# repositories/chat_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models import Chat
from typing import List, Optional

class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chat(self, user_id: int, title: str) -> Chat:
        chat = Chat(user_id=user_id, title=title)
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def list_chats_for_user(self, user_id: int) -> List[Chat]:
        q = await self.session.execute(
            select(Chat).where(Chat.user_id == user_id).order_by(Chat.created_at.desc())
        )
        return q.scalars().all()

    async def get_chat(self, chat_id: int) -> Optional[Chat]:
        q = await self.session.execute(select(Chat).where(Chat.id == chat_id))
        return q.scalars().first()

    async def delete_chat(self, chat_id: int) -> None:
        await self.session.execute(delete(Chat).where(Chat.id == chat_id))
        await self.session.commit()
