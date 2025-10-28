import { addMessageToDOM, appendTokenToMessage, scrollToBottom } from './chat_dom.js';
import { setupSendForm } from './chat_send.js';
import { setupSSE } from './chat_sse.js';
import { setupVoiceRecorder } from './chat_voice.js';
import { setupTTS } from './chat_tts.js'; 

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
  const playButton = document.getElementById('play-audio-button');
  const ttsButton = document.getElementById('tts-button');

  scrollToBottom(messageList);
  setupSendForm(sendForm, messageInput, selectedChatId);
  setupSSE(selectedChatId, messageList, addMessageToDOM, appendTokenToMessage);
  setupVoiceRecorder(recordButton, voiceIcon, messageInput, loadingIndicator, loadingText, playButton);
  setupTTS(ttsButton, messageInput); // <-- вызываем настройку TTS
});
