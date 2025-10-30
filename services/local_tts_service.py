import io
import torch
import soundfile as sf
from typing import List


class LocalTextToVoiceService:
    """
    Локальный сервис TTS (Text-to-Speech) на базе Silero.
    """

    DEFAULT_LANGUAGE = 'ru'
    DEFAULT_MODEL_ID = 'v4_ru'
    DEFAULT_SAMPLE_RATE = 48000

    def __init__(self,
                 language: str = DEFAULT_LANGUAGE,
                 model_id: str = DEFAULT_MODEL_ID,
                 sample_rate: int = DEFAULT_SAMPLE_RATE):
        self.language = language
        self.model_id = model_id
        self.sample_rate = sample_rate
        self.device = self._select_device()
        self.model = None
        self.speakers: List[str] = []
        self._load_model()

    def _select_device(self) -> torch.device:
        if torch.cuda.is_available():
            print("🚀 Используется CUDA (GPU).")
            return torch.device('cuda')
        else:
            print("🖥️ Используется CPU.")
            return torch.device('cpu')

    def _load_model(self):
        print(f"Загрузка модели Silero ({self.model_id})...")
        try:
            self.model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-models',
                model='silero_tts',
                language=self.language,
                speaker=self.model_id
            )
            self.model.to(self.device)
            self.speakers = self.model.speakers
            print(f"✅ Модель загружена. Доступные дикторы: {self.speakers}")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            self.model = None

    def synthesize_to_bytes(self, text: str, speaker: str = 'aidar') -> bytes:
        """
        Синтезирует речь в память и возвращает в виде байтов .wav.
        """
        if not self.model:
            raise RuntimeError("TTS модель не загружена")

        if speaker not in self.speakers:
            raise ValueError(f"Голос '{speaker}' не найден. Доступные: {self.speakers}")

        # Генерация аудио
        audio = self.model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=self.sample_rate
        )

        # Конвертация в wav (байты)
        buffer = io.BytesIO()
        sf.write(buffer, audio.cpu().numpy(), self.sample_rate, format='WAV')
        buffer.seek(0)
        return buffer.read()
