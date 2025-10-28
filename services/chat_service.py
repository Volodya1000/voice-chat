# services/chat_service.py
from models import MessageType
from langchain_ollama.llms import OllamaLLM
import asyncio

# --- НОВЫЙ КОД ---
from collections import defaultdict
from dtos import MessageDTO  # Нужен для сериализации сообщения в JSON
import json


# --- КОНЕЦ НОВОГО КОДА ---


# --- НОВЫЙ КЛАСС ДЛЯ SSE ---
class Broadcaster:
    """Управляет подписчиками SSE и рассылает сообщения."""

    def __init__(self):
        # Словарь, где ключ - chat_id, а значение - set() очередей (подписчиков)
        self._listeners: dict[int, set[asyncio.Queue]] = defaultdict(set)

    async def subscribe(self, chat_id: int) -> asyncio.Queue:
        """Подписывает клиента на обновления чата и возвращает очередь."""
        queue = asyncio.Queue()
        self._listeners[chat_id].add(queue)
        return queue

    def unsubscribe(self, chat_id: int, queue: asyncio.Queue):
        """Отписывает клиента от обновлений."""
        try:
            self._listeners[chat_id].remove(queue)
            if not self._listeners[chat_id]:
                del self._listeners[chat_id]
        except (KeyError, ValueError):
            pass  # Игнорируем, если уже отписан

    async def publish(self, chat_id: int, message_json: str):
        """Публикует сообщение (уже в виде JSON) всем подписчикам чата."""
        for queue in self._listeners.get(chat_id, set()):
            await queue.put(message_json)


# --- КОНЕЦ НОВОГО КЛАССА ---


class ChatService:
    def __init__(self, message_repo, broadcaster: Broadcaster):  # <-- ИЗМЕНЕНО
        """
        message_repo: любой объект, у которого есть метод `add_message(...)`
        broadcaster: Экземпляр Broadcaster для SSE
        """
        self.message_repo = message_repo
        self.llm = OllamaLLM(model="saiga_llama3_8b:latest")
        self.broadcaster = broadcaster  # <-- ИЗМЕНЕНО

    async def process_user_message(self, chat_id: int, content: str) -> None:
        # 1. Сохраняем сообщение пользователя
        user_msg = await self.message_repo.add_message(  # <-- ИЗМЕНЕНО
            chat_id=chat_id,
            content=content,
            message_type=MessageType.USER
        )

        # --- НОВЫЙ КОД ---
        # 2. Публикуем сообщение пользователя в SSE
        #    Сериализуем его с помощью DTO, как в api.py
        await self.broadcaster.publish(
            chat_id,
            MessageDTO.model_validate(user_msg).model_dump_json()
        )
        # --- КОНЕЦ НОВОГО КОДА ---

        # 3. Получаем ответ модели через LangChain LLM
        model_response = await self._invoke_llm_async(content)

        # 4. Сохраняем ответ модели
        model_msg = await self.message_repo.add_message(  # <-- ИЗМЕНЕНО
            chat_id=chat_id,
            content=model_response,
            message_type=MessageType.MODEL
        )

        # --- НОВЫЙ КОД ---
        # 5. Публикуем ответ модели в SSE
        await self.broadcaster.publish(
            chat_id,
            MessageDTO.model_validate(model_msg).model_dump_json()
        )
        # --- КОНЕЦ НОВОГО КОДА ---

    async def _invoke_llm_async(self, prompt: str) -> str:
        """
        Обёртка для вызова синхронного метода `invoke` в асинхронном коде
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.llm.invoke, prompt)