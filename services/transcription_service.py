import os
import io
import asyncio
import tempfile
from typing import Optional

from fastapi import HTTPException, UploadFile

# Предполагается, что эти библиотеки установлены: pip install pydub faster-whisper
try:
    from pydub import AudioSegment
    from pydub.exceptions import CouldntDecodeError
    from faster_whisper import WhisperModel
except ImportError:
    # Заглушки, если библиотеки не установлены
    class AudioSegment:
        @staticmethod
        def from_file(file): raise NotImplementedError("pydub not installed")


    class CouldntDecodeError(Exception):
        pass


    class WhisperModel:
        def __init__(self, *args, **kwargs): pass

        def transcribe(self, path, language): return [
            type('Segment', (object,), {'text': 'Модель Whisper не загружена.'})], None

# ---------------------------------------------------------------------
# ИНИЦИАЛИЗАЦИЯ WHISPER
# ---------------------------------------------------------------------

WHISPER_MODEL_SIZE = "small"  # Используем небольшую модель для CPU
whisper_model: Optional[WhisperModel] = None

try:
    # Загружаем модель Whisper при старте модуля
    # Внимание: для реального DI лучше загружать модель внутри контейнера
    whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    print(f"✅ STT Модель {WHISPER_MODEL_SIZE} загружена на CPU.")
except Exception as e:
    print(f"❌ Ошибка загрузки Whisper: {e}")
    # Если загрузка не удалась, модель остается None


# ---------------------------------------------------------------------
# КЛАСС СЕРВИСА
# ---------------------------------------------------------------------

class TranscriptionService:
    """
    Сервис для транскрипции аудио с использованием faster-whisper.
    Обрабатывает загрузку, конвертацию pydub и транскрипцию.
    """

    def __init__(self, model: Optional[WhisperModel] = whisper_model):
        self.model = model

    async def transcribe_audio(self, audio_file: UploadFile) -> str:
        if not self.model:
            raise HTTPException(status_code=503, detail="Whisper model not loaded or failed to initialize.")

        # Шаг 1: Чтение и сохранение аудио во временный файл
        # Используем tempfile для безопасного создания и управления временными файлами
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            temp_path = temp_audio_file.name

        try:
            # Чтение загруженного файла
            audio_bytes = await audio_file.read()

            # Pydub для конвертации (MediaRecorder может отдавать WEBM или OGG)
            # и сохранения в WAV, который предпочитает Whisper
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))

            # Конвертируем в WAV и сохраняем на диск
            # Используем asyncio.to_thread для блокирующей операции ввода/вывода
            await asyncio.to_thread(audio_segment.export, temp_path, format="wav")

            # Шаг 2: Транскрипция с faster-whisper
            # Также используем asyncio.to_thread, так как это блокирующая операция
            segments, _ = await asyncio.to_thread(self.model.transcribe, temp_path, language="ru")
            user_prompt = "".join([segment.text for segment in segments]).strip()

            print(f"🎤 Транскрипция: {user_prompt}")
            return user_prompt

        except CouldntDecodeError:
            raise HTTPException(status_code=400,
                                detail="Невозможно декодировать аудиофайл. Проверьте установку FFmpeg.")
        except Exception as e:
            # Общая ошибка при обработке или транскрипции
            raise HTTPException(status_code=500, detail=f"Ошибка транскрипции на сервере: {e}")
        finally:
            # Шаг 3: Удаление временного файла
            if os.path.exists(temp_path):
                os.remove(temp_path)