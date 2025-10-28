# services/chat_service.py
from models import MessageType
from langchain_ollama.llms import OllamaLLM
import asyncio
from dtos import MessageDTO
import json
from collections import defaultdict
from repositories.message_repo import MessageRepository


class Broadcaster:
    """
    Управляет подписчиками SSE и рассылает сообщения (полные или токены).
    """

    def __init__(self):
        # Очереди теперь хранят словари (полные SSE-события)
        self._listeners: dict[int, set[asyncio.Queue[dict]]] = defaultdict(set)

    async def subscribe(self, chat_id: int) -> asyncio.Queue[dict]:
        """Подписывает клиента на обновления чата и возвращает очередь."""
        queue = asyncio.Queue()
        self._listeners[chat_id].add(queue)
        return queue

    def unsubscribe(self, chat_id: int, queue: asyncio.Queue[dict]):
        """Отписывает клиента от обновлений."""
        try:
            self._listeners[chat_id].remove(queue)
            if not self._listeners[chat_id]:
                del self._listeners[chat_id]
        except (KeyError, ValueError):
            pass  # Игнорируем, если уже отписан

    async def publish_message(self, chat_id: int, message_json: str):
        """Публикует полное новое сообщение."""
        event_data = {
            "event": "new_message",
            "data": message_json
        }
        for queue in self._listeners.get(chat_id, set()):
            await queue.put(event_data)

    async def publish_token(self, chat_id: int, msg_id: int, token: str):
        """Публикует один токен для существующего сообщения."""
        token_data = {"msg_id": msg_id, "token": token}
        event_data = {
            "event": "stream_token",
            "data": json.dumps(token_data)
        }
        for queue in self._listeners.get(chat_id, set()):
            await queue.put(event_data)


class ChatService:
    def __init__(self, message_repo: MessageRepository, broadcaster: Broadcaster):
        self.message_repo = message_repo
        self.broadcaster = broadcaster
        # Используйте вашу фактическую модель Ollama
        self.llm = OllamaLLM(model="saiga_llama3_8b:latest")

        # Обратите внимание: аргумент user_id остался для получения ID текущего пользователя

    async def process_user_message(self, chat_id: int, content: str, user_id: int) -> None:
        """
        Обрабатывает сообщение пользователя, запускает стриминг ответа модели.
        """

        # 1. Сохраняем и публикуем сообщение пользователя
        try:
            # --- ИСПРАВЛЕНО: user_id теперь передается для сообщения пользователя ---
            user_msg = await self.message_repo.add_message(
                chat_id=chat_id,
                content=content,
                message_type=MessageType.USER,
                user_id=user_id  # <-- АКТИВИРОВАНО: Передаем ID пользователя
            )
            await self.broadcaster.publish_message(
                chat_id,
                MessageDTO.model_validate(user_msg).model_dump_json()
            )
        except Exception as e:
            print(f"Error saving user message: {e}")
            return

        # 2. Создаем ПУСТОЕ сообщение-плейсхолдер от модели
        try:
            # --- ИСПРАВЛЕНО: Передаем user_id=None для сообщения модели ---
            model_msg = await self.message_repo.add_message(
                chat_id=chat_id,
                content="",
                message_type=MessageType.MODEL,
                user_id=None  # <-- АКТИВИРОВАНО: Сообщение модели не принадлежит пользователю
            )
            # 3. Публикуем это пустое сообщение, чтобы JS создал div
            await self.broadcaster.publish_message(
                chat_id,
                MessageDTO.model_validate(model_msg).model_dump_json()
            )
        except Exception as e:
            print(f"Error creating placeholder model message: {e}")
            return

        # 4. Запускаем стриминг LLM и публикуем токены
        full_content = []
        try:
            # В production-коде здесь нужно передавать контекст (предыдущие сообщения)
            async for token in self.llm.astream(content):
                full_content.append(token)
                await self.broadcaster.publish_token(
                    chat_id,
                    model_msg.id,
                    token
                )
        except Exception as e:
            print(f"Error during LLM stream: {e}")
            await self.broadcaster.publish_token(
                chat_id,
                model_msg.id,
                "\n[ОШИБКА ГЕНЕРАЦИИ ОТВЕТА]"
            )

        # 5. Сохраняем полный ответ в БД
        final_content = "".join(full_content)
        try:
            await self.message_repo.update_message_content(
                model_msg.id,
                final_content
            )
        except Exception as e:
            print(f"Error updating model message content: {e}")