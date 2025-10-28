from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from models import Message, \
    MessageType  # Предполагается, что 'Message' имеет поля 'id', 'chat_id', 'user_id', 'content', 'message_type', 'created_at'
from typing import List
from datetime import datetime
from typing import Optional


class MessageRepository:
    """
    Репозиторий для управления сообщениями в базе данных.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_message(
            self,
            chat_id: int,
            content: str,
            message_type: MessageType,
            user_id: Optional[int] = None  # <-- ДОБАВЛЕНО: Теперь user_id опционален
    ) -> Message:
        """Сохраняет новое сообщение в базу данных."""
        message = Message(
            chat_id=chat_id,
            content=content,
            message_type=message_type,
            user_id=user_id  # <-- ПЕРЕДАЕМ user_id в конструктор модели
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def update_message_content(self, message_id: int, new_content: str):
        """Обновляет содержимое существующего сообщения по ID."""
        message = await self.session.get(Message, message_id)
        if message:
            message.content = new_content
            await self.session.commit()
            return True
        return False

    async def get_messages_for_chat(self, chat_id: int) -> List[Message]:
        """
        Получает все сообщения для чата, отсортированные по времени.
        """
        q = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        return q.scalars().all()

    async def get_recent_messages_for_chat(self, chat_id: int, limit: int = 100) -> List[Message]:
        """
        Получает последние N сообщений для контекста LLM.
        """
        q = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        # Результат нужно развернуть, так как мы получаем его в обратном порядке
        return list(q.scalars().all())[::-1]