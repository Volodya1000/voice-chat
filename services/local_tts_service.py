import io
import re
import traceback
from typing import List

import numpy as np
import soundfile as sf
import torch
import librosa


DIGIT_WORDS = {
    "0": "ноль",
    "1": "один",
    "2": "два",
    "3": "три",
    "4": "четыре",
    "5": "пять",
    "6": "шесть",
    "7": "семь",
    "8": "восемь",
    "9": "девять",
}


def _select_device() -> torch.device:
    if torch.cuda.is_available():
        print("🚀 Используется CUDA (GPU).")
        return torch.device("cuda")
    else:
        print("🖥️ Используется CPU.")
        return torch.device("cpu")


def sanitize_text(text: str) -> str:
    """
    Убирает LaTeX/форматирование, emoji и прочий мусор, нормализует
    некоторые математические символы в слова.
    """
    if text is None:
        return ""

    # Убираем LaTeX-обёртки \( ... \), \[...\], $$...$$, одиночные слеши
    text = re.sub(r"\\\(|\\\)|\\\[|\\\]", " ", text)
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)

    # Приводим некоторые математические символы к словам (англ/рус)
    text = text.replace("≈", "примерно")
    text = text.replace("×", "умножить на")
    text = text.replace("π", "пи")
    # Англ -> русские эквиваленты простых слов, чтобы русская модель читала лучше
    text = re.sub(r"\bpi\b", "пи", text, flags=re.IGNORECASE)
    text = re.sub(r"\btimes\b", "умножить на", text, flags=re.IGNORECASE)
    text = re.sub(r"\bapprox\b", "примерно", text, flags=re.IGNORECASE)

    # Заменяем латинскую 'e' как отдельное слово на русскую 'е'
    text = re.sub(r"\be\b", "е", text, flags=re.IGNORECASE)

    # Убираем эмодзи и прочие непечатные символы, но сохраняем цифры/буквы/пунктуацию
    text = re.sub(r"[^\w\dА-Яа-яёЁ\.,!?\-:;()«»\"'\/ \t\n]", " ", text, flags=re.UNICODE)

    # Сжимаем множественные пробелы и обрезаем
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fix_number_spacing(text: str) -> str:
    """
    Гарантируем пробел перед числом, если его нет (например 'примерно8' -> 'примерно 8').
    """
    # вставляем пробел перед цифрой, если перед ней не пробел и не символ начала строки
    text = re.sub(r"(?<!\s)(?<=\D)(\d)", r" \1", text)
    # и перед минусом-числом
    text = re.sub(r"(?<!\s)(?<=\D)(-)(\d)", r" \1\2", text)
    return text


def digits_to_words(text: str, max_frac_digits: int = 6) -> str:
    """
    Заменяет числа вида:
      - 123 -> 'один два три'
      - -5.03 -> 'минус пять точка ноль три'
    Обрезает дробную часть до max_frac_digits цифр.
    """

    def num_replacer(m):
        s = m.group(0)
        result_parts = []

        # Минус
        if s.startswith("-"):
            result_parts.append("минус")
            s = s[1:]
        # Если в числе есть точка
        if "." in s:
            int_part, frac_part = s.split(".", 1)
        else:
            int_part, frac_part = s, None

        # Целая часть: каждый символ-цифра -> слово
        if int_part == "":
            # случай вроде ".5" -> считаем как "ноль"
            result_parts.append(DIGIT_WORDS.get("0"))
        else:
            for ch in int_part:
                if ch in DIGIT_WORDS:
                    result_parts.append(DIGIT_WORDS[ch])
                else:
                    # на всякий случай (неожиданные символы) — просто добавить символ
                    result_parts.append(ch)

        # Дробная часть
        if frac_part is not None:
            result_parts.append("точка")
            # ограничиваем длину дробной части
            frac_part = frac_part[:max_frac_digits]
            for ch in frac_part:
                if ch in DIGIT_WORDS:
                    result_parts.append(DIGIT_WORDS[ch])
                else:
                    result_parts.append(ch)
            if len(m.group(0).split(".", 1)[1]) > max_frac_digits:
                result_parts.append("…")  # визуальный маркер обрезки

        return " ".join(result_parts)

    # Паттерн: опциональный минус, затем цифры, опционально дробная часть
    return re.sub(r"-?\d+(?:\.\d+)?", num_replacer, text)


class LocalTextToVoiceService:
    DEFAULT_LANGUAGE = "ru"
    DEFAULT_MODEL_ID = "v4_ru"
    DEFAULT_SAMPLE_RATE = 48000

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        model_id: str = DEFAULT_MODEL_ID,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ):
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
                repo_or_dir="snakers4/silero-models",
                model="silero_tts",
                language=self.language,
                speaker=self.model_id,
            )
            try:
                self.model.to(self.device)
            except Exception as e:
                print(f"[warn] model.to(device) не применим: {e}")

            self.speakers = getattr(self.model, "speakers", [self.model_id]) or [self.model_id]
            print(f"✅ Модель загружена. Доступные дикторы: {self.speakers}")
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            traceback.print_exc()
            self.model = None

    def synthesize_to_bytes(
        self,
        text: str,
        speaker: str = "aidar",
        speed: float = 1.0,
        pitch_semitones: float = 0.0,
        gain_db: float = 0.0,
        reverb_time: float = 0.0,
        reverb_decay: float = 0.0,
        silence_before: float = 0.0,
        silence_after: float = 0.0,
    ) -> bytes:
        """
        Синтез речи и пост-обработка с применением всех параметров.
        Возвращает WAV в виде байтов.
        """
        if not self.model:
            raise RuntimeError("TTS модель не загружена")

        raw_text = "" if text is None else str(text)
        # pipeline предобработки: sanitize -> spacing -> digits->words
        clean_text = sanitize_text(raw_text)
        clean_text = fix_number_spacing(clean_text)
        clean_text = digits_to_words(clean_text, max_frac_digits=4)

        # Ещё небольшая осторожная нормализация: убрать двойные пробелы
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        print("[TTS RAW INPUT]", repr(raw_text))
        print("[TTS CLEAN INPUT]", repr(clean_text))
        print("[TTS] Available speakers:", self.speakers)

        if not clean_text:
            # явный fallback, чтобы модель не падала на пустой строке
            clean_text = "Ответ не содержит текста для озвучивания."
            print("[TTS] text was empty after sanitize; using fallback text.")

        # Генерация исходного аудио (numpy float32)
        wav_tensor = self.model.apply_tts(
            text=clean_text,
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


