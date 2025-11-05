import asyncio
import json
from collections import defaultdict

class Broadcaster:
    """
    Управляет подписчиками SSE и рассылает сообщения (полные, токены и аудио).
    """

    def __init__(self):
        # Очереди теперь хранят словари с событием и данными
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

    async def publish_audio(self, chat_id: int, msg_id: int, audio_url: str):
        event_data = {
            "event": "audio_ready",
            "data": json.dumps({"msg_id": msg_id, "audio_url": audio_url})
        }
        for queue in self._listeners.get(chat_id, set()):
            await queue.put(event_data)
        print(f"[DEBUG] Broadcaster sent audio_ready to {len(self._listeners.get(chat_id, []))} listeners")

