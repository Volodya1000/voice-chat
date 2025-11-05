import io
import torch
import soundfile as sf
import numpy as np
from typing import List, Optional, Tuple

import librosa  # для pitch/time-stretch

def _select_device() -> torch.device:
    if torch.cuda.is_available():
        print("🚀 Используется CUDA (GPU).")
        return torch.device('cuda')
    else:
        print("🖥️ Используется CPU.")
        return torch.device('cpu')


class LocalTextToVoiceService:
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
        self.device = _select_device()
        self.model = None
        self.speakers: List[str] = []
        self._load_model()

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
            self.speakers = getattr(self.model, "speakers", [self.model_id])
            print(f"✅ Модель загружена. Доступные дикторы: {self.speakers}")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            self.model = None

    def synthesize_to_bytes(
        self,
        text: str,
        speaker: str = 'aidar',
        speed: float = 1.0,
        pitch_semitones: float = 0.0,
        gain_db: float = 0.0,
        reverb_time: float = 0.0,
        reverb_decay: float = 0.0,
        silence_before: float = 0.0,
        silence_after: float = 0.0
    ) -> bytes:
        """
        Синтез речи и пост-обработка с применением всех параметров.
        Возвращает WAV в виде байтов.
        """
        if not self.model:
            raise RuntimeError("TTS модель не загружена")

        if speaker not in self.speakers:
            raise ValueError(f"Голос '{speaker}' не найден. Доступные: {self.speakers}")

        # Генерация исходного аудио (numpy float32)
        wav_tensor = self.model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=self.sample_rate
        )
        wav = wav_tensor.detach().cpu().numpy().astype(np.float32)

        # -----------------------
        # Пост-обработка
        # -----------------------
        wav = self._add_silence(wav, silence_before, silence_after)
        wav = self._pitch_shift(wav, pitch_semitones)
        wav = self._time_stretch(wav, speed)
        wav = self._add_reverb(wav, reverb_time, reverb_decay)
        wav = self._normalize(wav)
        wav = self._change_volume(wav, gain_db)

        # Конвертация в WAV байты
        buffer = io.BytesIO()
        sf.write(buffer, wav, self.sample_rate, format='WAV')
        buffer.seek(0)
        return buffer.read()

    # -----------------------
    # Пост-обработка
    # -----------------------
    def _normalize(self, wav: np.ndarray, target_peak: float = 0.98) -> np.ndarray:
        peak = np.max(np.abs(wav))
        if peak > 0:
            wav = wav * (target_peak / peak)
        return wav.astype(np.float32)

    def _change_volume(self, wav: np.ndarray, db: float) -> np.ndarray:
        if abs(db) < 1e-3:  # если db ≈ 0, ничего не делаем
            return wav
        factor = 10 ** (db / 20)
        wav = wav * factor
        # Ограничиваем амплитуду, чтобы не было клиппинга
        max_val = np.max(np.abs(wav))
        if max_val > 1.0:
            wav = wav / max_val
        return wav.astype(np.float32)

    def _time_stretch(self, wav: np.ndarray, speed: float) -> np.ndarray:
        if abs(speed - 1.0) < 1e-6:
            return wav
        return librosa.effects.time_stretch(wav, rate=speed).astype(np.float32)

    def _pitch_shift(self, wav: np.ndarray, n_steps: float) -> np.ndarray:
        if abs(n_steps) < 1e-6:
            return wav
        return librosa.effects.pitch_shift(wav, sr=self.sample_rate, n_steps=n_steps).astype(np.float32)

    def _add_silence(self, wav: np.ndarray, before: float, after: float) -> np.ndarray:
        b = int(round(before * self.sample_rate))
        a = int(round(after * self.sample_rate))
        if b == 0 and a == 0:
            return wav
        silence_before = np.zeros(b, dtype=np.float32)
        silence_after = np.zeros(a, dtype=np.float32)
        return np.concatenate([silence_before, wav, silence_after]).astype(np.float32)


    def _add_reverb(self, wav: np.ndarray, reverb_time: float, decay: float) -> np.ndarray:
        # Проверяем корректность параметров
        if reverb_time <= 0 or decay <= 0 or decay >= 1:
            return wav

        # Создание импульсного отклика
        n = int(self.sample_rate * reverb_time)
        t = np.arange(n, dtype=np.float32)
        ir = decay ** (t / n)

        # Применение реверберации через свертку
        convolved = np.convolve(wav, ir, mode='full')[:len(wav)]

        # Добавление "мокрого" сигнала с уменьшенной громкостью
        out = wav + convolved * 0.15  # Значение 0.1–0.25 можно регулировать

        # Нормализация только если пик превышает 1
        peak = np.max(np.abs(out))
        if peak > 1.0:
            out /= peak

        return out.astype(np.float32)


