export function setupTTS(ttsButton, messageInput) {
  const ttsPanel = document.getElementById('tts-settings');
  const toggleBtn = document.getElementById('toggle-tts-panel');
  const playButton = document.getElementById('play-audio-button');

  // Тоггл панели
  if (toggleBtn && ttsPanel) {
    toggleBtn.addEventListener('click', () => {
      ttsPanel.classList.toggle('hidden');
      toggleBtn.textContent = ttsPanel.classList.contains('hidden')
        ? "🎧 Показать настройки озвучки"
        : "🔽 Скрыть настройки озвучки";
    });
  }

  // Обновление чисел при движении ползунков
  function formatLabelFor(slider, value) {
    if (!value && value !== 0) value = slider.value;
    switch (slider.id) {
      case 'speed-range': return parseFloat(value).toFixed(1);
      case 'pitch-range': return parseInt(value, 10).toString();
      case 'gain-range': {
        const v = parseInt(value, 10);
        return (v > 0 ? '+' + v : v.toString());
      }
      case 'reverb-time': return parseFloat(value).toFixed(1);
      case 'reverb-decay': return parseFloat(value).toFixed(2);
      default: return value;
    }
  }

  document.querySelectorAll('input[type="range"]').forEach(slider => {
    let label = document.getElementById(slider.id + '-value');
    if (!label) {
      const alt = slider.id.replace(/-range$/, '');
      label = document.getElementById(alt + '-value') || document.getElementById(slider.id.replace(/-time$/, '') + '-value');
    }
    if (label) {
      label.textContent = formatLabelFor(slider, slider.value);
      slider.addEventListener('input', () => {
        label.textContent = formatLabelFor(slider, slider.value);
      });
    }
  });

  // Обработка TTS
  let lastAudioUrl = null;

  if (ttsButton && messageInput) {
    ttsButton.addEventListener('click', async () => {
      const text = messageInput.value.trim();
      if (!text) return alert("Введите текст для озвучки.");

      const payload = {
        text,
        speaker: document.getElementById('voice-select').value,
        speed: parseFloat(document.getElementById('speed-range').value),
        pitch_semitones: parseInt(document.getElementById('pitch-range').value, 10),
        gain_db: parseFloat(document.getElementById('gain-range').value),
        reverb_time: parseFloat(document.getElementById('reverb-time').value),
        reverb_decay: parseFloat(document.getElementById('reverb-decay').value)
      };

      try {
        const resp = await fetch("/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) return alert("Ошибка TTS: " + resp.statusText);

        const blob = await resp.blob();
        if (lastAudioUrl) URL.revokeObjectURL(lastAudioUrl);
        lastAudioUrl = URL.createObjectURL(blob);

        const audio = new Audio(lastAudioUrl);
        audio.play();
      } catch (err) {
        console.error(err);
        alert("Ошибка при отправке запроса TTS.");
      }
    });
  }

  if (playButton) {
    playButton.addEventListener('click', () => {
      if (!lastAudioUrl) return alert("Нет сохранённого аудио. Сначала нажмите «Озвучить текст».");
      const audio = new Audio(lastAudioUrl);
      audio.play();
    });
  }
}
