export function setupSSE(selectedChatId, messageList, addMessageToDOM, appendTokenToMessage) {
  if (!selectedChatId || typeof EventSource === 'undefined') return;

  console.log("[DEBUG] Setting up SSE for chat_id:", selectedChatId);

  const eventSource = new EventSource(`/chats/${selectedChatId}/events`);

  // ================== Новое сообщение ==================
  eventSource.addEventListener("new_message", (event) => {
    const message = JSON.parse(event.data);
    console.log("[DEBUG] new_message event received", message);
    addMessageToDOM(messageList, message);
  });

  // ================== Токены модели ==================
  eventSource.addEventListener("stream_token", (event) => {
    const tokenData = JSON.parse(event.data);
    console.log("[DEBUG] stream_token event received", tokenData);
    appendTokenToMessage(messageList, tokenData.msg_id, tokenData.token);
  });

  // ================== Автоозвучка ==================
  eventSource.addEventListener("audio_ready", (event) => {
    const data = JSON.parse(event.data); // {msg_id, audio_url}
    console.log("[DEBUG] audio_ready event received", data);

    const waitForEl = async (selector, timeout = 5000) => {
      const start = Date.now();
      while (Date.now() - start < timeout) {
        const el = document.querySelector(selector);
        if (el) return el;
        await new Promise(r => setTimeout(r, 50));
      }
      return null;
    };

    (async () => {
      const msgEl = await waitForEl(`[data-msg-id="${data.msg_id}"]`, 5000);
      console.log("[DEBUG] msgEl found?", !!msgEl, msgEl);

      if (!msgEl) {
        console.warn("[WARN] msgEl not found, audio will not play");
        return;
      }

      try {
        const resp = await fetch(data.audio_url);
        if (!resp.ok) {
          console.error("[ERROR] Failed to fetch audio, status:", resp.status);
          return;
        }

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        await audio.play();
        console.log("[DEBUG] Audio playback started for msg_id", data.msg_id);
      } catch (e) {
        console.error("[ERROR] Exception while fetching/playing audio", e);
      }
    })();
  });

  // ================== Ошибки SSE ==================
  eventSource.onerror = (err) => {
    console.error("SSE error", err);
    eventSource.close();
  };
}
