import os
import io
import asyncio
import tempfile
from typing import Optional

from fastapi import HTTPException, UploadFile
from faster_whisper import WhisperModel

WHISPER_MODEL_SIZE = "small"
whisper_model: Optional[WhisperModel] = None

try:
    whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    print(f"✅ STT Модель {WHISPER_MODEL_SIZE} загружена на CPU.")
except Exception as e:
    print(f"❌ Ошибка загрузки Whisper: {e}")

class TranscriptionService:
    def __init__(self, model: Optional[WhisperModel] = whisper_model):
        self.model = model

    async def transcribe_audio(self, audio_file: UploadFile) -> str:
        if not self.model:
            raise HTTPException(status_code=503, detail="Whisper model not loaded or failed to initialize.")

        # Создаем временный файл с тем же расширением, что и оригинальный файл
        ext = os.path.splitext(audio_file.filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_audio_file:
            temp_path = temp_audio_file.name

        try:
            audio_bytes = await audio_file.read()
            # Записываем аудио в временный файл
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)

            # Транскрипция
            segments, _ = await asyncio.to_thread(self.model.transcribe, temp_path, language="ru")
            user_prompt = "".join([segment.text for segment in segments]).strip()
            print(f"🎤 Транскрипция: {user_prompt}")
            return user_prompt

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка транскрипции на сервере: {e}")

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
