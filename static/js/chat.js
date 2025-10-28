// static/js/chat.js
(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const ctx = window.__CHAT_CONTEXT || {};
    const selectedChatId = ctx.selected_chat || null;

    const messageList = document.getElementById("message-list");
    const sendForm = document.getElementById("send-form");
    const messageInput = document.getElementById("message-input");
    const recordButton = document.getElementById('voice-record-button');
    const voiceIcon = document.getElementById('voice-icon');
    const loadingIndicator = document.getElementById('loading-indicator');
    const loadingText = document.getElementById('loading-text');

    function scrollToBottom() {
      if (messageList) messageList.scrollTop = messageList.scrollHeight;
    }

    function addMessageToDOM(message) {
  const time = new Date(message.created_at).toLocaleString();
  const messageDiv = document.createElement("div");

  // приводим к нижнему регистру, чтобы совпадало с CSS
  const typeClass = message.message_type.toLowerCase();
  messageDiv.classList.add("message", typeClass);
  messageDiv.setAttribute("data-id", message.id);

  const meta = document.createElement("div");
  meta.className = "m-meta";
  const strong = document.createElement("strong");
  strong.textContent = message.message_type.charAt(0).toUpperCase() + message.message_type.slice(1);
  const spanTime = document.createElement("span");
  spanTime.className = "time";
  spanTime.textContent = time;
  meta.appendChild(strong);
  meta.appendChild(spanTime);

  const body = document.createElement("div");
  body.className = "m-body";
  body.textContent = message.content;

  messageDiv.appendChild(meta);
  messageDiv.appendChild(body);

  if (messageList) {
    messageList.appendChild(messageDiv);
    scrollToBottom();
  }
}


    function appendTokenToMessage(msgId, token) {
      const messageBody = document.querySelector(`.message[data-id='${msgId}'] .m-body`);
      if (messageBody) {
        messageBody.parentElement.classList.remove("streaming");
        // Добавляем токен как текст (чтобы избежать XSS)
        messageBody.textContent = messageBody.textContent + token;
        scrollToBottom();
      }
    }

    // Отправка сообщения (если есть форма)
    if (sendForm) {
      sendForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const content = messageInput.value.trim();
        if (!content) return;
        const original = content;
        messageInput.value = "";

        try {
          const resp = await fetch(`/chats/${selectedChatId}/send`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ content })
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

    // SSE
    if (selectedChatId && typeof EventSource !== 'undefined') {
      const eventSource = new EventSource(`/chats/${selectedChatId}/events`);
      eventSource.addEventListener("new_message", (event) => {
        const message = JSON.parse(event.data);
        addMessageToDOM(message);
      });
      eventSource.addEventListener("stream_token", (event) => {
        const tokenData = JSON.parse(event.data);
        appendTokenToMessage(tokenData.msg_id, tokenData.token);
      });
      eventSource.onerror = (err) => {
        console.error("SSE error", err);
        eventSource.close();
      };
    }

    scrollToBottom();

    // --- Voice recorder setup (как у вас) ---
    let mediaRecorder, audioChunks = [], isRecording = false;
    const setupRecorder = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = uploadAudio;
        if (recordButton) recordButton.disabled = false;
      } catch (err) {
        console.error('Mic access denied', err);
        if (recordButton) {
          recordButton.disabled = true;
          recordButton.title = "Необходимо разрешение на использование микрофона.";
        }
      }
    };
    setupRecorder();

    async function uploadAudio() {
      if (!audioChunks.length) return;
      const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
      audioChunks = [];
      if (loadingText) loadingText.textContent = 'Обработка аудио локальной моделью...';
      if (loadingIndicator) loadingIndicator.style.display = 'flex';
      if (recordButton) recordButton.disabled = true;

      const fd = new FormData();
      fd.append("audio_file", audioBlob, "recording." + mediaRecorder.mimeType.split('/')[1]);

      try {
        const resp = await fetch(`/chats/transcribe_voice`, { method: "POST", body: fd });
        if (loadingIndicator) loadingIndicator.style.display = 'none';
        if (!resp.ok) {
          const err = await resp.json().catch(()=>({detail:resp.statusText}));
          alert(`Ошибка транскрипции: ${err.detail || resp.statusText}`);
          return;
        }
        const data = await resp.json();
        const transcription = data.content || "";
        if (messageInput) {
          let cur = messageInput.value.trim();
          if (cur.length > 0 && transcription.length > 0) cur += ' ';
          messageInput.value = cur + transcription + ' ';
          messageInput.focus();
        }
      } catch (err) {
        if (loadingIndicator) loadingIndicator.style.display = 'none';
        console.error('Error uploading audio', err);
        alert("Ошибка сети или сервера при отправке аудио.");
      } finally {
        if (voiceIcon) voiceIcon.textContent = '🎤';
        if (recordButton) recordButton.disabled = false;
      }
    }

    if (recordButton) {
      recordButton.addEventListener('click', () => {
        if (!mediaRecorder || recordButton.disabled) return;
        if (isRecording) {
          mediaRecorder.stop();
          recordButton.classList.remove('recording');
          voiceIcon.textContent = '⚙️';
          isRecording = false;
        } else {
          audioChunks = [];
          mediaRecorder.start();
          recordButton.classList.add('recording');
          voiceIcon.textContent = '🔴';
          isRecording = true;
        }
      });
    }
  });
})();
