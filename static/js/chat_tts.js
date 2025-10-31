export function setupTTS(ttsButton, messageInput) {
  if (!ttsButton || !messageInput) return;

  ttsButton.addEventListener("click", async () => {
    const text = messageInput.value.trim();
    if (!text) return alert("Введите текст для озвучки.");

    const payload = {
      text,
      speaker: document.getElementById("voice-select")?.value || "aidar",
      speed: parseFloat(document.getElementById("speed-range")?.value) || 1.0,
      pitch_semitones: parseFloat(document.getElementById("pitch-range")?.value) || 0,
      gain_db: parseFloat(document.getElementById("gain-range")?.value) || 0,
      reverb_time: parseFloat(document.getElementById("reverb-time")?.value) || 0,
      reverb_decay: parseFloat(document.getElementById("reverb-decay")?.value) || 0
    };

    // Проверка NaN
    Object.keys(payload).forEach(key => {
      if (typeof payload[key] === "number" && isNaN(payload[key])) {
        payload[key] = 0;
      }
    });

    try {
      const resp = await fetch("/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const errText = await resp.text();
        let msg = `Ошибка ${resp.status}: ${resp.statusText}`;
        try {
          const json = JSON.parse(errText);
          msg = json.detail || msg;
        } catch (_) {}
        throw new Error(msg);
      }

      const blob = await resp.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audio.play();
      audio.onended = () => URL.revokeObjectURL(audioUrl);

    } catch (err) {
      console.error("TTS Error:", err);
      alert("Ошибка TTS: " + err.message);
    }
  });
}

