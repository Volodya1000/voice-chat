// chat_send.js (обновлённая setupSendForm)
export function setupSendForm(sendForm, messageInput, selectedChatId) {
  if (!sendForm) return;
  sendForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const content = messageInput.value.trim();
    if (!content) return;
    const original = content;
    messageInput.value = "";

    // Считываем TTS-параметры и голосовой флаг
    const voiceEnabled = document.getElementById('voice-response-checkbox')?.checked ? "true" : "false";
    const payload = new URLSearchParams({
      content,
      voice_enabled: voiceEnabled,
      speaker: document.getElementById('voice-select')?.value || 'aidar',
      speed: document.getElementById('speed-range')?.value || '1.0',
      pitch_semitones: document.getElementById('pitch-range')?.value || '0',
      gain_db: document.getElementById('gain-range')?.value || '0',
      reverb_time: document.getElementById('reverb-time')?.value || '0',
      reverb_decay: document.getElementById('reverb-decay')?.value || '0'
    });

    try {
      const resp = await fetch(`/chats/${selectedChatId}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: payload.toString()
      });
      if (!resp.ok) {
        console.error("Failed to send", await resp.text());
        messageInput.value = original;
      }
    } catch (err) {
      console.error("Error sending message:", err);
      messageInput.value = original;
    }
  });
}
