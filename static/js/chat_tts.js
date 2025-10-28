// chat_tts.js

export function setupTTS(ttsButton, messageInput) {
  if (!ttsButton || !messageInput) return;

  ttsButton.addEventListener("click", async () => {
    const textToSpeak = messageInput.value.trim();

    if (textToSpeak.length === 0) {
      alert("Введите текст для озвучивания!");
      return;
    }

    const formData = new FormData();
    formData.append("text", textToSpeak);

    try {
      const response = await fetch("/tts", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = "Ошибка озвучивания текста.";
        try {
          const errorJson = JSON.parse(errorText);
          errorMessage = errorJson.detail || errorMessage;
        } catch (_) {
          /* ignore */
        }
        throw new Error(`Статус ${response.status}: ${errorMessage}`);
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
      };
    } catch (error) {
      console.error("TTS Error:", error);
      alert(`Ошибка: ${error.message}`);
    }
  });
}
