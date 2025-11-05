# services/chat_service.py
import os

from models import MessageType
from langchain_ollama.llms import OllamaLLM
from dtos import MessageDTO
from repositories.message_repo import MessageRepository
from services.broadcaster_service import Broadcaster
from services.local_tts_service import LocalTextToVoiceService


class ChatService:
    def __init__(
        self,
        message_repo: MessageRepository,
        broadcaster: Broadcaster,
        tts_service: LocalTextToVoiceService | None = None,  # <-- добавляем
    ):
        self.message_repo = message_repo
        self.broadcaster = broadcaster
        self.tts_service = tts_service  # <-- сохраняем сервис TTS
        self.llm = OllamaLLM(model="saiga_llama3_8b:latest")

        # Обратите внимание: аргумент user_id остался для получения ID текущего пользователя

    async def process_user_message(self, chat_id: int, content: str, user_id: int,
                                   tts_options: dict | None = None) -> None:
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

        try:
            if tts_options and tts_options.get("voice_enabled") and self.tts_service:
                print(f"[DEBUG] Generating TTS audio for msg_id={model_msg.id}")

                # Генерируем аудио (synthesize_to_bytes возвращает bytes WAV)
                audio_bytes = self.tts_service.synthesize_to_bytes(
                    text=final_content,
                    speaker=tts_options.get("speaker", "aidar"),
                    speed=tts_options.get("speed", 1.0),
                    pitch_semitones=tts_options.get("pitch_semitones", 0),
                    gain_db=tts_options.get("gain_db", 0.0),
                    reverb_time=tts_options.get("reverb_time", 0.0),
                    reverb_decay=tts_options.get("reverb_decay", 0.0),
                )

                # Сохраняем на диск в директорию кеша
                tts_cache_dir = os.getenv("TTS_CACHE_DIR", "/tmp/tts_cache")
                os.makedirs(tts_cache_dir, exist_ok=True)
                audio_path = os.path.join(tts_cache_dir, f"tts_{model_msg.id}.wav")
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)

                # Публикуем событие для клиентов, чтобы они могли скачать/воспроизвести
                audio_url = f"/chats/{chat_id}/messages/{model_msg.id}/audio"
                await self.broadcaster.publish_audio(
                    chat_id=chat_id,
                    msg_id=model_msg.id,
                    audio_url=audio_url
                )
        except Exception as e:
            print(f"TTS generation error for msg {model_msg.id}: {e}")