# file: services/chat_service.py

import os
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from dtos import MessageDTO
from models import MessageType
from repositories.message_repo import MessageRepository
from services.broadcaster_service import Broadcaster
from services.local_tts_service import LocalTextToVoiceService

from services.agent_service import AgentService


class ChatService:
    def __init__(
            self,
            message_repo: MessageRepository,
            broadcaster: Broadcaster,
            agent_service: AgentService,
            tts_service: LocalTextToVoiceService | None = None,
    ):
        self.message_repo = message_repo
        self.broadcaster = broadcaster
        self.agent_service = agent_service
        self.tts_service = tts_service

    async def process_user_message(
            self,
            chat_id: int,
            content: str,
            user_id: int,
            tts_options: dict | None = None
    ) -> None:
        """
        Обрабатывает сообщение пользователя:
          1. сохраняет и публикует сообщение пользователя
          2. создаёт пустое сообщение от модели
          3. формирует историю чата (БЕЗ нового сообщения)
          4. ! ЗАПУСКАЕТ АГЕНТА  со стримом
          5. сохраняет результат и TTS (если включён)
        """
        user_msg = await self._save_and_publish_user_message(chat_id, content, user_id)
        if not user_msg:
            return

        model_msg = await self._create_placeholder_model_message(chat_id)
        if not model_msg:
            return

        messages = await self._build_message_history(chat_id)

        final_content = await self.agent_service.arun_agent_stream(
            chat_id=chat_id,
            model_msg_id=model_msg.id,
            input_query=content,
            history_messages=messages,
            broadcaster=self.broadcaster
        )

        if final_content:
            await self.message_repo.update_message_content(model_msg.id, final_content)
            await self._maybe_generate_tts(chat_id, model_msg.id, final_content, tts_options)


    async def _save_and_publish_user_message(self, chat_id: int, content: str, user_id: int):
        """Сохраняет и публикует сообщение пользователя."""
        try:
            msg = await self.message_repo.add_message(
                chat_id=chat_id,
                content=content,
                message_type=MessageType.USER,
                user_id=user_id
            )
            await self.broadcaster.publish_message(
                chat_id,
                MessageDTO.model_validate(msg).model_dump_json()
            )
            return msg
        except Exception as e:
            print(f"Error saving user message: {e}")
            return None

    async def _create_placeholder_model_message(self, chat_id: int):
        try:
            msg = await self.message_repo.add_message(
                chat_id=chat_id,
                content="",
                message_type=MessageType.MODEL,
                user_id=None
            )
            await self.broadcaster.publish_message(
                chat_id,
                MessageDTO.model_validate(msg).model_dump_json()
            )
            return msg
        except Exception as e:
            print(f"Error creating placeholder model message: {e}")
            return None

    async def _build_message_history(self, chat_id: int, limit: int = 50):
        try:
            messages = await self.message_repo.get_recent_messages_for_chat(chat_id, limit)

            if messages and messages[-1].message_type == MessageType.USER:
                messages = messages[:-1]
            result = [SystemMessage(content="Ты — полезный помощник».")]

            for m in messages:
                if not m.content:
                    continue

                if m.message_type == MessageType.MODEL and not m.content:
                    continue

                if m.message_type == MessageType.USER:
                    result.append(HumanMessage(content=m.content))
                elif m.message_type == MessageType.MODEL:
                    result.append(AIMessage(content=m.content))

            return result
        except Exception as e:
            print(f"Error building chat history: {e}")
            return [SystemMessage(content="Ты — полезный помощник для сотрудников компании УП «Белтехосмотр».")]


    async def _maybe_generate_tts(self, chat_id: int, msg_id: int, text: str, tts_options: dict | None):
        if not (tts_options and tts_options.get("voice_enabled") and self.tts_service):
            return

        try:
            print(f"[DEBUG] Generating TTS audio for msg_id={msg_id}")
            audio_bytes = self.tts_service.synthesize_to_bytes(
                text=text,
                speaker=tts_options.get("speaker", "aidar"),
                speed=tts_options.get("speed", 1.0),
                pitch_semitones=tts_options.get("pitch_semitones", 0),
                gain_db=tts_options.get("gain_db", 0.0),
                reverb_time=tts_options.get("reverb_time", 0.0),
                reverb_decay=tts_options.get("reverb_decay", 0.0),
            )

            tts_cache_dir = os.getenv("TTS_CACHE_DIR", "/tmp/tts_cache")
            os.makedirs(tts_cache_dir, exist_ok=True)
            audio_path = os.path.join(tts_cache_dir, f"tts_{msg_id}.wav")
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            audio_url = f"/chats/{chat_id}/messages/{msg_id}/audio"
            await self.broadcaster.publish_audio(chat_id, msg_id, audio_url)
        except Exception as e:
            print(f"TTS generation error for msg {msg_id}: {e}")