// chat_voice.js
export async function setupVoiceRecorder(recordButton, voiceIcon, messageInput, loadingIndicator, loadingText, playButton) {
  let mediaRecorder, audioChunks = [], isRecording = false;
  let lastAudioBlob = null; // для воспроизведения последнего аудио

  // --- Функция загрузки аудио на сервер ---
  const uploadAudio = async () => {
    if (!audioChunks.length) return;

    const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
    lastAudioBlob = audioBlob; // сохраняем для прослушивания
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
        if (cur.length && transcription.length) cur += ' ';
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
  };

  // --- Инициализация MediaRecorder ---
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

  // --- Обработчик кнопки записи ---
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

  // --- Обработчик кнопки воспроизведения последнего аудио ---
  if (playButton) {
    playButton.addEventListener('click', () => {
      if (!lastAudioBlob) {
        alert("Нет записанного аудио для воспроизведения.");
        return;
      }
      const audioUrl = URL.createObjectURL(lastAudioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
    });
  }
}
